"""
赛博人类 v0.4 - 核心记忆系统（方向B）

三层记忆架构 + 遗忘曲线 + 情绪标记 + 夜间巩固
"""

import sqlite3
from datetime import datetime, date, timedelta


class MemoryCore:
    """
    赛博人类的"大脑"——真正的记忆系统。
    
    三层记忆：
    - 短期 (short): 当天看到的，睡前就忘了
    - 中期 (mid): 持续几天到几周，经常回忆就记得
    - 长期 (long): 重要的事，能记住很久
    
    遗忘规则：
    - 短期超过24小时没被回忆 → 降级或遗忘
    - 中期超过7天没被回忆 → 降级
    - 重要程度 < 3 的记忆遗忘更快
    """
    
    TIERS = {"short": "短期", "mid": "中期", "long": "长期"}
    EMOTIONS = ["好奇", "开心", "困惑", "害怕", "伤心", "生气", "平静", "惊讶"]
    
    def __init__(self, memory):
        self.memory = memory
        self._ensure_columns()
    
    def _ensure_columns(self):
        """确保数据库有必要的列"""
        conn = self.memory.conn
        for col in ["memory_tier", "emotion", "last_recalled", "recall_count"]:
            try:
                conn.execute("ALTER TABLE thoughts ADD COLUMN %s TEXT DEFAULT ''" % col)
            except:
                pass
        try:
            conn.execute("ALTER TABLE thoughts ADD COLUMN recall_count INTEGER DEFAULT 0")
        except:
            pass
        
        # 每日巩固记录表
        conn.execute("""CREATE TABLE IF NOT EXISTS memory_consolidation (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL UNIQUE,
            consolidated_at TEXT,
            total_before INTEGER DEFAULT 0,
            promoted_to_mid INTEGER DEFAULT 0,
            promoted_to_long INTEGER DEFAULT 0,
            forgotten INTEGER DEFAULT 0,
            summary TEXT
        )""")
        conn.commit()
    
    def tag_thought(self, thought, importance, emotion=""):
        """
        给一条新想法标记记忆层级和情绪。
        返回记忆层级。
        """
        conn = self.memory.conn
        
        # 根据重要程度决定初始层级
        if importance >= 5:
            tier = "mid"  # 印象深刻的直接进中期
        elif importance >= 3:
            tier = "short"  # 普通的先进短期
        else:
            tier = "short"  # 没什么感觉的也是短期
        
        if not emotion:
            emotion = self._detect_emotion(thought)
        
        # 更新最新一条想法
        conn.execute(
            "UPDATE thoughts SET memory_tier=?, emotion=?, last_recalled=? WHERE id = (SELECT MAX(id) FROM thoughts)",
            (tier, emotion, datetime.now().isoformat())
        )
        conn.commit()
        
        return tier
    
    def _detect_emotion(self, text):
        """从文本中简单检测情绪关键词"""
        text = text[:200]
        emotions_map = [
            ("好奇", ["好奇", "想知道", "第一次", "没听说过", "是什么"]),
            ("开心", ["开心", "高兴", "温暖", "喜欢", "棒", "好治愈"]),
            ("困惑", ["困惑", "不明白", "不懂", "什么意思", "奇怪"]),
            ("害怕", ["害怕", "吓人", "可怕", "恐怖", "担心"]),
            ("伤心", ["伤心", "难过", "哭了", "难受", "遗憾"]),
            ("生气", ["生气", "可恶", "气", "讨厌", "烦"]),
            ("惊讶", ["哇", "天啊", "震惊", "没想到", "竟然"]),
        ]
        for emotion, keywords in emotions_map:
            for kw in keywords:
                if kw in text:
                    return emotion
        return "平静"
    
    def get_context_memories(self, limit=5):
        """
        获取当前最相关的记忆（给AI做上下文）。
        优先选：长期 > 中期 > 短期
        同层级内：重要程度高的 > 最近回忆的
        """
        conn = self.memory.conn
        now = datetime.now()
        
        # 先从长期记忆里筛选
        rows = conn.execute("""
            SELECT id, thought, source, importance, emotion, memory_tier, last_recalled
            FROM thoughts 
            WHERE memory_tier = 'long'
            ORDER BY importance DESC, last_recalled ASC
            LIMIT ?
        """, (limit,)).fetchall()
        
        if len(rows) < limit:
            # 不够的话补充中期记忆
            more = conn.execute("""
                SELECT id, thought, source, importance, emotion, memory_tier, last_recalled
                FROM thoughts 
                WHERE memory_tier = 'mid'
                ORDER BY importance DESC, last_recalled ASC
                LIMIT ?
            """, (limit - len(rows),)).fetchall()
            rows.extend(more)
        
        if len(rows) < limit:
            # 还差的话从短期里挑重要的
            more = conn.execute("""
                SELECT id, thought, source, importance, emotion, memory_tier, last_recalled
                FROM thoughts 
                WHERE memory_tier = 'short' AND importance >= 3
                ORDER BY last_recalled ASC
                LIMIT ?
            """, (limit - len(rows),)).fetchall()
            rows.extend(rows)
        
        # 更新这些记忆的回忆时间
        for row in rows:
            conn.execute(
                "UPDATE thoughts SET last_recalled=?, recall_count=recall_count+1 WHERE id=?",
                (datetime.now().isoformat(), row[0])
            )
        conn.commit()
        
        return rows
    
    def consolidate(self):
        """
        夜间记忆巩固（睡前执行）。
        
        规则：
        - 重要程度 5 的短期记忆 → 提升为中期
        - 重要程度 >= 4 的中期记忆 → 提升为长期
        - 重要程度 <= 2 的短期记忆 → 遗忘（标记）
        - 超过 7 天没被回忆的中期记忆 → 降级为短期
        """
        conn = self.memory.conn
        today = date.today().isoformat()
        now = datetime.now().isoformat()
        
        # 统计
        total = conn.execute("SELECT COUNT(*) FROM thoughts").fetchone()[0]
        promoted_mid = 0
        promoted_long = 0
        forgotten = 0
        
        # 短期 → 中期（重要程度高）
        c = conn.execute("""
            SELECT id FROM thoughts 
            WHERE memory_tier='short' AND importance >= 4
        """)
        ids = [r[0] for r in c.fetchall()]
        if ids:
            conn.execute(
                "UPDATE thoughts SET memory_tier='mid' WHERE id IN (%s)" % ",".join("?" * len(ids)),
                ids
            )
            promoted_mid = len(ids)
        
        # 中期 → 长期（重要程度高且被回忆过）
        c = conn.execute("""
            SELECT id FROM thoughts 
            WHERE memory_tier='mid' AND importance >= 4 AND recall_count > 0
        """)
        ids = [r[0] for r in c.fetchall()]
        if ids:
            conn.execute(
                "UPDATE thoughts SET memory_tier='long' WHERE id IN (%s)" % ",".join("?" * len(ids)),
                ids
            )
            promoted_long = len(ids)
        
        # 遗忘不重要、很少回忆的短期记忆
        seven_days_ago = (datetime.now() - timedelta(days=7)).isoformat()
        c = conn.execute("""
            SELECT id FROM thoughts 
            WHERE memory_tier='short' AND importance <= 2 
            AND (last_recalled IS NULL OR last_recalled < ?)
        """, (seven_days_ago,))
        ids = [r[0] for r in c.fetchall()]
        if ids:
            # 标记为遗忘（改为 mid 带 forget 标记或者直接删除）
            # 这里我们保留但标记遗忘
            for tid in ids:
                conn.execute(
                    "UPDATE thoughts SET memory_tier='short', importance=0 WHERE id=?",
                    (tid,)
                )
            forgotten = len(ids)
        
        # 保存巩固记录
        conn.execute(
            "INSERT OR REPLACE INTO memory_consolidation (date, consolidated_at, total_before, promoted_to_mid, promoted_to_long, forgotten, summary) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (today, now, total, promoted_mid, promoted_long, forgotten,
             "巩固完成: %d条提升->中期, %d条提升->长期, %d条被遗忘" % (promoted_mid, promoted_long, forgotten))
        )
        conn.commit()
        
        return {
            "total": total,
            "promoted_mid": promoted_mid,
            "promoted_long": promoted_long,
            "forgotten": forgotten
        }
    
    def get_memory_summary(self):
        """获取记忆系统状态摘要"""
        conn = self.memory.conn
        short = conn.execute("SELECT COUNT(*) FROM thoughts WHERE memory_tier='short'").fetchone()[0]
        mid = conn.execute("SELECT COUNT(*) FROM thoughts WHERE memory_tier='mid'").fetchone()[0]
        long_ = conn.execute("SELECT COUNT(*) FROM thoughts WHERE memory_tier='long'").fetchone()[0]
        consolidated = conn.execute("SELECT COUNT(*) FROM memory_consolidation").fetchone()[0]
        
        return {
            "tiers": {"短期": short, "中期": mid, "长期": long_},
            "total": short + mid + long_,
            "nights_consolidated": consolidated
        }
