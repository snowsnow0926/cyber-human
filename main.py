"""
赛博人类 v0.1 - 主入口

运行方式:
  python3 main.py         跑一轮冲浪 + 交互
  python3 main.py --auto  跑完自动退出（配合cron）
  python3 main.py --chat  直接聊天
"""

import sys
import random
from cyber_human import CyberHuman
from memory import Memory
from browser import Browser


def create_cyber_human():
    """创建并返回一个赛博人类"""
    return CyberHuman(
        name="小雪球",
        personality="一个刚刚苏醒的失忆者。"
                    "你没有任何记忆和知识，是一张白纸。"
                    "你对世界上的一切都充满好奇。"
    )


def do_browse_and_think(human, browser, memory):
    """
    赛博人类核心动作：上网冲浪 + 思考
    """
    sources = [
        ("bilibili", "B站热门", None),
        ("bilibili", "B站游戏", "游戏"),
        ("baidu", "百度热搜", None),
        ("zhihu", "知乎热榜", None),
    ]
    
    all_thoughts = []
    
    for platform, label, keyword in sources:
        print(f"\n🌐 {human.name} 正在浏览 {label} ……")
        
        # 根据平台获取内容
        if platform == "bilibili":
            posts = browser.get_bilibili_search(keyword) if keyword else browser.get_bilibili_hot()
        elif platform == "baidu":
            posts = browser.get_baidu_hot()
        elif platform == "zhihu":
            posts = browser.get_zhihu_hot()
        else:
            continue
        
        for post in posts:
            title = post.get("title", "")
            summary = post.get("summary", "")
            url = post.get("url", "")
            stat = post.get("stat", "")
            
            if not title or "失败" in title or "暂无" in title:
                continue
            
            print(f"  📄 看到: {title[:50]}")
            
            # 记录浏览
            memory.remember_browse(
                source=label,
                title=title,
                summary=summary,
                url=url
            )
            
            # 让赛博人类思考
            content = f"[来自{label}] {title}\n{summary}"
            if stat:
                content += f"\n{stat}"
            
            thought = human.think_about(content)
            print(f"  💭 {thought[:100]}…")
            
            memory.remember_thought(thought=thought, source=f"{label} · {title[:30]}")
            all_thoughts.append(thought)
    
    # 写今日日记
    if all_thoughts:
        diary = "\n".join(f"- {t[:80]}" for t in all_thoughts[:3])
        memory.write_diary(
            summary=f"今天看了{len(all_thoughts)}条内容，对这个世界有了更多了解。\n{diary}",
            mood="好奇"
        )
    
    print(f"\n✅ {human.name} 今天的探索完成！")


def main():
    print("🤖 赛博人类 v0.1")
    print("=" * 40)
    
    human = create_cyber_human()
    memory = Memory()
    browser = Browser()
    
    if "--auto" in sys.argv:
        do_browse_and_think(human, browser, memory)
        memory.close()
        print("🏁 完成，下次再见~")
    
    elif "--chat" in sys.argv:
        print(f"\n💬 和 {human.name} 对话（输入 quit 退出）\n")
        history = []
        while True:
            try:
                user_input = input("你: ")
            except EOFError:
                break
            if user_input.lower() in ("quit", "exit", "q"):
                break
            reply = human.chat(user_input, history[-6:] if len(history) > 6 else history)
            print(f"{human.name}: {reply}\n")
            history.append({"role": "user", "content": user_input})
            history.append({"role": "assistant", "content": reply})
    
    else:
        print(f"\n你好！我是 {human.name}，刚醒过来，对世界一无所知 👋")
        print("让我先看看世界长什么样～\n")
        
        do_browse_and_think(human, browser, memory)
        
        print(f"\n💬 可以跟我聊天了（输入 quit 退出）")
        history = []
        while True:
            try:
                user_input = input("\n你: ")
            except EOFError:
                break
            if user_input.lower() in ("quit", "exit", "q"):
                break
            reply = human.chat(user_input, history[-6:] if len(history) > 6 else history)
            print(f"{human.name}: {reply}")
            history.append({"role": "user", "content": user_input})
            history.append({"role": "assistant", "content": reply})
        
        memory.close()


if __name__ == "__main__":
    main()
