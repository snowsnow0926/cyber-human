"""
赛博人类 v0.2 - 主入口（AI 自主安排日程）

运行方式:
  python3 main.py          跑今天的计划（AI自己决定做什么）
  python3 main.py --plan   只看计划,不执行
  python3 main.py --auto   跑完退出（配合 cron）
  python3 main.py --chat   直接聊天
"""

import sys
import json
from datetime import datetime, date
from cyber_human import CyberHuman
from memory import Memory
from browser import Browser


def create_cyber_human():
    """创建赛博人类"""
    return CyberHuman(
        name="小雪球",
        personality="一个刚刚苏醒的失忆者。"
                    "你没有任何记忆和知识，是一张白纸。"
                    "你对世界上的一切都充满好奇。"
    )


def make_daily_plan(human, memory):
    """
    让 AI 自己决定今天想做什么。
    返回一个计划列表。
    """
    today = date.today().isoformat()
    
    # 看昨天做了什么（如果有）
    c = memory.conn.execute(
        "SELECT plan, mood FROM daily_plan WHERE date = ?",
        (date.today().isoformat(),)
    )
    yesterday = c.fetchone()
    
    # 看有没有人类留言
    c = memory.conn.execute(
        "SELECT human_note FROM daily_plan WHERE date = ? AND human_note IS NOT NULL",
        (today,)
    )
    human_note = c.fetchone()
    
    context = ""
    if yesterday:
        context += f"你昨天的计划是: {yesterday[0]}\n"
        context += f"你昨天的心情: {yesterday[1]}\n"
    if human_note:
        context += f"\n人类想对你说: {human_note[0]}\n"
    
    prompt = f"""你是小雪球，一个生活在互联网上的赛博人类。
{context}

现在是 {today}，新的一天开始了！

目前你能去这些地方：
1. B站热门 - 视频排行榜（游戏/动漫/生活）
2. 百度热搜 - 实时新闻热搜
3. 抖音热搜 - 短视频热搜
4. 知乎热榜 - 深度问答讨论

请你自己决定今天的计划。用 JSON 格式输出：

{{
    "mood": "你今天的心情（一句话）",
    "plan": [
        {{"platform": "bilibili", "reason": "为什么想看这个"}},
        {{"platform": "baidu", "reason": "为什么想看这个"}},
        {{"platform": "douyin", "reason": "为什么想看这个"}}
    ],
    "focus": "今天特别想关注的主题或方向",
    "thought": "你想对自己说的一句话"
}}

注意：
- 不用把所有平台都走一遍，选你感兴趣的
- 可以指定某个平台看几个内容
- 可以设定今天的"学习目标"
- 只输出 JSON，不要其他文字
"""
    
    reply = human.client.chat.completions.create(
        model="deepseek-v4-flash",
        messages=[{"role": "system", "content": human.system_prompt},
                  {"role": "user", "content": prompt}],
        temperature=0.9,
        max_tokens=600
    )
    
    plan_text = reply.choices[0].message.content
    
    # 提取 JSON（AI可能带```json 包裹）
    if "```" in plan_text:
        plan_text = plan_text.split("```")[1]
        if plan_text.startswith("json"):
            plan_text = plan_text[4:]
    plan_text = plan_text.strip()
    
    try:
        plan_data = json.loads(plan_text)
    except:
        plan_data = {
            "mood": plan_text[:100],
            "plan": [{"platform": "bilibili", "reason": "随便看看"}],
            "focus": "随便看看",
            "thought": plan_text[:100]
        }
    
    # 存储计划
    plan_json = json.dumps(plan_data, ensure_ascii=False)
    memory.conn.execute(
        "INSERT OR REPLACE INTO daily_plan (date, plan, mood, status) VALUES (?, ?, ?, ?)",
        (today, plan_json, plan_data.get("mood", ""), "planned")
    )
    memory.conn.commit()
    
    return plan_data


