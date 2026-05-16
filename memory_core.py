#!/usr/bin/env python3
"""
三层记忆架构模块
短期记忆 → 中期记忆 → 长期记忆，基于重要度和回忆频率自动晋级/遗忘
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from logger import get_logger
from memory import Database, get_db

logger = get_logger(__name__)


@dataclass
class MemoryTier:
    name: str
    min_importance: int
    recall_threshold: int
    decay_days: int


TIERS: dict[str, MemoryTier] = {
    "short": MemoryTier("短期记忆", 1, 0, 1),
    "mid": MemoryTier("中期记忆", 4, 2, 14),
    "long": MemoryTier("长期记忆", 7, 5, 365),
}


class MemoryConsolidation:
    def __init__(self, db: Optional[Database] = None) -> None:
        self.db = db or get_db()
        logger.info("MemoryConsolidation initialized")

    def promote_short_to_mid(self) -> int:
        try:
            with self.db.get_cursor() as cursor:
                rows = cursor.execute(
                    """SELECT id FROM thoughts
                       WHERE memory_tier = 'short' AND importance >= ?""",
                    (TIERS["mid"].min_importance,),
                ).fetchall()
                promoted = 0
                for row in rows:
                    cursor.execute(
                        "UPDATE thoughts SET memory_tier = 'mid' WHERE id = ?",
                        (row["id"],),
                    )
                    promoted += 1
                logger.info(f"Promoted {promoted} thoughts from short to mid")
                return promoted
        except Exception as e:
            logger.error(f"Failed to promote short to mid: {e}")
            return 0

    def promote_mid_to_long(self) -> int:
        try:
            with self.db.get_cursor() as cursor:
                rows = cursor.execute(
                    """SELECT id FROM thoughts
                       WHERE memory_tier = 'mid'
                         AND importance >= ?
                         AND recall_count >= ?""",
                    (TIERS["long"].min_importance, TIERS["long"].recall_threshold),
                ).fetchall()
                promoted = 0
                for row in rows:
                    cursor.execute(
                        "UPDATE thoughts SET memory_tier = 'long' WHERE id = ?",
                        (row["id"],),
                    )
                    promoted += 1
                logger.info(f"Promoted {promoted} thoughts from mid to long")
                return promoted
        except Exception as e:
            logger.error(f"Failed to promote mid to long: {e}")
            return 0

    def forget_weak(self) -> int:
        try:
            with self.db.get_cursor() as cursor:
                rows = cursor.execute(
                    """SELECT id FROM thoughts
                       WHERE memory_tier = 'short'
                         AND importance <= 2
                         AND recall_count = 0""",
                ).fetchall()
                forgotten = 0
                for row in rows:
                    cursor.execute("DELETE FROM thoughts WHERE id = ?", (row["id"],))
                    forgotten += 1
                logger.info(f"Forgotten {forgotten} weak short-term memories")
                return forgotten
        except Exception as e:
            logger.error(f"Failed to forget weak memories: {e}")
            return 0

    def consolidate(self) -> dict[str, int]:
        logger.info("Starting nightly memory consolidation")
        promoted_short = self.promote_short_to_mid()
        promoted_mid = self.promote_mid_to_long()
        forgotten = self.forget_weak()
        result = {
            "promoted_to_mid": promoted_short,
            "promoted_to_long": promoted_mid,
            "forgotten": forgotten,
        }
        logger.info(f"Consolidation complete: {result}")
        return result

    def get_summary(self) -> dict[str, int]:
        try:
            with self.db.get_cursor() as cursor:
                total = cursor.execute(
                    "SELECT COUNT(*) as c FROM thoughts"
                ).fetchone()["c"]
                by_tier: dict[str, int] = {}
                for tier in ["short", "mid", "long"]:
                    c = cursor.execute(
                        "SELECT COUNT(*) as c FROM thoughts WHERE memory_tier = ?",
                        (tier,),
                    ).fetchone()["c"]
                    by_tier[tier] = c
                return {"total": total, **by_tier}
        except Exception as e:
            logger.error(f"Failed to get memory summary: {e}")
            return {"total": 0, "short": 0, "mid": 0, "long": 0}


def get_consolidation() -> MemoryConsolidation:
    return MemoryConsolidation()
