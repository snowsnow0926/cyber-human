#!/usr/bin/env python3
"""
情感/情绪系统模块
为小雪球模拟动态情绪状态，影响 AI 回复风格
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any

import config
from logger import get_logger

logger = get_logger(__name__)


class EmotionState(Enum):
    HAPPY = "高兴"       # 开心、兴奋
    CALM = "平静"        # 平和、满足
    CURIOUS = "好奇"     # 好奇、有兴趣
    TIRED = "疲惫"       # 累了、困倦
    SAD = "失落"         # 难过、低落
    ANXIOUS = "焦虑"     # 紧张、不安
    EXCITED = "兴奋"     # 特别兴奋
    BORED = "无聊"       # 无聊、犯困


EMOTION_EMOJI: Dict[EmotionState, str] = {
    EmotionState.HAPPY: "😊",
    EmotionState.CALM: "😌",
    EmotionState.CURIOUS: "🤔",
    EmotionState.TIRED: "😪",
    EmotionState.SAD: "😢",
    EmotionState.ANXIOUS: "😰",
    EmotionState.EXCITED: "🤩",
    EmotionState.BORED: "😐",
}


@dataclass
class Emotion:
    state: EmotionState = EmotionState.CALM
    intensity: float = 0.5
    triggers: list[str] = field(default_factory=list)
    timestamp: datetime = field(default_factory=lambda: datetime.now())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "state": self.state.value,
            "intensity": round(self.intensity, 2),
            "triggers": self.triggers,
            "timestamp": self.timestamp.isoformat(),
            "emoji": EMOTION_EMOJI.get(self.state, "😐"),
        }


@dataclass
class EmotionSystem:
    current: Emotion = field(default_factory=Emotion)
    history: list[Emotion] = field(default_factory=list)

    _event_effects: Dict[str, float] = field(default_factory=lambda: {
        "美食": 0.15,
        "猫": 0.15,
        "狗": 0.15,
        "游戏": 0.12,
        "甜品": 0.13,
        "好成绩": 0.20,
        "天气好": 0.10,
        "睡眠不足": -0.15,
        "坏消息": -0.15,
        "下雨": -0.05,
        "社交": 0.08,
        "学习": -0.05,
        "无聊内容": -0.10,
        "好朋友": 0.18,
        "陌生人": -0.05,
    })

    _time_effects: Dict[str, float] = field(default_factory=lambda: {
        "morning": 0.05,
        "afternoon": 0.0,
        "evening": 0.08,
        "night": -0.05,
        "lunch": 0.10,
        "dinner": 0.10,
    })

    _state_transitions: Dict[EmotionState, list[EmotionState]] = field(default_factory=lambda: {
        EmotionState.HAPPY: [EmotionState.CALM, EmotionState.EXCITED, EmotionState.HAPPY],
        EmotionState.CALM: [EmotionState.CURIOUS, EmotionState.HAPPY, EmotionState.CALM],
        EmotionState.CURIOUS: [EmotionState.EXCITED, EmotionState.CALM, EmotionState.CURIOUS],
        EmotionState.TIRED: [EmotionState.SAD, EmotionState.CALM, EmotionState.BORED, EmotionState.TIRED],
        EmotionState.SAD: [EmotionState.CALM, EmotionState.ANXIOUS, EmotionState.SAD],
        EmotionState.ANXIOUS: [EmotionState.CALM, EmotionState.SAD, EmotionState.ANXIOUS],
        EmotionState.EXCITED: [EmotionState.HAPPY, EmotionState.CURIOUS, EmotionState.EXCITED],
        EmotionState.BORED: [EmotionState.CURIOUS, EmotionState.TIRED, EmotionState.BORED],
    })

    def get_time_slot(self) -> str:
        hour = datetime.now().hour
        if 6 <= hour < 9:
            return "morning"
        elif 9 <= hour < 11:
            return "morning"
        elif 11 <= hour < 14:
            return "lunch"
        elif 14 <= hour < 17:
            return "afternoon"
        elif 17 <= hour < 19:
            return "afternoon"
        elif 19 <= hour < 21:
            return "dinner"
        elif 21 <= hour < 23:
            return "evening"
        else:
            return "night"

    def apply_time_effect(self) -> None:
        slot = self.get_time_slot()
        delta = self._time_effects.get(slot, 0.0)
        if delta != 0.0:
            self.current.intensity = max(0.1, min(1.0, self.current.intensity + delta))
            logger.debug(f"Time effect [{slot}] delta={delta}, new intensity={self.current.intensity:.2f}")

    def apply_event(self, event_type: str) -> None:
        delta = self._event_effects.get(event_type, 0.0)
        old_state = self.current.state
        self.current.intensity = max(0.1, min(1.0, self.current.intensity + delta))
        if delta > 0.1:
            self.current.state = EmotionState.EXCITED if delta > 0.15 else EmotionState.HAPPY
        elif delta < -0.1:
            self.current.state = EmotionState.SAD if delta < -0.12 else EmotionState.TIRED
        if self.current.state != old_state:
            self.current.triggers.append(f"{event_type}->{self.current.state.value}")
        self.current.timestamp = datetime.now()
        logger.debug(f"Event [{event_type}] delta={delta}, new state={self.current.state.value}, intensity={self.current.intensity:.2f}")

    def step(self) -> None:
        self.apply_time_effect()
        self.current.state = random.choice(
            self._state_transitions.get(self.current.state, [self.current.state])
        )
        self.current.intensity = max(0.1, min(1.0, self.current.intensity + random.uniform(-0.05, 0.05)))
        self.current.timestamp = datetime.now()
        self.history.append(self.current)
        logger.debug(f"Emotion step: state={self.current.state.value}, intensity={self.current.intensity:.2f}")

    def apply_browse_result(self, title: str, summary: str) -> None:
        title_lower = title.lower()
        summary_lower = summary.lower()
        for keyword, delta in self._event_effects.items():
            if keyword in title_lower or keyword in summary_lower:
                self.apply_event(keyword)
                break

    def get_prompt_context(self) -> str:
        state = self.current.state.value
        intensity = self.current.intensity
        emoji = EMOTION_EMOJI.get(self.current.state, "😐")
        if intensity > 0.75:
            modifier = "非常"
        elif intensity > 0.55:
            modifier = "有点"
        elif intensity > 0.35:
            modifier = ""
        else:
            modifier = "略微"
        return f"[当前情绪：{modifier}{state} {emoji}]"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "current": self.current.to_dict(),
            "history_count": len(self.history),
            "time_slot": self.get_time_slot(),
        }


_default_emotion_system: Optional[EmotionSystem] = None


def get_emotion_system() -> EmotionSystem:
    global _default_emotion_system
    if _default_emotion_system is None:
        _default_emotion_system = EmotionSystem()
    return _default_emotion_system
