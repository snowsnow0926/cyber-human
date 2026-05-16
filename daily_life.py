#!/usr/bin/env python3
"""
日常生活模拟引擎
12 时段日程规划，驱动每日模拟循环
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from datetime import date, datetime, time
from typing import Any, Optional

from logger import get_logger
from memory import BrowseRecord, Database, Thought, TokenUsage, get_db
from browser import BrowseResult, HTTPBrowser, get_browser
from browser_bot import BrowserBot, BotBrowseResult, get_browser_bot
from knowledge import KnowledgeBase, get_knowledge_base
from emotion import EmotionSystem, get_emotion_system
from cyber_human import AIError, CyberHuman, get_ai

logger = get_logger(__name__)


@dataclass
class TimeSlot:
    start_time: str
    end_time: str
    activity_type: str
    label: str
    description: str
    interest_keywords: list[str] = field(default_factory=list)


TIME_SLOTS: list[TimeSlot] = [
    TimeSlot("08:00", "08:30", "wake_up", "起床", "新的一天开始，伸个懒腰迎接阳光", []),
    TimeSlot("08:30", "09:00", "breakfast", "早餐", "吃一顿丰盛的早餐开启美好一天", ["美食", "早餐", "食谱"]),
    TimeSlot("09:00", "11:00", "browse", "上网学习", "浏览感兴趣的内容，学习新知识", ["美食", "猫", "游戏", "大学", "无锡"]),
    TimeSlot("11:00", "12:00", "walk", "出门散步", "走出房间，呼吸新鲜空气", ["风景", "天气"]),
    TimeSlot("12:00", "14:00", "lunch", "午餐时间", "午餐时光，享受美食", ["美食", "午餐", "食堂"]),
    TimeSlot("14:00", "16:00", "explore", "下午探索", "下午时光，继续探索感兴趣的内容", ["游戏", "甜品", "美妆"]),
    TimeSlot("16:00", "18:00", "relax", "下午茶/摸鱼", "休闲放松时光，摸鱼时间到", ["游戏", "视频", "娱乐"]),
    TimeSlot("18:00", "20:00", "dinner", "晚餐/刷热搜", "晚餐时间，一边吃饭一边刷热搜", ["热搜", "美食", "新闻"]),
    TimeSlot("20:00", "22:00", "entertainment", "晚间娱乐", "晚间娱乐时光，打游戏或看视频", ["游戏", "电影", "娱乐"]),
    TimeSlot("22:00", "23:00", "cleanup", "洗漱整理", "洗漱整理，准备休息", []),
    TimeSlot("23:00", "00:00", "reflection", "睡前反思", "回顾一天，写下日记", []),
    TimeSlot("00:00", "08:00", "sleep", "进入梦乡", "进入梦乡休息，明天继续探索世界", []),
]


class DailyLifeEngine:
    
    # 情绪 → 表情映射
    MOOD_EMOJIS: dict[str, str] = {
        "好奇": "🤔",
        "开心": "😊",
        "困惑": "😕",
        "害怕": "😨",
        "伤心": "😢",
        "生气": "😤",
        "惊讶": "😲",
        "平静": "😐",
    }

    def __init__(
        self,
        db: Optional[Database] = None,
        ai: Optional[CyberHuman] = None,
        browser: Optional[HTTPBrowser] = None,
        browser_bot: Optional[BrowserBot] = None,
        knowledge_base: Optional[KnowledgeBase] = None,
        emotion_system: Optional[EmotionSystem] = None,
    ) -> None:
        self.db = db or get_db()
        self.ai = ai or get_ai()
        self.browser = browser or get_browser()
        self.browser_bot = browser_bot or get_browser_bot()
        self.kb = knowledge_base or get_knowledge_base()
        from weather import Weather
        from holiday import Holiday
        self.weather = Weather()
        self.holiday = Holiday()
        self.emotion = emotion_system or get_emotion_system()
        self.current_slot: Optional[TimeSlot] = None
        self.schedule: list[dict[str, Any]] = []
        logger.info("DailyLifeEngine initialized")

    def get_time_slot(self) -> TimeSlot:
        now = datetime.now()
        for slot in TIME_SLOTS:
            start_h, start_m = map(int, slot.start_time.split(":"))
            end_h, end_m = map(int, slot.end_time.split(":"))
            slot_start = now.replace(hour=start_h, minute=start_m, second=0)
            slot_end = now.replace(hour=end_h, minute=end_m, second=0)
            if start_h > end_h:
                slot_end = slot_end.replace(day=now.day + 1)
            if start_h <= now.hour < end_h:
                return slot
        return TIME_SLOTS[-1]

    def get_interests_for_slot(self, slot: TimeSlot) -> list[str]:
        if "早餐" in slot.label or "午餐" in slot.label or "晚餐" in slot.label:
            return ["美食", "食谱", "烹饪", "甜品"]
        if "娱乐" in slot.label or "摸鱼" in slot.label:
            return ["游戏", "视频", "娱乐", "热搜"]
        if "学习" in slot.label or "探索" in slot.label:
            return ["美食", "猫", "狗", "游戏", "大学", "美妆", "无锡"]
        return ["热搜", "新闻", "娱乐"]


    def get_mood_emoji(self) -> str:
        """获取小雪球当前的情绪表情"""
        try:
            mood = self.emotion.current.state.value
            if mood in self.MOOD_EMOJIS:
                return self.MOOD_EMOJIS[mood]
            return "😐"
        except Exception:
            return "😐"


    def _load_continuations(self) -> list[str]:
        """加载未完成的事件链"""
        try:
            from datetime import date
            today = date.today().isoformat()
            rows = self.db.get_conn().__enter__().execute(
                "SELECT continuation FROM daily_schedule WHERE date = ? AND continuation != '' ORDER BY time_slot DESC LIMIT 3",
                (today,)
            ).fetchall()
            return [r[0] for r in rows if r[0]]
        except:
            return []

    def _save_continuation(self, text: str) -> None:
        """保存事件链延续到明天"""
        try:
            from datetime import date
            today = date.today().isoformat()
            with self.db.get_cursor() as cursor:
                cursor.execute(
                    "UPDATE daily_schedule SET continuation = ? WHERE date = ? AND time_slot = (SELECT MAX(time_slot) FROM daily_schedule WHERE date = ?)",
                    (text, today, today)
                )
        except Exception as e:
            logger.warning(f"Failed to save continuation: {e}")

    def browse_and_think(
        self,
        slot: TimeSlot,
        max_browses: int = 3,
    ) -> list[dict[str, Any]]:
        interests = self.get_interests_for_slot(slot)
        results: list[dict[str, Any]] = []
        thought_count = 0
        total_browsed = 0

        for _ in range(max_browses):
            browse_results: list[BrowseResult] = []
            try:
                browse_results = self.browser.browse_random(interests, max_results=3)
            except Exception as e:
                logger.warning(f"Browse failed: {e}")

            if not browse_results:
                try:
                    bot_results = self.browser_bot.fetch("weibo")
                    for br in bot_results:
                        browse_results.append(
                            BrowseResult(br.source, br.title, br.summary, br.url, br.category)
                        )
                except Exception as e:
                    logger.warning(f"BrowserBot failed: {e}")

            total_browsed += len(browse_results)

            for item in browse_results:
                record = BrowseRecord(
                    timestamp=datetime.now().isoformat(),
                    source=item.source,
                    title=item.title,
                    summary=item.summary,
                    url=item.url,
                    category=item.category,
                )
                self.db.add_browse(record)

                try:
                    thought_text, importance = self.ai.think_about(
                        f"{item.title}。{item.summary}",
                        item.source,
                    )
                    thought = Thought(
                        timestamp=datetime.now().isoformat(),
                        source=item.source,
                        thought=thought_text,
                        importance=importance,
                        emotion=self.emotion.current.state.value,
                    )
                    self.db.add_thought(thought)
                    self.emotion.apply_browse_result(item.title, item.summary)
                    thought_count += 1
                    results.append({
                        "browse": item,
                        "thought": thought_text,
                        "importance": importance,
                    })
                except AIError as e:
                    logger.error(f"AI think failed: {e}")
                except Exception as e:
                    logger.error(f"Unexpected error in browse_and_think: {e}")

        logger.info(f"browse_and_think: browsed={total_browsed}, thoughts={thought_count}")
        return results

    def write_diary(self) -> str:
        from memory import DiaryEntry
        today = date.today().isoformat()
        try:
            thoughts = self.db.get_today_thoughts()
            browses = self.db.get_today_browses()
            context = (
                f"今天共浏览了 {len(browses)} 条内容，"
                f"产生了 {len(thoughts)} 条想法。"
            )
            if thoughts:
                top = sorted(thoughts, key=lambda t: t["importance"], reverse=True)[:3]
                context += " 印象最深的是：" + "。".join(
                    (t.get("thought") or "")[:50] for t in top
                )
            prompt = f"""你是「小雪球」，{self.emotion.get_prompt_context()}。

