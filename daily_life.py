"""
日常生活模拟引擎
v0.7 核心逻辑 + v1.0 接口适配
"""

from __future__ import annotations

import random
from datetime import datetime, date
from typing import Any, Optional

from logger import get_logger
from character import should_be_interested, get_interest_weight
from memory import BrowseRecord, Thought, DiaryEntry
from memory_core import get_consolidation

logger = get_logger(__name__)


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
    "起床": ["打了个哈欠，翻了个身，不想起来", "闹钟响了三遍才醒", "醒来发现嘴角有口水印",
             "做了个奇怪的梦，但想不起来了", "今天阳光真好，心情不错", "好困……再躺五分钟",
             "今天不知道为什么特别精神"],
    "早餐": ["随便吃了点东西", "想了半天不知道吃什么", "早餐凉了，凑合吃"],
    "出门散步": ["在小区里走了走", "今天天气不错", "路上没什么人",
               "看到一只鸟在树上叫", "风吹过来凉凉的"],
    "午餐时间": ["随便吃了点外卖", "今天点了一家新店，一般般",
               "想了好久才决定吃什么", "午饭比平时晚了一个小时"],
    "下午茶/摸鱼": ["发了会儿呆", "没什么事干，躺着", "喝了杯水，继续摸鱼",
                  "有点困，但睡不着"],
    "洗漱整理": ["洗完澡感觉整个人都清醒了", "刷牙的时候对着镜子发了会儿呆",
               "今天好累，简单洗洗就睡了", "洗澡的时候突然想到一件白天的事"],
}

# 浏览源配置（源名称, 显示名, 默认权重）
BROWSE_SOURCES = [
    ("bilibili", "B站热门", 3),
    ("baidu", "百度热搜", 2),
    ("zhihu", "知乎热榜", 2),
    ("ithome", "IT之家", 1),
    ("people", "人民网", 1),
    ("xiaohongshu", "小红书", 2),
]


