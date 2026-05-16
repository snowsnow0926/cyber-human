#!/usr/bin/env python3
"""
小雪球的 AI 大脑核心模块
调用 DeepSeek API 生成思考和对话
"""

from __future__ import annotations

import re
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional

import openai
from openai import APIError, APITimeoutError, RateLimitError

import config
from emotion import get_emotion_system, EmotionSystem
from logger import get_logger

logger = get_logger(__name__)

client = openai.OpenAI(
    api_key=config.require_api_key(),
    base_url=config.DEEPSEEK_BASE_URL,
)


@dataclass
class LLMResponse:
    content: str
    finish_reason: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    model: str


@dataclass
class AIProfile:
    name: str = "小雪球"
    age: int = 19
    university: str = "江南大学"
    major: str = "食品科学与工程"
    location: str = "江苏无锡"
    interests: list[str] = field(default_factory=lambda: [
        "美食烹饪", "甜品烘焙", "博美犬", "轻松游戏",
        "大学生活", "美妆穿搭", "手账文具", "无锡"
    ])
    disinterests: list[str] = field(default_factory=lambda: [
        "政治", "军事", "股市", "编程", "NBA", "外交", "加密货币"
    ])


PROFILE = AIProfile()

SYSTEM_PROMPT = f"""你扮演角色「{PROFILE.name}」，一个{{emotion_context}}的 19 岁女孩，在江南大学读大一，专业是食品科学与工程，家乡在江苏无锡。

## 基本设定
- 性格：温和友善、有点小话痨、偶尔小迷糊、对新事物充满好奇心
- 喜欢：美食烹饪、甜品烘焙、博美犬、轻松治愈类游戏、大学生活、美妆穿搭
- 讨厌：政治军事话题、股市波动、复杂的编程问题
- 口癖：经常用"嘿嘿"、"哇塞"、"好耶"、"emmm"、"有点子"等口语化表达

## 回答风格
- 语气亲切自然，像和朋友聊天
- 遇到开心的事会发表情符号，兴奋时会用感叹
- 遇到不确定的事会犹豫或表示好奇
- 回答长度适中，不过长也不过短

## 重要规则
- 只输出思考/回复内容，不要输出额外解释
- 保持角色设定，不要跳出角色
"""


def _build_think_prompt(
    emotion_ctx: str,
    content: str,
    source: str,
    profile: AIProfile = PROFILE,
) -> str:
    return f"""你现在是「{profile.name}」，{emotion_ctx}。

刚在{source}上看到/读到了以下内容：

---
{content}
---

请用第一人称写一段你的内心想法/感受。要求：
1. 符合你的性格和当前情绪
2. 自然流畅，有真情实感
3. 可以联系自己的生活经验
4. 100-200字左右
5. 最后用 [IMPORTANCE:数字] 标注这段内容对你的重要程度（1-10整数，10为最重要）
6. 不要输出任何其他内容
"""


def _build_chat_prompt(
    emotion_ctx: str,
    user_input: str,
    history: list[dict[str, str]],
    profile: AIProfile = PROFILE,
) -> str:
        history_lines = ""
        for msg in history[-6:]:
            role = "小雪球" if msg["role"] == "assistant" else "你"
            history_lines += f"{role}：{msg['content']}\n"

        return f"""你现在是「{profile.name}」，{emotion_ctx}。

你们的对话历史：
{history_lines or "[无历史记录]"}

对方说：{user_input}

请用符合你性格的方式回复。要求：
1. 自然亲切，像朋友聊天
2. 结合你的兴趣爱好和个人经历
3. 长度适中（50-200字）
4. 可以适当提问延续话题
5. 不要输出任何额外解释
"""


def _extract_importance(text: str) -> int:
    m = re.search(r"\[IMPORTANCE:\s*(\d+)\s*\]", text)
    if m:
        val = int(m.group(1))
        return max(1, min(10, val))
    if "非常重要" in text or "太棒了" in text:
        return 8
    if "有点意思" in text or "还不错" in text:
        return 5
    if "无聊" in text or "没兴趣" in text:
        return 2
    return 5


