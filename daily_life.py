"""
赛博人类 - 日常生活引擎
"""

import json
import random
from datetime import datetime, date, timedelta
from memory_core import MemoryCore
from character import should_be_interested, get_interest_weight
from knowledge import KnowledgeSystem
from holiday import Holiday
from weather import Weather

# Playwright 浏览器增强（可选）
try:
    from browser_bot import BrowserBot
    HAS_PLAYWRIGHT = True
except:
    HAS_PLAYWRIGHT = False


def _ts(msg):
    """带时间戳的日志输出"""
    return "[DL %s] %s" % (datetime.now().strftime("%H:%M:%S"), msg)


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

    # 情绪 → 表情映射
    MOOD_EMOJIS = {
        "好奇": "🤔", "开心": "😊", "困惑": "😕", "害怕": "😨",
        "伤心": "😢", "生气": "😤", "惊讶": "😲", "平静": "😐",
    }

    def __init__(self, human, memory, browser):
        self.human = human
        self.memory = memory
        self.browser = browser
        self.today = date.today().isoformat()
        self.events = []
        self._playwright_available = HAS_PLAYWRIGHT
        self.total_tokens = 0
        self.memory_core = MemoryCore(memory)
        self.knowledge = KnowledgeSystem(memory)
        self.weather = Weather()
        self.holiday = Holiday()
        self.continuations = self._load_continuations()

    def _record_tokens(self, tokens):
        if tokens <= 0:
            return
        try:
            self.memory.conn.execute(
                "INSERT INTO token_usage (timestamp, prompt_tokens, completion_tokens, total_tokens) VALUES (?, 0, 0, ?)",
                (datetime.now().isoformat(), tokens)
            )
            self.memory.conn.commit()
        except Exception as e:
            print(_ts("记录token失败: " + str(e)))
    
    def _log(self, msg):
        print(_ts(msg))
    
    def get_mood_emoji(self):
        """获取小雪球当前的当前情绪表情"""
        try:
            recent = self.memory.get_recent_thoughts(1)
            if recent:
                mood = recent[0][4] if recent[0][4] else ""
                if mood in self.MOOD_EMOJIS:
                    return self.MOOD_EMOJIS[mood]
                # 如果mood是空的，尝试从thought text检测
                if recent[0][3]:
                    return self.MOOD_EMOJIS.get(self.memory_core._detect_emotion(recent[0][3]), "😐")
            return "😐"
        except:
            return "😐"

    def _load_continuations(self):
        """加载未完成的事件链"""
        try:
            rows = self.memory.conn.execute(
                "SELECT continuation FROM daily_schedule WHERE date = ? AND continuation != '' ORDER BY time_slot DESC LIMIT 3",
                (self.today,)
            ).fetchall()
            return [r[0] for r in rows if r[0]]
        except:
            return []
    
    def _save_continuation(self, text: str):
        """保存事件链延续到明天"""
        try:
            self.memory.conn.execute(
                "UPDATE daily_schedule SET continuation = ? WHERE date = ? AND time_slot = (SELECT MAX(time_slot) FROM daily_schedule WHERE date = ?)",
                (text, self.today, self.today)
            )
            self.memory.conn.commit()
        except Exception as e:
            print(_ts("保存continuation失败: " + str(e)))

    def run_full_day(self):
        """
        实时时间线：只生成当前时间附近（±1小时）的时间块。
        其他时间块标记为 "pending"。
        """
        print("\n🐩 的一天开始了......")
        print("=" * 40)
        
        now = datetime.now()
        current_minutes = now.hour * 60 + now.minute
        
        for block in self.TIME_BLOCKS:
            block_h, block_m = map(int, block["time"].split(":"))
            block_minutes = block_h * 60 + block_m
            
            # 计算时间差
            diff = abs(block_minutes - current_minutes)
            
            if diff <= 60:
                # 当前时间 ±1小时 → 执行
                result = self.execute_block(block)
                if result:
                    self.events.append(result)
            elif block_minutes < current_minutes:
                # 已经过去的时间 → 检查是否已生成，否则标记pending
                already_done = self._is_slot_done(block["time"])
                if not already_done:
                    self._mark_pending(block["time"], block["label"])
                else:
                    # 加载已有数据
                    self._load_existing_event(block)
            else:
                # 未来的时间块 → 标记pending
                self._mark_pending(block["time"], block["label"])
        
        # 如果今天还没有反思/日记，并且已经过了23点，写日记
        if current_minutes >= 23 * 60:
            self._write_diary()
        
        print("\n" + "=" * 40)
        print("🐩 今天执行了 %d 个时间块, 消耗 ~%d tokens" % (len(self.events), self.total_tokens))
        print(_ts("已完成区块: %d/%d" % (len(self.events), len(self.TIME_BLOCKS))))
        return self.events
    
    def _is_slot_done(self, time_slot):
        """检查时间块是否已经生成"""
        try:
            row = self.memory.conn.execute(
                "SELECT content FROM daily_schedule WHERE date = ? AND time_slot = ?",
                (self.today, time_slot)
            ).fetchone()
            return row is not None and row[0] != "pending"
        except:
            return False
    
    def _mark_pending(self, time_slot, label):
        """标记时间块为待定"""
        try:
            existing = self.memory.conn.execute(
                "SELECT id FROM daily_schedule WHERE date = ? AND time_slot = ?",
                (self.today, time_slot)
            ).fetchone()
            if not existing:
                self.memory.conn.execute(
                    "INSERT INTO daily_schedule (date, time_slot, activity_type, label, content, is_event, created_at) VALUES (?, ?, 'pending', ?, 'pending', 0, ?)",
                    (self.today, time_slot, label, datetime.now().isoformat())
                )
                self.memory.conn.commit()
        except Exception as e:
            print(_ts("标记pending失败: " + str(e)))
    
    def _load_existing_event(self, block):
        """加载已存在的事件数据"""
        try:
            rows = self.memory.conn.execute(
                "SELECT content, is_event, event_type, token_cost, source_platform FROM daily_schedule WHERE date = ? AND time_slot = ? AND content != 'pending'",
                (self.today, block["time"])
            ).fetchall()
            for r in rows:
                self.events.append({
                    "time": block["time"],
                    "label": block["label"],
                    "content": r[0][:200] if r[0] else "",
                    "is_event": bool(r[1]),
                    "event_type": r[2] or "", 
                    "source_platform": r[4] or ""
                })
        except:
            pass
    
    def execute_block(self, block):
        time_slot = block["time"]
        label = block["label"]
        block_type = block["type"]
        
        print("\n%s %s......" % (time_slot, label))
        
        if block_type == "sleep":
            self._save_slot(time_slot, "sleep", label, "zzz......")
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
        
        try:
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
        except Exception as e:
            print(_ts("routine块失败: " + str(e)))
            return None
    
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
            self._record_tokens(cost)
            return content, cost
        except Exception as e:
            print(_ts("mini事件生成失败: " + str(e)))
            return "在%s的时候遇到了一点小事......" % label, 50
    
    def _fetch_bilibili_enhanced(self, limit=3):
        """B站增强获取：有Playwright用浏览器，没有就用API"""
        if self._playwright_available:
            try:
                self._log("B站增强版: 使用Playwright浏览器")
                with BrowserBot(headless=True) as bot:
                    data = bot.get_bilibili_hot_data(limit=limit)
                    if data and len(data) >= limit//2:
                        self._log("Playwright获取到 %d 条B站数据" % len(data))
                        return data
            except Exception as e:
                self._log("Playwright B站失败，回退到API: " + str(e))
        
        self._log("B站回退: 使用API")
        return self.browser.get_bilibili_hot(limit=limit)
    
    def _do_browse_block(self, block):
        label = block["label"]
        time_slot = block["time"]
        
        try:
            hour = int(time_slot.split(":")[0])
            
            # 所有数据源（带权重）
            all_sources = [
                ("bilibili", "B站热门", 3),
                ("baidu", "百度热搜", 2),
                ("douyin", "抖音热搜", 3),
                ("zhihu", "知乎热榜", 2),
                ("xiaohongshu", "小红书", 2),
            ]
            
            # 根据时间段调整概率
            if hour < 12:
                weights = [3, 1, 1, 1, 1]
            elif hour < 17:
                weights = [1, 1, 3, 2, 2]
            else:
                weights = [3, 1, 2, 1, 2]
            
            # 加权随机选择
            total_w = sum(weights)
            r = random.randint(1, total_w)
            cumulative = 0
            chosen = all_sources[0]
            for i, w in enumerate(weights):
                cumulative += w
                if r <= cumulative:
                    chosen = all_sources[i]
                    break
            
            platform, label_name = chosen[0], chosen[1]
            
            fetchers = {
                "bilibili": lambda: self._fetch_bilibili_enhanced(limit=5),
                "baidu": lambda: self.browser.get_baidu_hot(limit=5),
                "douyin": lambda: self.browser.get_douyin_hot(limit=5),
                "zhihu": lambda: self.browser.get_zhihu_hot(limit=5),
                "xiaohongshu": lambda: self.browser.get_xiaohongshu_hot(limit=5),
            }
            
            fetcher = fetchers.get(platform)
            if not fetcher:
                return None
            
            posts = fetcher()
            results = []
            total_cost = 0
            
            posts = [p for p in posts if should_be_interested(p.get("title", ""), p.get("summary", ""))]
            if not posts:
                self._log("小雪球对此不感兴趣，跳过")
                return None
            
            posts.sort(key=lambda p: get_interest_weight(p.get("title", "")), reverse=True)
            
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
                self.memory_core.tag_thought(thought, importance)
                self.memory.conn.execute(
                    "UPDATE thoughts SET importance = ? WHERE id = (SELECT MAX(id) FROM thoughts)",
                    (importance,)
                )
                content_for_knowledge = "[%s] %s\n%s" % (label_name, title, summary)
                if stat:
                    content_for_knowledge += "\n" + stat
                
                k = self.knowledge.extract_from_content(content_for_knowledge, label_name, thought)
                if k["has_knowledge"]:
                    self.knowledge.save_knowledge(
                        concept=k["concept"],
                        explanation=k["explanation"],
                        category=k["category"],
                        source=label_name + " - " + title[:30]
                    )
                    self._log("学到新知识: " + k["category"] + " - " + k["concept"][:40])
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
        except Exception as e:
            print(_ts("浏览块失败: " + str(e)))
            return None
    
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
            self._record_tokens(cost)
            
            self._save_slot(time_slot, "reflect", block["label"], content, token_cost=cost)
            print("  " + content[:100] + "...")
            
            return {"time": time_slot, "label": block["label"], "content": content, "type": "reflect"}
        except Exception as e:
            print(_ts("反思块失败: " + str(e)))
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
        except Exception as e:
            print(_ts("写日记失败: " + str(e)))
    
    def _save_slot(self, time_slot, activity_type, label, content, is_event=0, event_type="", token_cost=0, source_platform=""):
        try:
            now = datetime.now().isoformat()
            # 删除之前的 pending 记录
            self.memory.conn.execute(
                "DELETE FROM daily_schedule WHERE date = ? AND time_slot = ?",
                (self.today, time_slot)
            )
            self.memory.conn.execute(
                "INSERT INTO daily_schedule (date, time_slot, activity_type, label, content, is_event, event_type, token_cost, source_platform, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (self.today, time_slot, activity_type, label, content, is_event, event_type, token_cost, source_platform, now)
            )
            self.memory.conn.commit()
        except Exception as e:
            print(_ts("保存slot失败: " + str(e)))
