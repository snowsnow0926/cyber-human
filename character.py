#!/usr/bin/env python3
"""
角色设定模块 v2.0
精简：保留兴趣判断逻辑，提供关键词提取
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from logger import get_logger

logger = get_logger(__name__)


@dataclass
class CharacterProfile:
    name: str = "小雪球"
    gender: str = "女"
    age: int = 19
    school: str = "江南大学"
    location: str = "江苏无锡"
    major: str = "食品科学与工程"
    interests: list[str] = field(default_factory=lambda: [
        "美食", "烹饪", "甜品", "烘焙", "猫", "狗", "博美犬",
        "游戏", "大学", "美妆", "穿搭", "手账", "无锡", "电影",
    ])
    disinterests: list[str] = field(default_factory=lambda: [
        "政治", "军事", "股市", "编程", "NBA", "外交", "加密货币",
        "战争", "武器",
    ])

    def is_interested(self, keyword: str) -> bool:
        return any(kw in keyword for kw in self.interests)

    def is_disinterested(self, keyword: str) -> bool:
        return any(kw in keyword for kw in self.disinterests)

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "gender": self.gender,
            "age": self.age,
            "school": self.school,
            "location": self.location,
            "major": self.major,
        }


_default_profile: Optional[CharacterProfile] = None


def get_profile() -> CharacterProfile:
    global _default_profile
    if _default_profile is None:
        _default_profile = CharacterProfile()
        logger.info("CharacterProfile loaded: 小雪球")
    return _default_profile


def should_be_interested(title: str, summary: str = "") -> bool:
    """
    快速判断小雪球是否对内容感兴趣。
    第一层：关键词快速过滤
    第二层：AI 判断（处理语义层面）
    """
    profile = get_profile()
    text = (title + " " + summary).lower()

    for kw in profile.disinterests:
        if kw.lower() in text:
            return False

    for kw in profile.interests:
        if kw.lower() in text:
            return True

    try:
        from cyber_human import get_ai
        ai = get_ai()
        prompt = f"""你是「小雪球」，19岁江南大学大一女生，专业食品科学与工程。

她的兴趣：美食烹饪、甜品烘焙、博美犬、轻松游戏、大学生活、美妆穿搭、手账文具
她讨厌的话题：政治、军事、股市、编程、NBA、外交、加密货币

请判断小雪球对以下内容是否感兴趣。

标题：{title}
内容摘要：{summary[:200] if summary else "无"}

请只回复「感兴趣」或「不感兴趣」，不要其他内容。"""

        response = ai._call_llm(prompt, system=None)
        result = response.content.strip()
        interested = "感兴趣" in result
        logger.debug(f"AI兴趣判断: {title[:30]} -> {result}")
        return interested
    except Exception as e:
        logger.warning(f"AI兴趣判断失败，默认为感兴趣: {e}")
        return True
