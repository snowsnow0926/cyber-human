#!/usr/bin/env python3
"""
记忆管理模块 v2.0
以记忆系统为核心：tag标签 + 重要性衰减 + 记忆召回 + 投喂支持
"""

from __future__ import annotations

import sqlite3
import threading
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime, date, timedelta
from pathlib import Path
from typing import Any, Generator, Optional

import config
from logger import get_logger

logger = get_logger(__name__)


# ── 数据模型 ─────────────────────────────────────────────────────────────────

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
    emotion: str = "平静"
    importance: int = 5
    tier: str = "短期"
    tags: str = ""
    last_recalled: str = ""
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


@dataclass
class FeedRecord:
    id: Optional[int] = None
    timestamp: str = ""
    user_content: str = ""
    ai_thought: str = ""
    tags: str = ""
    emotion: str = ""
    importance: int = 5


# ── 数据库核心 ───────────────────────────────────────────────────────────────

class Database:
    _instance: Optional["Database"] = None
    _local = threading.local()

    def __init__(self, db_path: Optional[Path] = None) -> None:
        self.db_path: Path = db_path or config.DB_PATH
        logger.info(f"Database initialized: {self.db_path}")

    @classmethod
    def get_instance(cls) -> "Database":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @contextmanager
    def get_conn(self) -> Generator[sqlite3.Connection, None, None]:
        conn = getattr(self._local, "conn", None)
        thread_id = threading.get_ident()
        if conn is None or thread_id != getattr(self._local, "thread_id", None):
            conn = sqlite3.connect(
                str(self.db_path),
                check_same_thread=False,
                detect_types=sqlite3.PARSE_DECLTYPES,
            )
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA busy_timeout=5000")
            conn.row_factory = sqlite3.Row
            self._local.conn = conn
            self._local.thread_id = thread_id
            logger.debug(f"DB connection opened for thread {thread_id}")

        self._ensure_tables(conn)
        try:
            yield conn
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

    def _ensure_tables(self, conn: sqlite3.Connection) -> None:
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
                emotion TEXT DEFAULT '平静',
                importance INTEGER DEFAULT 5,
                tier TEXT DEFAULT '短期',
                tags TEXT DEFAULT '',
                last_recalled TEXT DEFAULT '',
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
            CREATE TABLE IF NOT EXISTS feed_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                user_content TEXT,
                ai_thought TEXT,
                tags TEXT DEFAULT '',
                emotion TEXT DEFAULT '平静',
                importance INTEGER DEFAULT 5
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
            CREATE INDEX IF NOT EXISTS idx_thoughts_tier ON thoughts(tier);
        """)
        self._migrate_add_missing_columns(conn)
        logger.debug("Database tables ensured")

    def _migrate_add_missing_columns(self, conn: sqlite3.Connection) -> None:
        cursor = conn.cursor()
        migrations = [
            ("browse_log", [("category", "TEXT DEFAULT ''")]),
            ("thoughts", [
                ("tags", "TEXT DEFAULT ''"),
                ("last_recalled", "TEXT DEFAULT ''"),
                ("recall_count", "INTEGER DEFAULT 0"),
            ]),
            ("daily_schedule", [
                ("event_type", "TEXT DEFAULT ''"),
                ("source_platform", "TEXT DEFAULT ''"),
                ("created_at", "TEXT DEFAULT ''"),
            ]),
        ]
        for table, cols in migrations:
            cursor.execute(f"PRAGMA table_info({table})")
            existing = {row[1] for row in cursor.fetchall()}
            for col, coltype in cols:
                if col not in existing:
                    cursor.execute(f"ALTER TABLE {table} ADD COLUMN {col} {coltype}")
                    logger.info(f"Migration: added {table}.{col}")

    # ── 浏览记录 ─────────────────────────────────────────────────────────────

    def add_browse(self, record: BrowseRecord) -> int:
        with self.get_cursor() as cursor:
            cursor.execute(
                """INSERT INTO browse_log (timestamp, source, title, summary, url, category)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (record.timestamp, record.source, record.title,
                 record.summary, record.url, record.category),
            )
            logger.debug(f"Added browse: {record.title[:30]}")
            return cursor.lastrowid or 0

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

    # ── 想法（核心：记忆系统）──────────────────────────────────────────────────

    def add_thought(self, thought: Thought) -> int:
        with self.get_cursor() as cursor:
            cursor.execute(
                """INSERT INTO thoughts
                   (timestamp, source, thought, emotion, importance, tier, tags, last_recalled, recall_count)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (thought.timestamp, thought.source, thought.thought,
                 thought.emotion, thought.importance, thought.tier,
                 thought.tags, thought.last_recalled, thought.recall_count),
            )
            logger.debug(f"Added thought: tier={thought.tier}, importance={thought.importance}")
            return cursor.lastrowid or 0

    def save_thought(
        self,
        content: str,
        tags: str,
        emotion: str,
        importance: int = 5,
        source: str = "",
        timestamp: str = "",
    ) -> int:
        ts = timestamp or datetime.now().isoformat()
        tier = self._decide_tier(importance)
        thought = Thought(
            timestamp=ts,
            source=source,
            thought=content,
            emotion=emotion,
            importance=importance,
            tier=tier,
            tags=tags,
        )
        return self.add_thought(thought)

    def _decide_tier(self, importance: int) -> str:
        if importance >= 7:
            return "长期"
        elif importance >= 4:
            return "中期"
        return "短期"

    def recall_related(self, keywords: list[str], limit: int = 5) -> list[dict[str, Any]]:
        """
        关键词检索近30天相关记忆。
        召回时 importance +1，recall_count +1。
        """
        if not keywords:
            return []
        cutoff = (datetime.now() - timedelta(days=30)).isoformat()
        like_clauses = " OR ".join(["thought LIKE ?"] * len(keywords))
        params = [f"%{kw}%" for kw in keywords] + [cutoff]
        try:
            with self.get_cursor() as cursor:
                cursor.execute(
                    f"""SELECT * FROM thoughts
                        WHERE ({like_clauses})
                          AND timestamp >= ?
                        ORDER BY importance DESC, recall_count DESC
                        LIMIT ?""",
                    params + [limit],
                )
                results = [dict(row) for row in cursor.fetchall()]
                for row in results:
                    self.promote_memory(row["id"])
                return results
        except sqlite3.Error as e:
            logger.warning(f"recall_related failed: {e}")
            return []

    def promote_memory(self, thought_id: int) -> None:
        try:
            with self.get_cursor() as cursor:
                cursor.execute(
                    """UPDATE thoughts
                       SET importance = MIN(importance + 1, 10),
                           recall_count = recall_count + 1,
                           last_recalled = ?,
                           tier = ?
                       WHERE id = ?""",
                    (datetime.now().isoformat(),
                     self._decide_tier_from_id(cursor, thought_id),
                     thought_id),
                )
        except sqlite3.Error as e:
            logger.warning(f"promote_memory failed: {e}")

    def _decide_tier_from_id(self, cursor: sqlite3.Cursor, thought_id: int) -> str:
        cursor.execute("SELECT importance FROM thoughts WHERE id = ?", (thought_id,))
        row = cursor.fetchone()
        imp = row["importance"] if row else 5
        if imp >= 7:
            return "长期"
        elif imp >= 4:
            return "中期"
        return "短期"

    def forget_memory(self, thought_id: int) -> None:
        try:
            with self.get_cursor() as cursor:
                cursor.execute("DELETE FROM thoughts WHERE id = ? AND importance <= 1", (thought_id,))
                logger.debug(f"forget_memory: id={thought_id}")
        except sqlite3.Error as e:
            logger.warning(f"forget_memory failed: {e}")

    def decay_all(self) -> int:
        """所有记忆 importance -= 0.3，不能低于1"""
        try:
            with self.get_cursor() as cursor:
                cursor.execute(
                    """UPDATE thoughts
                       SET importance = MAX(importance - 1, 1)
                       WHERE tier = '短期'"""
                )
                affected = cursor.rowcount
                logger.info(f"decay_all: affected {affected} short-term memories")
                return affected
        except sqlite3.Error as e:
            logger.error(f"decay_all failed: {e}")
            return 0

    def consolidate(self) -> dict[str, int]:
        """每日睡前：升降级 + 遗忘"""
        promoted_short = 0
        promoted_mid = 0
        forgotten = 0
        try:
            with self.get_cursor() as cursor:
                cursor.execute(
                    """UPDATE thoughts
                       SET tier = '中期', importance = MIN(importance + 1, 10)
                       WHERE tier = '短期' AND importance >= 4"""
                )
                promoted_short = cursor.rowcount

                cursor.execute(
                    """UPDATE thoughts
                       SET tier = '长期', importance = MIN(importance + 1, 10)
                       WHERE tier = '中期'
                         AND importance >= 7
                         AND recall_count >= 2"""
                )
                promoted_mid = cursor.rowcount

                cursor.execute(
                    """DELETE FROM thoughts
                       WHERE tier = '短期' AND importance <= 1 AND recall_count = 0"""
                )
                forgotten = cursor.rowcount

            logger.info(f"consolidate: short→mid {promoted_short}, mid→long {promoted_mid}, forgotten {forgotten}")
            return {
                "promoted_short": promoted_short,
                "promoted_mid": promoted_mid,
                "forgotten": forgotten,
            }
        except sqlite3.Error as e:
            logger.error(f"consolidate failed: {e}")
            return {"promoted_short": 0, "promoted_mid": 0, "forgotten": 0}

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

    def get_thoughts_by_tag(self, tag: str, limit: int = 50) -> list[dict[str, Any]]:
        try:
            with self.get_cursor() as cursor:
                cursor.execute(
                    "SELECT * FROM thoughts WHERE tags LIKE ? ORDER BY timestamp DESC LIMIT ?",
                    (f"%{tag}%", limit),
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

    def get_top_memories(self, limit: int = 3) -> list[dict[str, Any]]:
        """获取印象最深的记忆（最高importance）"""
        try:
            with self.get_cursor() as cursor:
                cursor.execute(
                    """SELECT * FROM thoughts
                       ORDER BY importance DESC, recall_count DESC
                       LIMIT ?""",
                    (limit,),
                )
                return [dict(row) for row in cursor.fetchall()]
        except sqlite3.Error:
            return []

    # ── 日记 ─────────────────────────────────────────────────────────────────

    def add_diary(self, entry: DiaryEntry) -> int:
        with self.get_cursor() as cursor:
            cursor.execute(
                "INSERT OR REPLACE INTO diary (date, summary, mood) VALUES (?, ?, ?)",
                (entry.date, entry.summary, entry.mood),
            )
            return cursor.lastrowid or 0

    def get_all_diary(self) -> list[dict[str, Any]]:
        try:
            with self.get_cursor() as cursor:
                cursor.execute("SELECT * FROM diary ORDER BY date DESC LIMIT 50")
                return [dict(row) for row in cursor.fetchall()]
        except sqlite3.Error:
            return []

    # ── 时间表 ───────────────────────────────────────────────────────────────

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

    def save_slot(
        self,
        date_str: str,
        time_slot: str,
        activity_type: str,
        label: str,
        content: str,
        is_event: int = 0,
        token_cost: float = 0.0,
        source_platform: str = "",
    ) -> None:
        try:
            with self.get_cursor() as cursor:
                cursor.execute(
                    "DELETE FROM daily_schedule WHERE date = ? AND time_slot = ?",
                    (date_str, time_slot),
                )
                cursor.execute(
                    """INSERT INTO daily_schedule
                       (date, time_slot, activity_type, label, content, is_event,
                        token_cost, source_platform, created_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (date_str, time_slot, activity_type, label, content,
                     is_event, token_cost, source_platform, datetime.now().isoformat()),
                )
        except sqlite3.Error as e:
            logger.warning(f"save_slot failed: {e}")

    # ── 投喂日志 ─────────────────────────────────────────────────────────────

    def add_feed(self, feed: FeedRecord) -> int:
        with self.get_cursor() as cursor:
            cursor.execute(
                """INSERT INTO feed_log
                   (timestamp, user_content, ai_thought, tags, emotion, importance)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (feed.timestamp, feed.user_content, feed.ai_thought,
                 feed.tags, feed.emotion, feed.importance),
            )
            return cursor.lastrowid or 0

    def get_all_feeds(self, limit: int = 50) -> list[dict[str, Any]]:
        try:
            with self.get_cursor() as cursor:
                cursor.execute(
                    "SELECT * FROM feed_log ORDER BY timestamp DESC LIMIT ?",
                    (limit,),
                )
                return [dict(row) for row in cursor.fetchall()]
        except sqlite3.Error:
            return []

    # ── Token 统计 ────────────────────────────────────────────────────────────

    def add_token_usage(self, usage: TokenUsage) -> int:
        with self.get_cursor() as cursor:
            cursor.execute(
                """INSERT INTO token_usage
                   (timestamp, prompt_tokens, completion_tokens, total_tokens, model)
                   VALUES (?, ?, ?, ?, ?)""",
                (usage.timestamp, usage.prompt_tokens, usage.completion_tokens,
                 usage.total_tokens, usage.model),
            )
            return cursor.lastrowid or 0

    def get_stats(self) -> dict[str, Any]:
        today = date.today().isoformat()
        try:
            with self.get_cursor() as cursor:
                def count(table: str) -> int:
                    cursor.execute(f"SELECT COUNT(*) as c FROM {table}")
                    return cursor.fetchone()["c"]

                def sum_tokens(table: str = "token_usage", col: str = "total_tokens") -> int:
                    cursor.execute(f"SELECT SUM({col}) as s FROM {table}")
                    return cursor.fetchone()["s"] or 0

                cursor.execute(
                    "SELECT tier, COUNT(*) as c FROM thoughts GROUP BY tier"
                )
                tier_counts = {row["tier"]: row["c"] for row in cursor.fetchall()}

                return {
                    "browse_count": count("browse_log"),
                    "thought_count": count("thoughts"),
                    "diary_count": count("diary"),
                    "feed_count": count("feed_log"),
                    "total_tokens": sum_tokens(),
                    "today_tokens": cursor.execute(
                        "SELECT SUM(total_tokens) as s FROM token_usage WHERE timestamp LIKE ?",
                        (f"{today}%",)
                    ).fetchone()["s"] or 0,
                    "tier_counts": tier_counts,
                }
        except sqlite3.Error as e:
            logger.error(f"get_stats failed: {e}")
            return {}

    # ── 清空数据 ─────────────────────────────────────────────────────────────

    def clear_today_data(self) -> dict[str, int]:
        today = date.today().isoformat()
        results = {}
        try:
            with self.get_cursor() as cursor:
                for table, col in [
                    ("browse_log", "timestamp"),
                    ("thoughts", "timestamp"),
                    ("daily_schedule", "date"),
                ]:
                    cursor.execute(f"DELETE FROM {table} WHERE {col} LIKE ?", (f"{today}%",))
                    results[table] = cursor.rowcount
            logger.info(f"clear_today_data: {results}")
            return results
        except sqlite3.Error as e:
            logger.error(f"clear_today_data failed: {e}")
            return {}

    def close(self) -> None:
        if hasattr(self._local, "conn") and self._local.conn:
            self._local.conn.close()
            self._local.conn = None
            logger.debug("DB connection closed")


def get_db() -> Database:
    return Database.get_instance()
