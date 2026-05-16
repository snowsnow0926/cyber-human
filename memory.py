#!/usr/bin/env python3
"""
记忆管理模块
SQLite 持久化存储，支持浏览记录、想法、日记等
"""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime, date
from pathlib import Path
from typing import Any, Generator, Optional

import config
from logger import get_logger

logger = get_logger(__name__)


@dataclass
class BrowseRecord:
    id: Optional[int] = None
    timestamp: str = ""
    source: str = ""
    title: str = ""
    summary: str = ""
    url: str = ""
    category: str = ""


@dataclass
class Thought:
    id: Optional[int] = None
    timestamp: str = ""
    source: str = ""
    thought: str = ""
    mood: str = ""
    importance: int = 5
    memory_tier: str = "short"
    emotion: str = ""
    recall_count: int = 0


@dataclass
class DiaryEntry:
    id: Optional[int] = None
    date: str = ""
    summary: str = ""
    mood: str = ""


@dataclass
class TokenUsage:
    id: Optional[int] = None
    timestamp: str = ""
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    model: str = ""


class Database:
    _instance: Optional["Database"] = None

    def __init__(self, db_path: Optional[Path] = None) -> None:
        self.db_path: Path = db_path or config.DB_PATH
        self._conn: Optional[sqlite3.Connection] = None
        logger.info(f"Database instance created: {self.db_path}")

    @classmethod
    def get_instance(cls) -> "Database":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @contextmanager
    def get_conn(self) -> Generator[sqlite3.Connection, None, None]:
        if self._conn is None:
            self._conn = sqlite3.connect(
                str(self.db_path),
                check_same_thread=False,
                detect_types=sqlite3.PARSE_DECLTYPES,
            )
            self._conn.row_factory = sqlite3.Row
            self._ensure_tables()
            logger.debug(f"DB connection opened: {self.db_path}")

        try:
            yield self._conn
        except sqlite3.Error as e:
            logger.error(f"Database error: {e}")
            raise

    @contextmanager
    def get_cursor(self) -> Generator[sqlite3.Cursor, None, None]:
        with self.get_conn() as conn:
            cursor = conn.cursor()
            try:
                yield cursor
                conn.commit()
            except sqlite3.Error as e:
                conn.rollback()
                logger.error(f"Transaction error: {e}")
                raise

    def _ensure_tables(self) -> None:
        with self.get_conn() as conn:
            cursor = conn.cursor()
            cursor.executescript("""
                CREATE TABLE IF NOT EXISTS browse_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    source TEXT,
                    title TEXT,
                    summary TEXT,
                    url TEXT,
                    category TEXT DEFAULT ''
                );
                CREATE TABLE IF NOT EXISTS thoughts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    source TEXT,
                    thought TEXT,
                    mood TEXT DEFAULT '',
                    importance INTEGER DEFAULT 5,
                    memory_tier TEXT DEFAULT 'short',
                    emotion TEXT DEFAULT '',
                    recall_count INTEGER DEFAULT 0
                );
                CREATE TABLE IF NOT EXISTS diary (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date TEXT UNIQUE NOT NULL,
                    summary TEXT,
                    mood TEXT DEFAULT ''
                );
                CREATE TABLE IF NOT EXISTS token_usage (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    prompt_tokens INTEGER DEFAULT 0,
                    completion_tokens INTEGER DEFAULT 0,
                    total_tokens INTEGER DEFAULT 0,
                    model TEXT DEFAULT ''
                );
                CREATE TABLE IF NOT EXISTS daily_schedule (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date TEXT NOT NULL,
                    time_slot TEXT,
                    activity_type TEXT,
                    label TEXT,
                    content TEXT,
                    is_event INTEGER DEFAULT 0,
                    token_cost REAL DEFAULT 0.0
                );
                CREATE TABLE IF NOT EXISTS knowledge (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    concept TEXT,
                    explanation TEXT,
                    category TEXT DEFAULT '',
                    confidence INTEGER DEFAULT 1,
                    review_count INTEGER DEFAULT 0,
                    last_reviewed TEXT DEFAULT ''
                );
                CREATE TABLE IF NOT EXISTS memory_consolidation (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date TEXT UNIQUE NOT NULL,
                    promoted_to_mid INTEGER DEFAULT 0,
                    promoted_to_long INTEGER DEFAULT 0,
                    forgotten INTEGER DEFAULT 0
                );
                CREATE TABLE IF NOT EXISTS emotions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    state TEXT,
                    intensity REAL DEFAULT 0.5,
                    triggers TEXT DEFAULT ''
                );
                CREATE INDEX IF NOT EXISTS idx_browse_timestamp ON browse_log(timestamp);
                CREATE INDEX IF NOT EXISTS idx_thoughts_timestamp ON thoughts(timestamp);
                CREATE INDEX IF NOT EXISTS idx_thoughts_tier ON thoughts(memory_tier);
                CREATE INDEX IF NOT EXISTS idx_knowledge_category ON knowledge(category);
            """)
            logger.debug("Database tables ensured")

    def add_browse(self, record: BrowseRecord) -> int:
        with self.get_cursor() as cursor:
            cursor.execute(
                """INSERT INTO browse_log (timestamp, source, title, summary, url, category)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (record.timestamp, record.source, record.title,
                 record.summary, record.url, record.category),
            )
            logger.debug(f"Added browse record: {record.title[:30]}")
            return cursor.lastrowid or 0

    def add_thought(self, thought: Thought) -> int:
        with self.get_cursor() as cursor:
            cursor.execute(
                """INSERT INTO thoughts (timestamp, source, thought, mood, importance, memory_tier, emotion, recall_count)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (thought.timestamp, thought.source, thought.thought,
                 thought.mood, thought.importance, thought.memory_tier,
                 thought.emotion, thought.recall_count),
            )
            logger.debug(f"Added thought: tier={thought.memory_tier}, importance={thought.importance}")
            return cursor.lastrowid or 0

    def add_diary(self, entry: DiaryEntry) -> int:
        with self.get_cursor() as cursor:
            cursor.execute(
                "INSERT OR REPLACE INTO diary (date, summary, mood) VALUES (?, ?, ?)",
                (entry.date, entry.summary, entry.mood),
            )
            logger.debug(f"Added/updated diary: {entry.date}")
            return cursor.lastrowid or 0

    def add_token_usage(self, usage: TokenUsage) -> int:
        with self.get_cursor() as cursor:
            cursor.execute(
                """INSERT INTO token_usage (timestamp, prompt_tokens, completion_tokens, total_tokens, model)
                   VALUES (?, ?, ?, ?, ?)""",
                (usage.timestamp, usage.prompt_tokens, usage.completion_tokens,
                 usage.total_tokens, usage.model),
            )
            return cursor.lastrowid or 0

    def save_emotion(
        self,
        state: str,
        intensity: float,
        triggers: str,
    ) -> None:
        try:
            with self.get_cursor() as cursor:
                cursor.execute(
                    """INSERT INTO emotions (timestamp, state, intensity, triggers)
                       VALUES (?, ?, ?, ?)""",
                    (datetime.now().isoformat(), state, intensity, triggers),
                )
        except sqlite3.Error as e:
            logger.error(f"Failed to save emotion: {e}")

    def get_today_browses(self) -> list[dict[str, Any]]:
        today = date.today().isoformat()
        try:
            with self.get_cursor() as cursor:
                cursor.execute(
                    "SELECT * FROM browse_log WHERE timestamp LIKE ? ORDER BY timestamp DESC",
                    (f"{today}%",),
                )
                return [dict(row) for row in cursor.fetchall()]
        except sqlite3.Error:
            return []

    def get_today_thoughts(self) -> list[dict[str, Any]]:
        today = date.today().isoformat()
        try:
            with self.get_cursor() as cursor:
                cursor.execute(
                    "SELECT * FROM thoughts WHERE timestamp LIKE ? ORDER BY timestamp DESC",
                    (f"{today}%",),
                )
                return [dict(row) for row in cursor.fetchall()]
        except sqlite3.Error:
            return []

    def get_all_thoughts(self, limit: int = 100) -> list[dict[str, Any]]:
        try:
            with self.get_cursor() as cursor:
                cursor.execute(
                    "SELECT * FROM thoughts ORDER BY timestamp DESC LIMIT ?",
                    (limit,),
                )
                return [dict(row) for row in cursor.fetchall()]
        except sqlite3.Error:
            return []

    def get_all_diary(self) -> list[dict[str, Any]]:
        try:
            with self.get_cursor() as cursor:
                cursor.execute("SELECT * FROM diary ORDER BY date DESC LIMIT 50")
                return [dict(row) for row in cursor.fetchall()]
        except sqlite3.Error:
            return []

    def get_stats(self) -> dict[str, Any]:
        try:
            today = date.today().isoformat()
            with self.get_cursor() as cursor:
                cursor.execute("SELECT COUNT(*) as c FROM browse_log")
                browse_count = cursor.fetchone()["c"]

                cursor.execute("SELECT COUNT(*) as c FROM thoughts")
                thought_count = cursor.fetchone()["c"]

                cursor.execute("SELECT COUNT(*) as c FROM diary")
                diary_count = cursor.fetchone()["c"]

                # Total tokens
                cursor.execute("SELECT SUM(total_tokens) as s FROM token_usage")
                total_tokens = cursor.fetchone()["s"] or 0

                # Today tokens
                cursor.execute(
                    "SELECT SUM(total_tokens) as s FROM token_usage WHERE timestamp LIKE ?",
                    (f"{today}%",)
                )
                today_tokens = cursor.fetchone()["s"] or 0

                # API calls total
                cursor.execute("SELECT COUNT(*) as c FROM token_usage")
                api_calls_total = cursor.fetchone()["c"]

                # API calls today
                cursor.execute(
                    "SELECT COUNT(*) as c FROM token_usage WHERE timestamp LIKE ?",
                    (f"{today}%",)
                )
                api_calls_today = cursor.fetchone()["c"]

                # Distinct sources
                cursor.execute("SELECT COUNT(DISTINCT source) as c FROM browse_log")
                source_count = cursor.fetchone()["c"]

                # Memory tiers
                cursor.execute(
                    """SELECT memory_tier, COUNT(*) as c FROM thoughts GROUP BY memory_tier"""
                )
                tier_counts = {row["memory_tier"]: row["c"] for row in cursor.fetchall()}

                # Consolidation stats
                cursor.execute("SELECT SUM(promoted_to_mid) as m, SUM(promoted_to_long) as l, SUM(forgotten) as f, COUNT(*) as n FROM memory_consolidation")
                cons = cursor.fetchone()
                nights = cons["n"] or 0
                promoted_mid = cons["m"] or 0
                promoted_long = cons["l"] or 0
                forgotten = cons["f"] or 0

                return {
                    "browse_count": browse_count,
                    "thought_count": thought_count,
                    "diary_count": diary_count,
                    "total_tokens": total_tokens,
                    "today_tokens": today_tokens,
                    "api_calls_total": api_calls_total,
                    "api_calls_today": api_calls_today,
                    "source_count": source_count,
                    "tier_counts": tier_counts,
                    "nights_consolidated": nights,
                    "promoted_mid": promoted_mid,
                    "promoted_long": promoted_long,
                    "forgotten": forgotten,
                }
        except sqlite3.Error as e:
            logger.error(f"Failed to get stats: {e}")
            return {
                "browse_count": 0, "thought_count": 0, "diary_count": 0,
                "total_tokens": 0, "today_tokens": 0,
                "api_calls_total": 0, "api_calls_today": 0,
                "source_count": 0, "tier_counts": {},
                "nights_consolidated": 0, "promoted_mid": 0,
                "promoted_long": 0, "forgotten": 0,
            }

    def get_today_schedule(self) -> list[dict[str, Any]]:
        today = date.today().isoformat()
        try:
            with self.get_cursor() as cursor:
                cursor.execute(
                    "SELECT * FROM daily_schedule WHERE date = ? ORDER BY time_slot",
                    (today,),
                )
                return [dict(row) for row in cursor.fetchall()]
        except sqlite3.Error:
            return []

    def get_browses_by_date(self, date_str: str) -> list[dict[str, Any]]:
        try:
            with self.get_cursor() as cursor:
                cursor.execute(
                    "SELECT * FROM browse_log WHERE timestamp LIKE ? ORDER BY timestamp DESC",
                    (f"{date_str}%",),
                )
                return [dict(row) for row in cursor.fetchall()]
        except sqlite3.Error:
            return []

    def get_thoughts_by_date(self, date_str: str) -> list[dict[str, Any]]:
        try:
            with self.get_cursor() as cursor:
                cursor.execute(
                    "SELECT * FROM thoughts WHERE timestamp LIKE ? ORDER BY timestamp DESC",
                    (f"{date_str}%",),
                )
                return [dict(row) for row in cursor.fetchall()]
        except sqlite3.Error:
            return []

    def get_schedule_by_date(self, date_str: str) -> list[dict[str, Any]]:
        try:
            with self.get_cursor() as cursor:
                cursor.execute(
                    "SELECT * FROM daily_schedule WHERE date = ? ORDER BY time_slot",
                    (date_str,),
                )
                return [dict(row) for row in cursor.fetchall()]
        except sqlite3.Error:
            return []

    def get_all_knowledge(self, limit: int = 100) -> list[dict[str, Any]]:
        try:
            with self.get_cursor() as cursor:
                cursor.execute(
                    "SELECT * FROM knowledge ORDER BY timestamp DESC LIMIT ?",
                    (limit,),
                )
                return [dict(row) for row in cursor.fetchall()]
        except sqlite3.Error:
            return []

    def get_knowledge_stats(self) -> dict[str, Any]:
        try:
            with self.get_cursor() as cursor:
                cursor.execute(
                    "SELECT category, COUNT(*) as c FROM knowledge GROUP BY category"
                )
                categories = {row["category"]: row["c"] for row in cursor.fetchall()}
                cursor.execute("SELECT COUNT(*) as c FROM knowledge")
                total = cursor.fetchone()["c"]
                return {"total": total, "by_category": categories}
        except sqlite3.Error:
            return {"total": 0, "by_category": {}}

    def save_schedule(self, date_str: str, schedule: list[dict[str, Any]]) -> None:
        try:
            with self.get_cursor() as cursor:
                for item in schedule:
                    cursor.execute(
                        """INSERT OR REPLACE INTO daily_schedule
                           (date, time_slot, activity_type, label, content, is_event, token_cost)
                           VALUES (?, ?, ?, ?, ?, ?, ?)""",
                        (date_str, item.get("time_slot", ""), item.get("activity_type", ""),
                         item.get("label", ""), item.get("content", ""),
                         item.get("is_event", 0), item.get("token_cost", 0.0)),
                    )
                logger.debug(f"Saved schedule for {date_str}: {len(schedule)} items")
        except sqlite3.Error as e:
            logger.error(f"Failed to save schedule: {e}")

    def close(self) -> None:
        if self._conn:
            self._conn.close()
            self._conn = None
            logger.debug("DB connection closed")


def get_db() -> Database:
    return Database.get_instance()
