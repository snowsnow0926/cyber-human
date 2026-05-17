#!/usr/bin/env python3
"""
日常生活模拟引擎 v2.0
简化架构：12时段引擎，记忆系统驱动想法生成
"""

from __future__ import annotations

import random
from datetime import datetime, date
from typing import Any, Optional

from logger import get_logger
from memory import BrowseRecord, Thought, DiaryEntry, get_db

logger = get_logger(__name__)


# ── 时间块配置 ──────────────────────────────────────────────────────────────

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
    "起床": [
        "打了个哈欠，翻了个身，不想起来", "闹钟响了三遍才醒", "醒来发现嘴角有口水印",
        "做了个奇怪的梦，但想不起来了", "今天阳光真好，心情不错", "好困……再躺五分钟",
        "今天不知道为什么特别精神",
    ],
    "早餐": [
        "随便吃了点东西", "想了半天不知道吃什么", "早餐凉了，凑合吃",
        "去食堂买了包子", "泡了杯麦片，懒得分身",
    ],
    "出门散步": [
        "在小区里走了走", "今天天气不错", "路上没什么人",
        "看到一只鸟在树上叫", "风吹过来凉凉的", "去校门口拿了快递",
    ],
    "午餐时间": [
        "随便吃了点外卖", "今天点了一家新店，一般般",
        "想了好久才决定吃什么", "午饭比平时晚了一个小时", "食堂的红烧肉还不错",
    ],
    "下午茶/摸鱼": [
        "发了会儿呆", "没什么事干，躺着", "喝了杯水，继续摸鱼",
        "有点困，但睡不着", "刷了会儿手机", "做了会儿作业",
    ],
    "洗漱整理": [
        "洗完澡感觉整个人都清醒了", "刷牙的时候对着镜子发了会儿呆",
        "今天好累，简单洗洗就睡了", "洗澡的时候突然想到一件白天的事",
        "敷了张面膜，感觉皮肤好多了",
    ],
}

BROWSE_SOURCES = [
    ("bilibili", "B站热门", 3),
    ("baidu", "百度热搜", 2),
    ("zhihu", "知乎热榜", 2),
    ("ithome", "IT之家", 1),
    ("people", "人民网", 1),
    ("xiaohongshu", "小红书", 2),
]


# ── 引擎核心 ────────────────────────────────────────────────────────────────

