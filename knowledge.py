"""
赛博人类 - 知识学习系统

小雪球不只是"看完说两句"，而是真正学进去。

核心流程：
1. 浏览内容 → AI提取知识点（"我学到了..."）
2. 存入知识库 → 分类、打分
3. 低谷时段 → 复习旧知识 → 加深理解
4. 关联 → 发现知识之间的联系
"""

import json
import random
from datetime import datetime, date, timedelta


class KnowledgeSystem:
    """
    知识学习系统。
    
    模拟一个人的学习过程：
    - 第一次看到 → 粗糙理解（confidence=1）
    - 复习一次 → 加深一点（confidence+1）
    - 能关联到其他知识 → 真的懂了
    - 长期不复习 → 遗忘
    """
    
    # 知识分类
    CATEGORIES = [
        "美食烹饪", "食品科学", "大学生活",
        "可爱动物", "游戏", "美妆穿搭",
        "生活常识", "人文地理", "科学知识",
        "娱乐影视", "其他"
    ]
    
    def __init__(self, memory):
        self.memory = memory
        self._create_tables()
    
    def _create_tables(self):
        conn = self.memory.conn
        conn.execute("""CREATE TABLE IF NOT EXISTS knowledge (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            concept TEXT NOT NULL,
            explanation TEXT,
            category TEXT DEFAULT '其他',
            source TEXT DEFAULT '',
            confidence INTEGER DEFAULT 1,
            review_count INTEGER DEFAULT 0,
            last_reviewed TEXT,
            related_ids TEXT DEFAULT '',
            forgotten INTEGER DEFAULT 0
        )""")
        conn.execute("""CREATE TABLE IF NOT EXISTS knowledge_reviews (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            knowledge_id INTEGER,
            review_date TEXT,
            understanding TEXT,
            confidence_before INTEGER,
            confidence_after INTEGER
        )""")
        conn.commit()
    
    def extract_from_content(self, content: str, source: str, ai_thought: str) -> dict:
        """
        从浏览内容和AI想法中提取知识点。
        
        返回：{ "has_knowledge": bool, "concept": str, "explanation": str, "category": str }
        
        注意：真正的知识提取应该由AI完成，
        这里先用一个简单版本——从AI的想法中提取。
        """
        result = {
            "has_knowledge": False,
            "concept": "",
            "explanation": "",
            "category": "其他"
        }
        
        thought = ai_thought.lower()
        
        # 判断AI是否有学到新东西
        learning_indicators = [
            "学到了", "第一次知道", "原来", "才发现",
            "了解了", "认识到了", "懂了", "知道了",
            "记住了", "get到",
            "竟然", "居然", "哇 ", "好奇",
            "好有意思", "有趣", "好神奇",
            "种草了", "马住了",
        ]
        
        has_learning = any(ind in thought for ind in learning_indicators)
        if not has_learning:
            return result
        
        # 尝试从内容中提取知识点
        # 取内容中比较有信息量的部分（第一段或标题）
        lines = content.split("\n")
        title = lines[0] if lines else ""
        
        # 分类判断
        category = self._guess_category(title + " " + ai_thought)
        
        # 从AI想法中提取学习点
        concept = title[:60] if len(title) > 10 else ai_thought[:60]
        explanation = ai_thought[:200]
        
        result["has_knowledge"] = True
        result["concept"] = concept
        result["explanation"] = explanation
        result["category"] = category
        
        return result
    
    def _guess_category(self, text: str) -> str:
        """根据文本猜测知识分类"""
        text_lower = text.lower()
        
        category_keywords = {
            "美食烹饪": ["美食", "好吃", "烹饪", "做饭", "食谱", "甜品", "蛋糕", "面包",
                        "咖啡", "奶茶", "零食", "探店", "外卖", "味道", "食材", "菜"],
            "食品科学": ["营养", "配料表", "食品", "健康饮食", "卡路里", "维生素", "蛋白质",
                        "添加剂", "保质期", "食品安全"],
            "可爱动物": ["猫", "狗", "博美", "宠物", "萌宠", "小动物", "狗狗", "猫咪"],
            "游戏": ["游戏", "steam", "switch", "通关", "攻略", "副本", "角色", "剧情"],
            "大学生活": ["大学", "宿舍", "开学", "期末", "校园", "上课", "考试", "考研"],
            "美妆穿搭": ["化妆", "美妆", "护肤", "穿搭", "平价", "口红", "粉底"],
            "生活常识": ["技巧", "方法", "教程", "省钱", "收纳", "清洁"],
        }
        
        for category, keywords in category_keywords.items():
            for kw in keywords:
                if kw in text_lower:
                    return category
        
        return "其他"
    
    def save_knowledge(self, concept: str, explanation: str, category: str, source: str):
        """保存一条新知识"""
        conn = self.memory.conn
        now = datetime.now().isoformat()
        
        # 检查是否已存在类似知识（避免重复）
        existing = conn.execute(
            "SELECT id, review_count FROM knowledge WHERE concept = ? AND forgotten = 0",
            (concept,)
        ).fetchone()
        
        if existing:
            # 已存在：更新为新的理解
            conn.execute(
                "UPDATE knowledge SET explanation = ?, review_count = review_count + 1, last_reviewed = ?, confidence = MIN(confidence + 1, 5) WHERE id = ?",
                (explanation, now, existing[0])
            )
            return existing[0]
        
        conn.execute(
            "INSERT INTO knowledge (timestamp, concept, explanation, category, source, confidence, last_reviewed) VALUES (?, ?, ?, ?, ?, 1, ?)",
            (now, concept, explanation, category, source, now)
        )
        conn.commit()
        return conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    
    def review_random(self, limit=3) -> list:
        """
        随机挑选几个知识点来复习。
        
        优先选：
        1. 很久没复习的
        2. 理解程度低的
        3. 从未复习过的
        """
        conn = self.memory.conn
        now = datetime.now().isoformat()
        
        # 挑需要复习的：confidence < 3 或 超过3天没复习
        three_days_ago = (datetime.now() - timedelta(days=3)).isoformat()
        candidates = conn.execute("""
            SELECT id, concept, explanation, category, confidence, review_count, last_reviewed
            FROM knowledge
            WHERE forgotten = 0
            ORDER BY 
                CASE WHEN last_reviewed < ? THEN 0 ELSE 1 END,
                confidence ASC,
                last_reviewed ASC
            LIMIT ?
        """, (three_days_ago, limit)).fetchall()
        
        reviewed = []
        for row in candidates:
            kid, concept, explanation, category, conf, count, last = row
            
            # 标记为已复习
            conn.execute(
                "UPDATE knowledge SET review_count = review_count + 1, last_reviewed = ?, confidence = MIN(confidence + 1, 5) WHERE id = ?",
                (now, kid)
            )
            
            # 记录复习历史
            conn.execute(
                "INSERT INTO knowledge_reviews (knowledge_id, review_date, understanding, confidence_before, confidence_after) VALUES (?, ?, ?, ?, ?)",
                (kid, date.today().isoformat(), "复习加深", conf, min(conf + 1, 5))
            )
            
            reviewed.append({
                "id": kid,
                "concept": concept,
                "explanation": explanation,
                "category": category,
                "confidence": conf,
                "new_confidence": min(conf + 1, 5)
            })
        
        conn.commit()
        return reviewed
    
    def forget_old(self, days=14):
        """
        超过指定天数没复习的旧知识 → 遗忘标记。
        """
        conn = self.memory.conn
        cutoff = (datetime.now() - timedelta(days=days)).isoformat()
        
        # confidence <= 2 且超过14天没复习
        forgotten = conn.execute("""
            SELECT id, concept FROM knowledge
            WHERE forgotten = 0 AND confidence <= 2 AND last_reviewed < ?
        """, (cutoff,)).fetchall()
        
        for row in forgotten:
            conn.execute("UPDATE knowledge SET forgotten = 1 WHERE id = ?", (row[0],))
        
        conn.commit()
        return len(forgotten)
    
    def get_stats(self) -> dict:
        """获取知识系统统计"""
        conn = self.memory.conn
        total = conn.execute("SELECT COUNT(*) FROM knowledge WHERE forgotten = 0").fetchone()[0]
        forgotten = conn.execute("SELECT COUNT(*) FROM knowledge WHERE forgotten = 1").fetchone()[0]
        
        # 按分类统计
        categories = {}
        for row in conn.execute("SELECT category, COUNT(*) FROM knowledge WHERE forgotten = 0 GROUP BY category"):
            categories[row[0]] = row[1]
        
        # 理解程度分布
        conf_dist = {}
        for i in range(1, 6):
            cnt = conn.execute("SELECT COUNT(*) FROM knowledge WHERE forgotten = 0 AND confidence = ?", (i,)).fetchone()[0]
            if cnt > 0:
                conf_dist[str(i)] = cnt
        
        return {
            "total": total,
            "forgotten": forgotten,
            "categories": categories,
            "confidence_distribution": conf_dist
        }
    
    def get_all_knowledge(self, limit=50) -> list:
        """获取所有知识列表"""
        conn = self.memory.conn
        rows = conn.execute("""
            SELECT id, timestamp, concept, explanation, category, source, confidence, review_count, last_reviewed
            FROM knowledge
            WHERE forgotten = 0
            ORDER BY confidence DESC, last_reviewed DESC
            LIMIT ?
        """, (limit,)).fetchall()
        return rows
