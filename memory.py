"""
赛博人类 - 记忆模块
"""

import sqlite3
from datetime import datetime, date

class Memory:
    def __init__(self, db_path: str = "cyber_memory.db"):
        self.conn = sqlite3.connect(db_path)
        self._create_tables()
        self._migrate()

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

    def _migrate(self):
        cursor = self.conn.cursor()
        cursor.execute("CREATE TABLE IF NOT EXISTS daily_schedule (id INTEGER PRIMARY KEY AUTOINCREMENT, date TEXT, time_slot TEXT, activity_type TEXT, label TEXT, content TEXT, is_event INTEGER DEFAULT 0, event_type TEXT DEFAULT '', token_cost INTEGER DEFAULT 0, source_platform TEXT DEFAULT '', created_at TEXT DEFAULT '', continuation TEXT DEFAULT '')")
        cursor.execute("CREATE TABLE IF NOT EXISTS memory_consolidation (id INTEGER PRIMARY KEY AUTOINCREMENT, date TEXT NOT NULL UNIQUE, consolidated_at TEXT, total_before INTEGER DEFAULT 0, promoted_to_mid INTEGER DEFAULT 0, promoted_to_long INTEGER DEFAULT 0, forgotten INTEGER DEFAULT 0, summary TEXT)")
        cursor.execute("CREATE TABLE IF NOT EXISTS dialogue_memory (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id TEXT, user_message TEXT, ai_reply TEXT, context TEXT, timestamp TEXT)")
        cursor.execute("CREATE TABLE IF NOT EXISTS knowledge_reviews (id INTEGER PRIMARY KEY AUTOINCREMENT, knowledge_id INTEGER, review_date TEXT, understanding TEXT, confidence_before INTEGER, confidence_after INTEGER)")
        self.conn.commit()

    def remember_dialogue(self, user_id, user_message, ai_reply, context=""):
        now = __import__('datetime').datetime.now().isoformat()
        self.conn.execute("INSERT INTO dialogue_memory (user_id, user_message, ai_reply, context, timestamp) VALUES (?, ?, ?, ?, ?)", (user_id, user_message, ai_reply, context, now))
        self.conn.commit()
    
    def get_recent_dialogues(self, user_id="", limit=5):
        if user_id:
            rows = self.conn.execute("SELECT user_message, ai_reply, timestamp FROM dialogue_memory WHERE user_id = ? ORDER BY timestamp DESC LIMIT ?", (user_id, limit))
        else:
            rows = self.conn.execute("SELECT user_message, ai_reply, timestamp FROM dialogue_memory ORDER BY timestamp DESC LIMIT ?", (limit,))
        return [{"user": r[0], "ai": r[1], "time": r[2]} for r in rows.fetchall()]
    
    def train(self):
        """
        AI 自训练：复习短期记忆，把重要的提升到中期。
        在 auto 模式最后自动调用。
        """
        try:
            from memory_core import MemoryCore as _MC
            mc = _MC(self)
            result = mc.consolidate()
            print("  [AI自训练] 完成: %d条提升->中期, %d条提升->长期, %d条被遗忘" % (
                result.get("promoted_mid", 0),
                result.get("promoted_long", 0),
                result.get("forgotten", 0)
            ))
            return result
        except Exception as e:
            print("  [AI自训练] 失败: " + str(e))
            return {}
    
    def close(self):
        self.conn.close()