class DailyLifeEngine:
    """日常生活模拟引擎（v0.7 逻辑 + v1.0 接口）"""

    def __init__(self, db=None, ai=None, browser=None, kb=None, emotion=None):
        from memory import get_db
        from cyber_human import get_ai
        from browser import get_browser
        from knowledge import get_knowledge_base
        from emotion import get_emotion_system

        self.db = db or get_db()
        self.ai = ai or get_ai()
        self.browser = browser or get_browser()
        self.kb = kb or get_knowledge_base()
        self.emotion = emotion or get_emotion_system()
        self.events: list[dict] = []
        self.total_tokens = 0
        self._is_simulating = False
        self._block_index = 0
        self._sim_date: str = ""
        self._seen_titles: set[str] = set()
        logger.info("DailyLifeEngine initialized (v0.7 merge)")

    def _today(self, sim_date: str = "") -> str:
        if sim_date and sim_date != "today":
            return sim_date
        return date.today().isoformat()

    def _record_tokens(self, tokens: int):
        if tokens <= 0:
            return
        try:
            with self.db.get_conn() as conn:
                conn.execute(
                    "INSERT INTO token_usage (timestamp, prompt_tokens, completion_tokens, total_tokens) VALUES (?, 0, 0, ?)",
                    (datetime.now().isoformat(), tokens),
                )
        except Exception as e:
            logger.warning(f"记录token失败: {e}")

    def _save_slot(self, time_slot: str, activity_type: str, label: str,
                   content: str, is_event: int = 0, event_type: str = "",
                   token_cost: int = 0, source_platform: str = "",
                   sim_date: str = ""):
        """保存时间块记录到 daily_schedule 表"""
        today = self._today(sim_date)
        try:
            with self.db.get_conn() as conn:
                conn.execute(
                    "DELETE FROM daily_schedule WHERE date = ? AND time_slot = ?",
                    (today, time_slot),
                )
                now = datetime.now().isoformat()
                conn.execute(
                    """INSERT INTO daily_schedule
                       (date, time_slot, activity_type, label, content,
                        is_event, event_type, token_cost, source_platform, created_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (today, time_slot, activity_type, label, content,
                     is_event, event_type, token_cost, source_platform, now),
                )
        except Exception as e:
            logger.warning(f"保存slot失败: {e}")

    def _mark_pending(self, time_slot: str, label: str, sim_date: str = ""):
        """标记时间块为待定"""
        today = self._today(sim_date)
        try:
            with self.db.get_conn() as conn:
                existing = conn.execute(
                    "SELECT id FROM daily_schedule WHERE date = ? AND time_slot = ?",
                    (today, time_slot),
                ).fetchone()
                if not existing:
                    conn.execute(
                        """INSERT INTO daily_schedule
                           (date, time_slot, activity_type, label, content, is_event, created_at)
                           VALUES (?, ?, pending, ?, pending, 0, ?)""",
                        (today, time_slot, label, datetime.now().isoformat()),
                    )
        except Exception as e:
            logger.warning(f"标记pending失败: {e}")

    def _is_slot_done(self, time_slot: str, sim_date: str = "") -> bool:
        today = self._today(sim_date)
        try:
            with self.db.get_conn() as conn:
                row = conn.execute(
                    "SELECT content FROM daily_schedule WHERE date = ? AND time_slot = ?",
                    (today, time_slot),
                ).fetchone()
                return row is not None and row[0] != "pending"
        except:
            return False

    def run_full_day(self, sim_date: str = "") -> list[dict]:
        """
        运行全天模拟。
        - sim_date 参数：传了则执行所有 12 个区块
        - 不传（实时模式）：只执行当前时间 ±1 小时，其余标记 pending
        """
        # 标准化日期参数：空字符串或 "today" 都转为今天日期
        if not sim_date or sim_date == "today":
            sim_date = date.today().isoformat()
        self._sim_date = sim_date
        today = self._today(sim_date)
        # _is_simulating: 始终为 True，确保日记在模拟结束时生成
        # （实时模式走 cron 定时，模拟模式走 run_full_day）
        self._is_simulating = True
        logger.info(f"=== 开始全天模拟: {today} ===")
        logger.warning(f">>> {today} 的一天开始了......")
        logger.warning("=" * 40)

        self.events = []
        self.total_tokens = 0
        self._block_index = 0

        # 模拟模式：执行所有区块（实时模式走 cron 定时，模拟模式走这里）
        for block in TIME_BLOCKS:
            result = self._execute_block(block, sim_date)
            if result:
                self.events.append(result)

        # 模拟结束：写日记 + 记忆巩固
        self._write_diary(sim_date)
        try:
            mc = get_consolidation()
            mc.consolidate()
        except Exception as e:
            logger.warning(f"记忆巩固失败: {e}")

        logger.warning("=" * 40)
        logger.info(f">>> 今天执行了 {len(self.events)} 个时间块, 消耗 ~{self.total_tokens} tokens")
        return self.events

    def _execute_block(self, block: dict, sim_date: str = "") -> Optional[dict]:
        time_slot = block["time"]
        label = block["label"]
        block_type = block["type"]
        self._block_index += 1

        logger.info(f"[{self._block_index}/12] {time_slot} {label}......")

        if block_type == "sleep":
            self._save_slot(time_slot, "sleep", label, "zzz......", sim_date=sim_date)
            return {"time": time_slot, "label": label, "content": "zzz...", "type": "sleep"}

        if block_type == "routine":
            return self._do_routine_block(block, sim_date)
        if block_type == "browse":
            return self._do_browse_block(block, sim_date)
        if block_type == "reflect":
            return self._do_reflect_block(block, sim_date)

        return None

    def _do_routine_block(self, block: dict, sim_date: str = "") -> Optional[dict]:
        label = block["label"]
        time_slot = block["time"]

        try:
            roll = random.random()

            if roll < 0.70:
                # 70% 模板
                templates = ROUTINE_TEMPLATES.get(label, ["没什么特别的"])
                content = random.choice(templates)
                self._save_slot(time_slot, "routine", label, content,
                                is_event=0, token_cost=0, sim_date=sim_date)
                logger.debug(f"  模板事件: {content}")
                return {"time": time_slot, "label": label, "content": content,
                        "type": "routine", "is_event": False}

            else:
                # 30% AI 生成小事件
                content, cost = self._generate_mini_event(label)
                self._save_slot(time_slot, "routine", label, content,
                                is_event=1, event_type="small", token_cost=cost,
                                sim_date=sim_date)
                logger.info(f"  [AI事件] {content[:80]}...")
                self.total_tokens += cost
                return {"time": time_slot, "label": label, "content": content,
                        "type": "event", "is_event": True}

        except Exception as e:
            logger.warning(f"routine块失败: {e}")
            self._save_slot(time_slot, "routine", label, "今天有点累，不想动..",
                            sim_date=sim_date)
            return None

    def _generate_mini_event(self, label: str) -> tuple[str, int]:
        prompt = f"现在是{label}的时间。发生了一件日常生活里的小事，用第一人称简单说说发生了什么，你是什么感觉。（2-3句话）"
        try:
            response = self.ai._call_llm(prompt, system=None)
            content = response.content
            cost = response.total_tokens if hasattr(response, 'total_tokens') else 100
            self._record_tokens(cost)
            return content, cost
        except Exception as e:
            logger.warning(f"mini事件生成失败: {e}")
            return f"在{label}的时候遇到了一点小事......", 50

    def _do_browse_block(self, block: dict, sim_date: str = "") -> Optional[dict]:
        label = block["label"]
        time_slot = block["time"]

        try:
            hour = int(time_slot.split(":")[0])

            # 根据时间段调整权重
            if hour < 12:
                weights = [3, 1, 1, 1, 1, 1]
            elif hour < 17:
                weights = [1, 1, 2, 2, 1, 2]
            else:
                weights = [3, 1, 1, 1, 1, 2]

            # 加权随机选择源
            total_w = sum(weights)
            r = random.randint(1, total_w)
            cumulative = 0
            chosen = BROWSE_SOURCES[0]
            for i, w in enumerate(weights):
                cumulative += w
                if r <= cumulative:
                    chosen = BROWSE_SOURCES[i]
                    break

            source_name, display_name = chosen[0], chosen[1]

            # 用 v1.0 browser.fetch 获取内容
            try:
                browse_results = self.browser.fetch(source_name, timeout=10)
            except Exception as e:
                logger.warning(f"从 {source_name} 获取失败: {e}")
                self._save_slot(time_slot, "browse", label,
                                f"在{display_name}上刷了刷，但没加载出来...",
                                sim_date=sim_date)
                return None

            if not browse_results:
                self._save_slot(time_slot, "browse", label,
                                f"在{display_name}上刷了刷，什么都没看到",
                                sim_date=sim_date)
                return None

            results = []
            total_cost = 0

            for br in browse_results[:5]:  # 最多处理5条
                if not br.title or "失败" in br.title or "暂无" in br.title:
                    continue
                # 跨区块全局去重（避免不同时间段拉取到相同内容）
                title_key = br.title[:60]
                if title_key in self._seen_titles:
                    continue
                self._seen_titles.add(title_key)

                # ===== 1. 保存浏览记录（模拟模式下使用该区块的时间戳）=====
                if self._is_simulating:
                    h, m = map(int, time_slot.split(":"))
                    ts = f"{sim_date}T{time_slot}:00.000"
                else:
                    ts = datetime.now().isoformat()
                record = BrowseRecord(
                    timestamp=ts,
                    source=display_name,
                    title=br.title,
                    summary=br.summary or br.title[:60],
                    url=br.url,
                    category=br.category,
                )
                self.db.add_browse(record)

                # ===== 2. 判断是否感兴趣 =====
                is_interesting = should_be_interested(br.title, br.summary)

                if is_interesting:
                    # 感兴趣：AI生成想法（耗token）
                    try:
                        thought_text, importance = self.ai.think_about(
                            content=f"{br.title}。{br.summary}",
                            source=display_name,
                        )
                        thought_ts = ts  # 与浏览记录时间戳一致
                        thought = Thought(
                            timestamp=thought_ts,
                            source=f"{display_name} - {br.title[:30]}",
                            thought=thought_text,
                            importance=importance,
                            emotion=self.emotion.current.state.value,
                        )
                        self.db.add_thought(thought)
                        total_cost += 100
                        results.append({"title": br.title, "thought": thought_text[:100]})
                    except Exception as e:
                        logger.warning(f"思考失败: {e}")
                else:
                    # 不感兴趣：只记录想法为"不感兴趣"，不调AI（0 token）
                    thought_ts = ts
                    self.db.add_thought(Thought(
                        timestamp=thought_ts,
                        source=display_name,
                        thought=f"看到「{br.title}」，不感兴趣没点开看",
                        importance=1,
                        emotion=self.emotion.current.state.value,
                    ))

                # 知识提取：所有内容都尝试提取，不受兴趣判断影响
                try:
                    self.kb.learn_from_content(
                        content=f"{br.title}\n{br.summary}",
                        title=br.title,
                        source=display_name,
                        timestamp=ts,  # 使用区块时间戳
                    )
                except Exception as e:
                    logger.debug(f"知识提取失败: {e}")

            # 生成摘要
            if results:
                first_title = results[0]["title"][:30]
                summary_text = f"在{display_name}看了{len(results)}条内容，最感兴趣的是【{first_title}】"
            else:
                summary_text = f"在{display_name}逛了一圈，没找到特别感兴趣的"

            self._save_slot(time_slot, "browse", label, summary_text,
                            token_cost=total_cost, source_platform=display_name,
                            sim_date=sim_date)
            self.total_tokens += total_cost

            logger.info(f"  {display_name}: {len(results)} 条感兴趣")
            for r in results:
                logger.debug(f"    {r['title'][:40]}")

            return {"time": time_slot, "label": label, "content": summary_text,
                    "type": "browse", "results": results}

        except Exception as e:
            logger.warning(f"浏览块失败: {e}")
            self._save_slot(time_slot, "browse", label,
                            f"在{label}时信号不太好...",
                            sim_date=sim_date)
            return None

    def _do_reflect_block(self, block: dict, sim_date: str = "") -> Optional[dict]:
        time_slot = block["time"]

        try:
            # 生成模拟时间戳（使用区块时间，而非实时时间）
            if self._is_simulating:
                ts = f"{self._sim_date}T{time_slot}:00.000"
            else:
                ts = datetime.now().isoformat()

            prompt = ("天快结束了，回想一下今天发生的事情。用第一人称写一段睡前反思（3-5句话）说说："
                      "1. 今天最开心的一件事是什么 2. 今天学到或看到什么新东西 3. 有什么想对明天说的")

            response = self.ai._call_llm(prompt, system=None)
            content = response.content
            cost = response.total_tokens if hasattr(response, 'total_tokens') else 200
            self.total_tokens += cost
            self._record_tokens(cost)

            self._save_slot(time_slot, "reflect", block["label"], content,
                            token_cost=cost, sim_date=sim_date)
            logger.info(f"  反思: {content[:100]}...")

            return {"time": time_slot, "label": block["label"], "content": content,
                    "type": "reflect"}

        except Exception as e:
            logger.warning(f"反思块失败: {e}")
            return None

    def _write_diary(self, sim_date: str = ""):
        """如果今天还没有日记，调用 AI 写一篇"""
        today = self._today(sim_date)
        try:
            existing = None
            try:
                existing = list(filter(lambda d: d.get("date", "") == today, self.db.get_all_diary()))
            except Exception:
                pass
            if existing:
                logger.info(f"{today} 已有日记，跳过")
                return

            # 收集所有事件：routine 事件、browse 摘要、想法、睡前反思
            context_parts: list[str] = []
            for e in self.events:
                etype = e.get("type", "")
                label = e.get("label", "")
                content = str(e.get("content", ""))

                if etype == "reflect" and content and content not in ("pending", "pending..."):
                    context_parts.append(f"睡前反思：{content}")
                elif e.get("is_event") and content and content not in ("pending", "pending..."):
                    context_parts.append(f"{label}：{content}")
                elif etype == "browse" and e.get("results"):
                    browse_titles = [r.get("title", "")[:40] for r in e["results"]][:5]
                    if browse_titles:
                        context_parts.append(f"上网时感兴趣的内容：{'、'.join(browse_titles)}")

            if not context_parts:
                logger.warning(f"{today} 无有效事件，跳过写日记")
                return

            diary_context = "\n".join(context_parts)
            mood_label = self.emotion.current.state.value

            try:
                response = self.ai._call_llm(
                    f"""你是「小雪球」，今日情绪状态：{mood_label}。

今日发生的事：
{diary_context}

请根据以上真实事件写一篇日记。要求：
1. 第一行格式：「小雪球的日记」X月X日 天气：（自由发挥）
2. 内容必须基于上面列出的真实事件，不能瞎编
3. 200-300字，有情感，有细节，像真正的大学生写的日记
4. 结尾要有「晚安，今天的小雪球很乖。😌」或类似收尾语
5. 只输出日记正文，不要任何额外说明""",
                    system=None,
                )
                diary_text = response.content
                cost = getattr(response, "total_tokens", 0)
                self._record_tokens(cost)
                self.total_tokens += cost

                db_entry = DiaryEntry(
                    date=today,
                    summary=diary_text[:1000],
                    mood=mood_label,
                )
                self.db.add_diary(db_entry)
                logger.info(f"日记已写入: {today} ({cost} tokens)")
            except Exception as e:
                logger.warning(f"AI写日记失败: {e}")
                fallback = DiaryEntry(
                    date=today,
                    summary=f"今天发生了这些事：\n{diary_context[:500]}",
                    mood=mood_label,
                )
                self.db.add_diary(fallback)

        except Exception as e:
            logger.warning(f"写日记失败: {e}")


# 单例
_engine: Optional[DailyLifeEngine] = None


def get_engine() -> DailyLifeEngine:
    global _engine
    if _engine is None:
        _engine = DailyLifeEngine()
    return _engine