class DailyLifeEngine:
    """日常生活模拟引擎 v2.0 — 记忆驱动"""

    def __init__(self, db=None, ai=None, browser=None, character=None) -> None:
        from memory import get_db
        from cyber_human import get_ai
        from browser import get_browser
        from character import should_be_interested

        self.db = db or get_db()
        self.ai = ai or get_ai()
        self.browser = browser or get_browser()
        self._should_be_interested = should_be_interested
        self.events: list[dict[str, Any]] = []
        self.total_tokens = 0
        self._is_simulating = False
        self._block_index = 0
        self._sim_date: str = ""
        self._seen_titles: set[str] = set()
        self._emotion_state: str = "平静"
        self._emotion_int: float = 0.5
        logger.info("DailyLifeEngine v2.0 initialized")

    def _today(self, sim_date: str = "") -> str:
        if sim_date and sim_date != "today":
            return sim_date
        return date.today().isoformat()

    def _make_ts(self, time_slot: str, sim_date: str = "") -> str:
        if self._is_simulating:
            return f"{self._sim_date}T{time_slot}:00.000"
        return datetime.now().isoformat()

    def _record_tokens(self, tokens: int) -> None:
        if tokens <= 0:
            return
        try:
            from memory import TokenUsage
            with self.db.get_conn() as conn:
                conn.execute(
                    "INSERT INTO token_usage (timestamp, prompt_tokens, completion_tokens, total_tokens) VALUES (?, 0, 0, ?)",
                    (datetime.now().isoformat(), tokens),
                )
        except Exception as e:
            logger.warning(f"记录token失败: {e}")

    def _save_slot(
        self,
        time_slot: str,
        activity_type: str,
        label: str,
        content: str,
        is_event: int = 0,
        token_cost: float = 0.0,
        source_platform: str = "",
        sim_date: str = "",
    ) -> None:
        self.db.save_slot(
            date_str=self._today(sim_date),
            time_slot=time_slot,
            activity_type=activity_type,
            label=label,
            content=content,
            is_event=is_event,
            token_cost=token_cost,
            source_platform=source_platform,
        )

    # ── 主流程 ─────────────────────────────────────────────────────────────

    def run_full_day(self, sim_date: str = "") -> list[dict[str, Any]]:
        if not sim_date or sim_date == "today":
            sim_date = date.today().isoformat()
        self._sim_date = sim_date
        self._is_simulating = True
        logger.warning(f">>> {sim_date} 的一天开始了......")
        logger.warning("=" * 40)

        self.events = []
        self.total_tokens = 0
        self._block_index = 0
        self._seen_titles.clear()

        for block in TIME_BLOCKS:
            result = self._execute_block(block, sim_date)
            if result:
                self.events.append(result)

        self._do_end_of_day(sim_date)

        logger.warning("=" * 40)
        logger.info(f">>> 今天执行了 {len(self.events)} 个时间块, 消耗 ~{self.total_tokens} tokens")
        return self.events

    def _execute_block(self, block: dict, sim_date: str = "") -> Optional[dict[str, Any]]:
        time_slot = block["time"]
        label = block["label"]
        block_type = block["type"]
        self._block_index += 1

        logger.info(f"[{self._block_index}/12] {time_slot} {label}......")

        if block_type == "sleep":
            self._save_slot(time_slot, "sleep", label, "zzz......", sim_date=sim_date)
            return {"time": time_slot, "label": label, "content": "zzz...", "type": "sleep"}

        if block_type == "routine":
            return self._do_routine(block, sim_date)
        if block_type == "browse":
            return self._do_browse(block, sim_date)
        if block_type == "reflect":
            return self._do_reflect(block, sim_date)

        return None

    # ── Routine 块 ───────────────────────────────────────────────────────

    def _do_routine(self, block: dict, sim_date: str = "") -> Optional[dict[str, Any]]:
        label = block["label"]
        time_slot = block["time"]

        try:
            roll = random.random()

            if roll < 0.70:
                content = random.choice(ROUTINE_TEMPLATES.get(label, ["没什么特别的"]))
                self._save_slot(time_slot, "routine", label, content, sim_date=sim_date)
                return {"time": time_slot, "label": label, "content": content, "type": "routine"}
            else:
                content, cost = self._generate_mini_event(label)
                self._save_slot(time_slot, "routine", label, content,
                                is_event=1, token_cost=float(cost), sim_date=sim_date)
                self.total_tokens += cost
                return {"time": time_slot, "label": label, "content": content,
                        "type": "event", "is_event": True}
        except Exception as e:
            logger.warning(f"routine块失败: {e}")
            self._save_slot(time_slot, "routine", label, "今天有点累，不想动..", sim_date=sim_date)
            return None

    def _generate_mini_event(self, label: str) -> tuple[str, int]:
        prompt = f"""现在是{label}的时间。
发生了一件日常生活里的小事，用第一人称简单说说发生了什么，你是什么感觉。（2-3句话）
要有画面感，符合一个19岁女大学生的真实状态。"""
        try:
            response = self.ai._call_llm(prompt, system=None)
            content = response.content
            cost = getattr(response, "total_tokens", 0) or 100
            self._record_tokens(cost)
            return content, cost
        except Exception as e:
            logger.warning(f"mini事件生成失败: {e}")
            return f"在{label}的时候遇到了一点小事......", 50

    # ── Browse 块 ─────────────────────────────────────────────────────────

    def _do_browse(self, block: dict, sim_date: str = "") -> Optional[dict[str, Any]]:
        label = block["label"]
        time_slot = block["time"]

        try:
            hour = int(time_slot.split(":")[0])
            if hour < 12:
                weights = [3, 1, 1, 1, 1, 1]
            elif hour < 17:
                weights = [1, 1, 2, 2, 1, 2]
            else:
                weights = [3, 1, 1, 1, 1, 2]

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

            try:
                browse_results = self.browser.fetch(source_name, timeout=10)
            except Exception as e:
                logger.warning(f"从 {source_name} 获取失败: {e}")
                self._save_slot(time_slot, "browse", label,
                                f"在{display_name}上刷了刷，但没加载出来...", sim_date=sim_date)
                return None

            if not browse_results:
                self._save_slot(time_slot, "browse", label,
                                f"在{display_name}上刷了刷，什么都没看到", sim_date=sim_date)
                return None

            results: list[dict[str, str]] = []
            total_cost = 0
            ts = self._make_ts(time_slot, sim_date)

            for br in browse_results[:5]:
                if not br.title or "失败" in br.title or "暂无" in br.title:
                    continue
                title_key = br.title[:60]
                if title_key in self._seen_titles:
                    continue
                self._seen_titles.add(title_key)

                record = BrowseRecord(
                    timestamp=ts,
                    source=display_name,
                    title=br.title,
                    summary=br.summary or br.title[:60],
                    url=br.url,
                    category=br.category,
                )
                self.db.add_browse(record)

                try:
                    is_interesting = self._should_be_interested(br.title, br.summary)
                except Exception:
                    is_interesting = True

                if is_interesting:
                    try:
                        keywords = self._extract_keywords(br.title + " " + (br.summary or ""))
                        thought_text, importance = self.ai.think_about(
                            content=f"{br.title}。{br.summary}",
                            source=display_name,
                            keywords=keywords,
                        )
                    except Exception as e:
                        logger.warning(f"思考生成失败: {e}")
                        thought_text = f"看到「{br.title}」，虽然挺感兴趣的但没来得及细想"
                        importance = 5

                    self.db.add_thought(Thought(
                        timestamp=ts,
                        source=f"{display_name} - {br.title[:30]}",
                        thought=thought_text,
                        emotion=self._emotion_state,
                        importance=importance,
                    ))
                    total_cost += 100
                    results.append({"title": br.title, "thought": thought_text[:100]})
                else:
                    self.db.add_thought(Thought(
                        timestamp=ts,
                        source=display_name,
                        thought=f"看到「{br.title}」，不感兴趣没点开看",
                        emotion=self._emotion_state,
                        importance=1,
                    ))

            if results:
                first_title = results[0]["title"][:30]
                summary_text = f"在{display_name}看了{len(results)}条内容，最感兴趣的是【{first_title}】"
            else:
                summary_text = f"在{display_name}逛了一圈，没找到特别感兴趣的"

            self._save_slot(time_slot, "browse", label, summary_text,
                            token_cost=float(total_cost), source_platform=display_name,
                            sim_date=sim_date)
            self.total_tokens += total_cost

            logger.info(f"  {display_name}: {len(results)} 条感兴趣")
            return {"time": time_slot, "label": label, "content": summary_text,
                    "type": "browse", "results": results}

        except Exception as e:
            logger.warning(f"浏览块失败: {e}")
            self._save_slot(time_slot, "browse", label,
                            f"在{label}时信号不太好...", sim_date=sim_date)
            return None

    def _extract_keywords(self, text: str) -> list[str]:
        import re
        chinese_words = re.findall(r"[\u4e00-\u9fff]{2,}", text)
        seen = set()
        keywords = []
        for w in chinese_words:
            if w not in seen and len(w) >= 2:
                seen.add(w)
                keywords.append(w)
                if len(keywords) >= 10:
                    break
        return keywords[:10]

    # ── Reflect 块 ────────────────────────────────────────────────────────

    def _do_reflect(self, block: dict, sim_date: str = "") -> Optional[dict[str, Any]]:
        time_slot = block["time"]

        try:
            ts = self._make_ts(time_slot, sim_date)
            reflect_text = self.ai.reflect_on_memories()
            cost = 200
            self.total_tokens += cost
            self._record_tokens(cost)

            self._save_slot(time_slot, "reflect", block["label"], reflect_text,
                            token_cost=float(cost), sim_date=sim_date)
            logger.info(f"  反思: {reflect_text[:100]}...")

            return {"time": time_slot, "label": block["label"],
                    "content": reflect_text, "type": "reflect"}
        except Exception as e:
            logger.warning(f"反思块失败: {e}")
            return None

    # ── 每日结束 ──────────────────────────────────────────────────────────

    def _do_end_of_day(self, sim_date: str = "") -> None:
        self.db.decay_all()
        consolidation = self.db.consolidate()
        logger.info(f"记忆巩固: {consolidation}")
        self._is_simulating = False


# ── 单例 ─────────────────────────────────────────────────────────────────────

_engine: Optional[DailyLifeEngine] = None


def get_engine() -> DailyLifeEngine:
    global _engine
    if _engine is None:
        _engine = DailyLifeEngine()
    return _engine