请根据以下信息，用符合你性格的方式写一篇今日日记：
{context}

要求：
1. 自然、真实、情感丰富
2. 200-300字左右
3. 结合今天的情绪状态
4. 可以加入对明天的期待
"""
            response = self.ai._call_llm(prompt, system=None)
            diary_text = response.content
            self.db.add_diary(
                DiaryEntry(
                    date=today,
                    summary=diary_text,
                    mood=self.emotion.current.state.value,
                )
            )
            logger.info(f"Diary written for {today}: {len(diary_text)} chars")
            return diary_text
        except Exception as e:
            logger.error(f"Failed to write diary: {e}")
            return ""

    def save_token_usage(
        self,
        prompt_tokens: int,
        completion_tokens: int,
        total_tokens: int,
        model: str,
    ) -> None:
        try:
            usage = TokenUsage(
                timestamp=datetime.now().isoformat(),
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=total_tokens,
                model=model,
            )
            self.db.add_token_usage(usage)
            self.db.save_emotion(
                self.emotion.current.state.value,
                self.emotion.current.intensity,
                ",".join(self.emotion.current.triggers),
            )
        except Exception as e:
            logger.error(f"Failed to save token usage: {e}")

    def run_slot(self, slot: Optional[TimeSlot] = None) -> dict[str, Any]:
        slot = slot or self.get_time_slot()
        self.current_slot = slot
        self.emotion.step()
        # Weather/holiday awareness
        try:
            weather = self.weather.get_today()
            weather_mod = self.weather.get_mood_modifier()
            events = self.holiday.get_today_events()
            special_days = [e["name"] for e in events if e["type"] != "season"]
            if special_days:
                logger.info(f"Today is special: {', '.join(special_days)}")
            if weather:
                weather_cond = weather.get("condition", "")
                logger.info(f"Weather: {weather_cond}, mood modifier: {weather_mod:+.1f}")
        except Exception as e:
            logger.debug(f"Weather/holiday check failed: {e}")
        logger.info(f"Running slot: {slot.label} ({slot.activity_type})")

        result: dict[str, Any] = {
            "slot": slot.label,
            "activity_type": slot.activity_type,
            "thoughts": [],
            "token_usage": {},
        }

        if slot.activity_type in ("browse", "explore", "dinner"):
            browse_results = self.browse_and_think(slot, max_browses=2)
            result["thoughts"] = browse_results

        elif slot.activity_type == "reflection":
            from memory import DiaryEntry
            diary = self.write_diary()
            result["diary"] = diary

        result["emotion"] = self.emotion.current.to_dict()
        logger.info(f"Slot '{slot.label}' completed")
        return result

    def run_full_day(self) -> list[dict[str, Any]]:
        today = date.today().isoformat()
        logger.info(f"=== Starting full day simulation: {today} ===")
        results: list[dict[str, Any]] = []
        active_slots = [s for s in TIME_SLOTS if s.activity_type not in ("sleep",)]
        for slot in active_slots:
            try:
                res = self.run_slot(slot)
                results.append(res)
            except Exception as e:
                logger.error(f"Slot '{slot.label}' failed: {e}")
                results.append({"slot": slot.label, "error": str(e)})
        logger.info(f"=== Full day simulation completed: {len(results)} slots ===")
        return results


def get_engine() -> DailyLifeEngine:
    return DailyLifeEngine()
