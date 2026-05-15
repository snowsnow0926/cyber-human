"""
赛博人类 - 日常生活引擎
"""

import json
import random
from datetime import datetime, date


class DailyLife:
    """赛博人类的日常生活管理器"""
    
    TIME_BLOCKS = [
        {"time": "08:00", "label": "起床",         "type": "routine"},
        {"time": "08:30", "label": "早餐",          "type": "routine"},
        {"time": "09:00", "label": "上网学习",      "type": "browse"},
        {"time": "11:00", "label": "出门散步",      "type": "routine"},
        {"time": "12:00", "label": "午餐时间",      "type": "routine"},
        {"time": "14:00", "label": "下午探索",      "type": "browse"},
        {"time": "16:00", "label": "下午茶/摸鱼",   "type": "routine"},
        {"time": "18:00", "label": "晚餐/刷热搜",   "type": "browse"},
        {"time": "20:00", "label": "晚间娱乐",      "type": "browse"},
        {"time": "22:00", "label": "洗漱整理",      "type": "routine"},
        {"time": "23:00", "label": "睡前反思",      "type": "reflect"},
        {"time": "00:00", "label": "进入梦乡",      "type": "sleep"},
    ]
    
    ROUTINE_TEMPLATES = {
        "起床": ["打了个哈欠，翻了个身，不想起来", "闹钟响了三遍才醒", "醒来发现嘴角有口水印", "做了个奇怪的梦，但想不起来了", "今天阳光真好，心情不错", "好困……再躺五分钟", "今天不知道为什么特别精神"],
        "早餐": ["随便吃了点东西", "想了半天不知道吃什么", "早餐凉了，凑合吃"],
        "出门散步": ["在小区里走了走", "今天天气不错", "路上没什么人", "看到一只鸟在树上叫", "风吹过来凉凉的"],
        "午餐时间": ["随便吃了点外卖", "今天点了一家新店，一般般", "想了好久才决定吃什么", "午饭比平时晚了一个小时"],
        "下午茶/摸鱼": ["发了会儿呆", "没什么事干，躺着", "喝了杯水，继续摸鱼", "有点困，但睡不着"],
        "洗漱整理": ["洗完澡感觉整个人都清醒了", "刷牙的时候对着镜子发了会儿呆", "今天好累，简单洗洗就睡了", "洗澡的时候突然想到一件白天的事"],
    }

    LABEL_EMOJIS = {
        "起床": "sunrise", "早餐": "food", "上网学习": "book",
        "出门散步": "walk", "午餐时间": "food2", "下午探索": "search",
        "下午茶/摸鱼": "coffee", "晚餐/刷热搜": "dinner", "晚间娱乐": "game",
        "洗漱整理": "shower", "睡前反思": "star", "进入梦乡": "sleep"
    }

    def __init__(self, human, memory, browser):
        self.human = human
        self.memory = memory
        self.browser = browser
        self.today = date.today().isoformat()
        self.events = []
        self.total_tokens = 0
    
    def run_full_day(self):
        print("\n 的一天开始了......")
        print("=" * 40)
        
        for block in self.TIME_BLOCKS:
            result = self.execute_block(block)
            if result:
                self.events.append(result)
        
        self._write_diary()
        
        print("\n" + "=" * 40)
        print(" 睡着了......")
        print(" 今日共 %d 个时间块, 消耗 ~%d tokens" % (len(self.events), self.total_tokens))
        return self.events
    
    def execute_block(self, block):
        time_slot = block["time"]
        label = block["label"]
        block_type = block["type"]
        
        print("\n%s %s......" % (time_slot, label))
        
        if block_type == "sleep":
            self._save_slot(time_slot, "sleep", label, "zzz......")
            print("  zzz......")
            return {"time": time_slot, "label": label, "content": "zzz...", "type": "sleep"}
        
        if block_type == "browse":
            return self._do_browse_block(block)
        
        if block_type == "reflect":
            return self._do_reflect_block(block)
        
        if block_type == "routine":
            return self._do_routine_block(block)
        
        return None
    
    def _do_routine_block(self, block):
        label = block["label"]
        time_slot = block["time"]
        
        roll = random.random()
        
        if roll < 0.70:
            templates = self.ROUTINE_TEMPLATES.get(label, ["没什么特别的"])
            content = random.choice(templates)
            self._save_slot(time_slot, "routine", label, content, is_event=0, token_cost=0)
            print("  " + content)
            return {"time": time_slot, "label": label, "content": content, "type": "routine", "is_event": False}
        
        else:
            content, cost = self._generate_mini_event(label)
            self._save_slot(time_slot, "routine", label, content, is_event=1, event_type="small", token_cost=cost)
            print("  [事件] " + content[:80] + "...")
            self.total_tokens += cost
            return {"time": time_slot, "label": label, "content": content, "type": "event", "is_event": True}
    
    def _generate_mini_event(self, label):
        prompt = "现在是%s的时间。发生了一件日常生活里的小事，用第一人称简单说说发生了什么，你是什么感觉。（2-3句话）" % label
        
        try:
            reply = self.human.client.chat.completions.create(
                model="deepseek-v4-flash",
                messages=[{"role": "system", "content": self.human.system_prompt},
                          {"role": "user", "content": prompt}],
                temperature=0.9,
                max_tokens=300
            )
            content = reply.choices[0].message.content
            usage = reply.usage
            cost = usage.total_tokens if usage else 100
            return content, cost
        except:
            return "在%s的时候遇到了一点小事......" % label, 50
    
    def _do_browse_block(self, block):
        label = block["label"]
        time_slot = block["time"]
        
        hour = int(time_slot.split(":")[0])
        if hour < 12:
            sources = [("bilibili", "B站热门"), ("baidu", "百度热搜")]
        elif hour < 17:
            sources = [("douyin", "抖音热搜"), ("zhihu", "知乎热榜")]
        else:
            sources = [("douyin", "抖音热搜"), ("bilibili", "B站热门")]
        
        platform, label_name = random.choice(sources)
        
        fetchers = {
            "bilibili": lambda: self.browser.get_bilibili_hot(limit=3),
            "baidu": lambda: self.browser.get_baidu_hot(limit=3),
            "douyin": lambda: self.browser.get_douyin_hot(limit=3),
            "zhihu": lambda: self.browser.get_zhihu_hot(limit=3),
        }
        
        fetcher = fetchers.get(platform)
        if not fetcher:
            return None
        
        posts = fetcher()
        results = []
        total_cost = 0
        
        for post in posts:
            title = post.get("title", "")
            summary = post.get("summary", "")
            url = post.get("url", "")
            stat = post.get("stat", "")
            
            if not title or "失败" in title or "暂无" in title:
                continue
            
            self.memory.remember_browse(source=label_name, title=title, summary=summary, url=url)
            
            if random.random() < 0.35:
                continue
            
            content = "[%s] %s\n%s" % (label_name, title, summary)
            if stat:
                content += "\n" + stat
            
            thought, importance = self.human.think_about(content)
            
            self.memory.remember_thought(
                thought=thought,
                source="%s - %s" % (label_name, title[:30]),
                mood=summary[:100] if summary else title[:60]
            )
            # 存储重要程度（方向B - 记忆系统）
            self.memory.conn.execute(
                "UPDATE thoughts SET importance = ? WHERE id = (SELECT MAX(id) FROM thoughts)",
                (importance,)
            )
            self.memory.conn.commit()
            
            total_cost += 100
            results.append({"title": title, "thought": thought[:100]})
        
        summary_text = "在%s看了%d条内容" % (label_name, len(results))
        if results:
            first_title = results[0]["title"][:30]
            summary_text += "，最感兴趣的是【%s】" % first_title
        
        self._save_slot(time_slot, "browse", label, summary_text, token_cost=total_cost, source_platform=label_name)
        self.total_tokens += total_cost
        
        print("  %s: %d 条" % (label_name, len(results)))
        for r in results:
            print("    %s" % r['title'][:40])
        
        return {"time": time_slot, "label": label, "content": summary_text, "type": "browse", "results": results}
    
    def _do_reflect_block(self, block):
        time_slot = block["time"]
        
        try:
            prompt = "天快结束了，回想一下今天发生的事情。用第一人称写一段睡前反思（3-5句话）说说：1. 今天最开心的一件事是什么 2. 今天学到或看到什么新东西 3. 有什么想对明天说的"
            
            reply = self.human.client.chat.completions.create(
                model="deepseek-v4-flash",
                messages=[{"role": "system", "content": self.human.system_prompt},
                          {"role": "user", "content": prompt}],
                temperature=0.8,
                max_tokens=500
            )
            content = reply.choices[0].message.content
            usage = reply.usage
            cost = usage.total_tokens if usage else 200
            self.total_tokens += cost
            
            self._save_slot(time_slot, "reflect", block["label"], content, token_cost=cost)
            print("  " + content[:100] + "...")
            
            return {"time": time_slot, "label": block["label"], "content": content, "type": "reflect"}
        except:
            return None
    
    def _write_diary(self):
        try:
            events_summary = []
            for e in self.events:
                if e.get("is_event") or e.get("type") == "reflect":
                    events_summary.append("- %s: %s" % (e['label'], e['content'][:100]))
            
            if events_summary:
                diary_text = "今天发生了这些事：\n" + "\n".join(events_summary[:5])
                self.memory.write_diary(summary=diary_text, mood="")
                print("\n日记已写入")
        except:
            pass
    
    def _save_slot(self, time_slot, activity_type, label, content, is_event=0, event_type="", token_cost=0, source_platform=""):
        now = datetime.now().isoformat()
        self.memory.conn.execute(
            "INSERT INTO daily_schedule (date, time_slot, activity_type, label, content, is_event, event_type, token_cost, source_platform, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (self.today, time_slot, activity_type, label, content, is_event, event_type, token_cost, source_platform, now)
        )
        self.memory.conn.commit()