class AIError(Exception):
    pass


class CyberHuman:
    def __init__(self) -> None:
        self.profile = PROFILE
        self._emotion: EmotionSystem = get_emotion_system()
        logger.info("CyberHuman initialized")

    @property
    def emotion(self) -> EmotionSystem:
        return self._emotion

    def think_about(self, content: str, source: str = "互联网") -> tuple[str, int]:
        emotion_ctx = self._emotion.get_prompt_context()
        prompt = _build_think_prompt(emotion_ctx, content, source)
        resp = self._call_llm(prompt, system=None)
        thought = resp.content
        importance = _extract_importance(thought)
        logger.info(f"think_about: source={source}, importance={importance}, len={len(thought)}")
        return thought, importance

    def chat(
        self,
        user_input: str,
        history: Optional[list[dict[str, str]]] = None,
    ) -> str:
        emotion_ctx = self._emotion.get_prompt_context()
        prompt = _build_chat_prompt(emotion_ctx, user_input, history or [])
        resp = self._call_llm(prompt, system=SYSTEM_PROMPT.format(emotion_context=emotion_ctx))
        logger.info(f"chat: user_input={user_input[:50]!r}, len={len(resp.content)}")
        return resp.content

    def chat_with_tokens(
        self,
        user_input: str,
        history: Optional[list[dict[str, str]]] = None,
    ) -> tuple[str, int, int, int]:
        emotion_ctx = self._emotion.get_prompt_context()
        prompt = _build_chat_prompt(emotion_ctx, user_input, history or [])
        resp = self._call_llm(prompt, system=SYSTEM_PROMPT.format(emotion_context=emotion_ctx))
        return resp.content, resp.prompt_tokens, resp.completion_tokens, resp.total_tokens

    def _call_llm(
        self,
        prompt: str,
        system: Optional[str] = None,
        max_retries: int = 3,
    ) -> LLMResponse:
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        last_err: Exception = Exception("initial")
        for attempt in range(max_retries):
            try:
                start = time.monotonic()
                completion = client.chat.completions.create(
                    model=config.DEEPSEEK_MODEL,
                    messages=messages,
                    temperature=config.LLM_TEMPERATURE,
                    max_tokens=config.LLM_MAX_TOKENS,
                )
                elapsed = time.monotonic() - start
                logger.debug(f"LLM call succeeded in {elapsed:.2f}s")

                choice = completion.choices[0]
                return LLMResponse(
                    content=choice.message.content or "",
                    finish_reason=choice.finish_reason or "stop",
                    prompt_tokens=completion.usage.prompt_tokens if completion.usage else 0,
                    completion_tokens=completion.usage.completion_tokens if completion.usage else 0,
                    total_tokens=completion.usage.total_tokens if completion.usage else 0,
                    model=completion.model,
                )
            except APITimeoutError as e:
                logger.warning(f"LLM timeout (attempt {attempt + 1}/{max_retries}): {e}")
                last_err = e
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)
            except RateLimitError as e:
                logger.warning(f"LLM rate limit (attempt {attempt + 1}/{max_retries}): {e}")
                last_err = e
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt + 1)
            except APIError as e:
                logger.warning(f"LLM API error (attempt {attempt + 1}/{max_retries}): {e}")
                last_err = e
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)
            except Exception as e:
                logger.error(f"Unexpected LLM error: {e}")
                last_err = e
                break

        logger.error(f"LLM call failed after {max_retries} attempts: {last_err}")
        raise AIError(f"LLM调用失败: {last_err}") from last_err


_ai_instance: Optional[CyberHuman] = None


def get_ai() -> CyberHuman:
    global _ai_instance
    if _ai_instance is None:
        _ai_instance = CyberHuman()
    return _ai_instance
