"""
赛博人类 - 记忆模块
"""

import sqlite3
from datetime import datetime, date

class Memory:
    def __init__(self, db_path: str = "cyber_memory.db"):
        self.conn = sqlite3.connect(db_path)
        self._create_tables()

    def _create_tables(self):
        cursor = self.conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS browse_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                source TEXT NOT NULL,
                title TEXT,
                summary TEXT,
                url TEXT
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS thoughts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                source TEXT,
                thought TEXT NOT NULL,
                mood TEXT,
                importance INTEGER DEFAULT 3
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS diary (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL UNIQUE,
                summary TEXT,
                mood TEXT
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS token_usage (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                prompt_tokens INTEGER DEFAULT 0,
                completion_tokens INTEGER DEFAULT 0,
                total_tokens INTEGER DEFAULT 0
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS daily_plan (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL UNIQUE,
                plan TEXT,
                mood TEXT,
                status TEXT DEFAULT "pending",
                executed_at TEXT,
                human_note TEXT
            )
        """)
        
        self.conn.commit()

    def remember_browse(self, source: str, title: str, summary: str, url: str = ""):
        now = datetime.now().isoformat()
        self.conn.execute(
            "INSERT INTO browse_log (timestamp, source, title, summary, url) VALUES (?, ?, ?, ?, ?)",
            (now, source, title, summary[:500], url)
        )
        self.conn.commit()

    def remember_thought(self, thought: str, source: str = "", mood: str = ""):
        now = datetime.now().isoformat()
        self.conn.execute(
            "INSERT INTO thoughts (timestamp, source, thought, mood) VALUES (?, ?, ?, ?)",
            (now, source, thought, mood)
        )
        self.conn.commit()

    def write_diary(self, summary: str, mood: str = ""):
        today = date.today().isoformat()
        self.conn.execute(
            "INSERT OR REPLACE INTO diary (date, summary, mood) VALUES (?, ?, ?)",
            (today, summary, mood)
        )
        self.conn.commit()

    def get_today_browse(self) -> list:
        today = date.today().isoformat()
        cursor = self.conn.execute(
            "SELECT * FROM browse_log WHERE timestamp LIKE ? ORDER BY timestamp DESC",
            (f"{today}%",)
        )
        return cursor.fetchall()

    def get_recent_thoughts(self, limit: int = 5) -> list:
        cursor = self.conn.execute(
            "SELECT * FROM thoughts ORDER BY timestamp DESC LIMIT ?",
            (limit,)
        )
        return cursor.fetchall()

    def close(self):
        self.conn.close()