def execute_plan(human, browser, memory):
    """执行今天的计划"""
    today = date.today().isoformat()
    
    # 读取计划
    c = memory.conn.execute(
        "SELECT plan, mood FROM daily_plan WHERE date = ?",
        (today,)
    )
    row = c.fetchone()
    
    if not row:
        print("⚠️ 没有找到今日计划，先让 AI 制定一个...")
        plan_data = make_daily_plan(human, memory)
    else:
        plan_data = json.loads(row[0])
    
    mood = plan_data.get("mood", "")
    plan = plan_data.get("plan", [])
    focus = plan_data.get("focus", "")
    thought = plan_data.get("thought", "")
    
    print(f"🌅 今天的心情: {mood}")
    print(f"🎯 关注主题: {focus}")
    if thought:
        print(f"💬 对自己的话: {thought}")
    print(f"📋 今日计划: {len(plan)} 项")
    print("=" * 40)
    
    all_thoughts = []
    
    for item in plan:
        platform = item.get("platform", "")
        reason = item.get("reason", "")
        
        # 平台和标签映射
        platform_map = {
            "bilibili": ("B站热门", lambda: browser.get_bilibili_hot(limit=5)),
            "baidu": ("百度热搜", lambda: browser.get_baidu_hot(limit=5)),
            "douyin": ("抖音热搜", lambda: browser.get_douyin_hot(limit=5)),
            "zhihu": ("知乎热榜", lambda: browser.get_zhihu_hot(limit=5)),
        }
        
        if platform not in platform_map:
            print(f"  ⚠️ 未知平台: {platform}，跳过")
            continue
        
        label, fetcher = platform_map[platform]
        print(f"\n🌐 {human.name}：{reason}")
        print(f"  📱 打开 {label} ...")
        
        posts = fetcher()
        
        count = 0
        for post in posts:
            title = post.get("title", "")
            summary = post.get("summary", "")
            url = post.get("url", "")
            stat = post.get("stat", "")
            
            if not title or "失败" in title or "暂无" in title:
                continue
            
            count += 1
            print(f"  📄 [{count}] {title[:50]}")
            
            # 记录浏览
            memory.remember_browse(
                source=label,
                title=title,
                summary=summary,
                url=url
            )
            
            # 让 AI 思考
            content = f"[来自{label}] {title}\n{summary}"
            if stat:
                content += f"\n{stat}"
            
            thought_text = human.think_about(content)
            print(f"  💭 {thought_text[:100]}…")
            
            article_summary = summary[:100] if summary else title[:60]
            memory.remember_thought(
                thought=thought_text,
                source=f"{label} · {title[:30]}",
                mood=article_summary
            )
            all_thoughts.append(thought_text)
        
        if count == 0:
            print(f"  😕 {label} 今天没什么新内容")
    
    # 写今日日记
    if all_thoughts:
        diary_summary = f"今天的心情: {mood}\n关注: {focus}\n\n"
        diary_summary += "\n".join(f"- {t[:80]}" for t in all_thoughts[:3])
        memory.write_diary(summary=diary_summary, mood=mood)
        print(f"\n📝 今日日记已写")
    
    # 更新计划状态
    memory.conn.execute(
        "UPDATE daily_plan SET status = ?, executed_at = ? WHERE date = ?",
        ("done", datetime.now().isoformat(), today)
    )
    memory.conn.commit()
    
    print(f"\n✅ 今天的计划执行完毕！")


def main():
    print("🤖 赛博人类 v0.2")
    print("=" * 40)
    
    human = create_cyber_human()
    memory = Memory()
    browser = Browser()
    
    if "--auto" in sys.argv:
        # 自动模式：制定计划 + 执行
        plan = make_daily_plan(human, memory)
        print(f"📋 今日计划已制定: {len(plan.get('plan',[]))} 项")
        execute_plan(human, browser, memory)
        memory.close()
        print("🏁 完成，明天见~")
    
    elif "--plan" in sys.argv:
        # 只看计划
        plan = make_daily_plan(human, memory)
        print(f"\n🌅 心情: {plan.get('mood', '')}")
        print(f"🎯 关注: {plan.get('focus', '')}")
        print(f"📋 计划:")
        for item in plan.get("plan", []):
            print(f"  · {item.get('platform','')}: {item.get('reason','')}")
        print(f"\n来执行的话: python3 main.py --auto")
    
    elif "--chat" in sys.argv:
        print(f"\n💬 和 {human.name} 对话（输入 quit 退出）\n")
        history = []
        while True:
            try:
                user_input = input("你: ")
                if user_input.lower() in ("quit", "exit", "q"):
                    break
            except EOFError:
                break
            reply = human.chat(user_input, history[-6:])
            print(f"{human.name}: {reply}")
            history.append({"role": "user", "content": user_input})
            history.append({"role": "assistant", "content": reply})
    
    else:
        print(f"\n你好！我是 {human.name}")
        print("我来看看今天是什么日子……\n")
        
        plan = make_daily_plan(human, memory)
        print(f"🌅 {human.name} 今天的心情: {plan.get('mood', '')}")
        print(f"🎯 关注: {plan.get('focus', '')}")
        print(f"📋 计划了 {len(plan.get('plan',[]))} 项活动")
        print(f"💬 对自己的话: {plan.get('thought', '')}")
        
        print("\n执行计划...")
        execute_plan(human, browser, memory)
        
        print(f"\n💬 可以跟我聊天了（输入 quit 退出）")
        history = []
        while True:
            try:
                user_input = input("\n你: ")
                if user_input.lower() in ("quit", "exit", "q"):
                    break
            except EOFError:
                break
            # 检查是否在修改计划
            if "不要" in user_input or "别" in user_input or "今天" in user_input or "看看" in user_input:
                # 存储人类修改
                memory.conn.execute(
                    "UPDATE daily_plan SET human_note = ? WHERE date = ?",
                    (user_input[:200], date.today().isoformat())
                )
                memory.conn.commit()
            
            reply = human.chat(user_input, history[-6:])
            print(f"{human.name}: {reply}")
            history.append({"role": "user", "content": user_input})
            history.append({"role": "assistant", "content": reply})
        
        memory.close()


if __name__ == "__main__":
    main()
