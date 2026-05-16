#!/usr/bin/env python3
"""
知识学习模块
从浏览内容中提取知识要点，按分类存储，支持间隔复习
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional

import config
from logger import get_logger
from memory import Database, get_db

logger = get_logger(__name__)

CATEGORIES = [
    "美食烹饪", "食品科学", "大学生活", "可爱动物",
    "游戏", "美妆穿搭", "生活常识", "人文地理",
    "科学知识", "娱乐影视", "其他",
]


@dataclass
class KnowledgeItem:
    concept: str
    explanation: str
    category: str
    confidence: int = 1


class KnowledgeExtractor:
    SYSTEM_PROMPT = """你是一个知识整理助手。请从以下内容中提取1-3个有价值的知识要点。

要求：
1. 每个知识要点包含「概念」和「解释」两部分
2. 判断内容属于哪个分类（美食烹饪/食品科学/大学生活/可爱动物/游戏/美妆穿搭/生活常识/人文地理/科学知识/娱乐影视/其他）
3. 用JSON数组格式输出：
[{"concept": "概念名", "explanation": "解释内容", "category": "分类"}]
4. 如果内容无知识价值，返回空数组 []
5. 不要输出任何额外内容
"""

    def __init__(self, client: Any = None) -> None:
        self._client = client

    def extract(self, content: str) -> list[KnowledgeItem]:
        try:
            import openai
            client = self._client or openai.OpenAI(
                api_key=config.DEEPSEEK_API_KEY,
                base_url=config.DEEPSEEK_BASE_URL,
            )
            response = client.chat.completions.create(
                model=config.DEEPSEEK_MODEL,
                messages=[
                    {"role": "system", "content": self.SYSTEM_PROMPT},
                    {"role": "user", "content": content[:2000]},
                ],
                temperature=0.3,
                max_tokens=512,
            )
            text = response.choices[0].message.content or ""
            logger.debug(f"Knowledge extraction raw: {text[:200]}")
            items = self._parse_json(text)
            logger.info(f"Extracted {len(items)} knowledge items from content")
            return items
        except Exception as e:
            logger.warning(f"Knowledge extraction failed: {e}")
            return []

    def _parse_json(self, text: str) -> list[KnowledgeItem]:
        import json
        match = re.search(r"\[[\s\S]*\]", text)
        if not match:
            return []
        try:
            data = json.loads(match.group())
            return [
                KnowledgeItem(
                    concept=str(item.get("concept", "")),
                    explanation=str(item.get("explanation", "")),
                    category=str(item.get("category", "其他")),
                )
                for item in data
                if isinstance(item, dict) and item.get("concept")
            ]
        except Exception:
            return []


class KnowledgeBase:
    def __init__(self, db: Optional[Database] = None) -> None:
        self.db = db or get_db()
        self.extractor = KnowledgeExtractor()
        logger.info("KnowledgeBase initialized")

    def learn_from_content(
        self,
        content: str,
        title: str,
        source: str,
    ) -> int:
        items = self.extractor.extract(f"标题：{title}\n内容：{content}")
        saved = 0
        for item in items:
            try:
                with self.db.get_cursor() as cursor:
                    cursor.execute(
                        """INSERT INTO knowledge
                           (timestamp, concept, explanation, category, confidence)
                           VALUES (?, ?, ?, ?, ?)""",
                        (datetime.now().isoformat(), item.concept,
                         item.explanation, item.category, item.confidence),
                    )
                    saved += 1
            except Exception as e:
                logger.warning(f"Failed to save knowledge item: {e}")
        logger.info(f"Saved {saved}/{len(items)} knowledge items from [{source}]")
        return saved

    def get_all(self, limit: int = 100) -> list[dict[str, Any]]:
        try:
            with self.db.get_cursor() as cursor:
                cursor.execute(
                    "SELECT * FROM knowledge ORDER BY timestamp DESC LIMIT ?",
                    (limit,),
                )
                return [dict(row) for row in cursor.fetchall()]
        except Exception:
            return []

    def get_by_category(self, category: str) -> list[dict[str, Any]]:
        try:
            with self.db.get_cursor() as cursor:
                cursor.execute(
                    "SELECT * FROM knowledge WHERE category = ? ORDER BY timestamp DESC",
                    (category,),
                )
                return [dict(row) for row in cursor.fetchall()]
        except Exception:
            return []

    def review_knowledge(self, knowledge_id: int, confidence_delta: int = 1) -> None:
        try:
            with self.db.get_cursor() as cursor:
                cursor.execute(
                    """UPDATE knowledge
                       SET review_count = review_count + 1,
                           last_reviewed = ?,
                           confidence = CASE
                               WHEN confidence + ? > 5 THEN 5
                               ELSE confidence + ?
                           END
                       WHERE id = ?""",
                    (datetime.now().isoformat(), confidence_delta, confidence_delta, knowledge_id),
                )
                logger.debug(f"Reviewed knowledge id={knowledge_id}, delta={confidence_delta}")
        except Exception as e:
            logger.error(f"Failed to review knowledge: {e}")

    def get_review_due(self, limit: int = 10) -> list[dict[str, Any]]:
        try:
            with self.db.get_cursor() as cursor:
                cursor.execute(
                    """SELECT * FROM knowledge
                       WHERE review_count < 5
                       ORDER BY confidence ASC, review_count ASC
                       LIMIT ?""",
                    (limit,),
                )
                return [dict(row) for row in cursor.fetchall()]
        except Exception:
            return []

    def get_stats(self) -> dict[str, Any]:
        try:
            with self.db.get_cursor() as cursor:
                total = cursor.execute(
                    "SELECT COUNT(*) as c FROM knowledge"
                ).fetchone()["c"]
                by_cat: dict[str, int] = {}
                for cat in CATEGORIES:
                    c = cursor.execute(
                        "SELECT COUNT(*) as c FROM knowledge WHERE category = ?",
                        (cat,),
                    ).fetchone()["c"]
                    if c > 0:
                        by_cat[cat] = c
                return {"total": total, "by_category": by_cat}
        except Exception:
            return {"total": 0, "by_category": {}}


def get_knowledge_base() -> KnowledgeBase:
    return KnowledgeBase()
