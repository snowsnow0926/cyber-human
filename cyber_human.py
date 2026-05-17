#!/usr/bin/env python3
"""
小雪球的 AI 大脑核心模块 v2.0
调用 DeepSeek API 生成思考，核心闭环：记忆检索 → 生成想法 → 保存记忆
新增：投喂内容分析与标签提取
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
from logger import get_logger

logger = get_logger(__name__)

_client: Optional[openai.OpenAI] = None


def _get_client() -> openai.OpenAI:
    global _client
    if _client is None:
        _client = openai.OpenAI(
            api_key=config.require_api_key(),
            base_url=config.DEEPSEEK_BASE_URL,
        )
    return _client


# ── 数据模型 ─────────────────────────────────────────────────────────────────

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

SYSTEM_PROMPT = f"""你扮演角色「{PROFILE.name}」，一个 19 岁的女孩，在江南大学读大一，专业是食品科学与工程，家乡在江苏无锡。

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


# ── Prompt 构建 ─────────────────────────────────────────────────────────────

def _build_think_prompt(
    emotion_ctx: str,
    content: str,
    source: str,
    memory_context: str = "",
) -> str:
    return f"""你现在是「{PROFILE.name}」，{emotion_ctx}。

刚在{source}上看到/读到了以下内容：

---
{content}
---

{memory_context}

请用第一人称写一段你的内心想法/感受。要求：
1. 符合你的性格和当前情绪
2. 自然流畅，有真情实感
3. 可以联系自己的生活经验
4. 100-200字左右
5. 最后用 [IMPORTANCE:数字] 标注这段内容对你的重要程度（1-10整数，10为最重要）
6. 如果内容无聊/不感兴趣，直接写"不感兴趣没点开看"并给低重要度(1-3)
7. 不要输出任何其他内容
"""


def _build_feed_think_prompt(
    emotion_ctx: str,
    feed_content: str,
    memory_context: str = "",
) -> str:
    return f"""你现在是「{PROFILE.name}」，{emotion_ctx}。

你收到了主人投喂的一段信息：

---
{feed_content}
---

{memory_context}

请用第一人称写一段你对这个内容的想法/感受。要求：
1. 符合你的性格和当前情绪
2. 自然流畅，有真情实感
3. 可以联系自己的生活经验
4. 100-200字左右
5. 最后用 [IMPORTANCE:数字] 标注这段内容对你的重要程度（1-10整数，10为最重要）
6. 不要输出任何其他内容
"""


def _build_tag_extract_prompt(feed_content: str) -> str:
    return f"""你是一个内容分析助手。请分析以下内容，提取3-5个关键词标签。

内容：
---
{feed_content[:1000]}
---

要求：
1. 标签要能概括内容主题，用中文词语
2. 参考：小雪球的兴趣包括：美食、烹饪、烘焙、宠物（尤其博美犬）、游戏、大学生活、美妆、穿搭、手账、无锡、电影、娱乐
3. 用逗号分隔输出，不要其他内容
示例输出：美食,烹饪,生活
"""


def _build_reflect_prompt(
    emotion_ctx: str,
    top_memories: list[dict[str, Any]],
) -> str:
    mem_lines = ""
    for i, m in enumerate(top_memories, 1):
        mem_lines += f"{i}. {m.get('thought', '')[:80]}...\n"

    return f"""现在是睡前时间，「{PROFILE.name}」正在回想今天发生的事情。

{emotion_ctx}

今天印象最深的记忆：
{mem_lines}

请用第一人称写一段睡前反思（3-5句话），说说：
1. 今天最开心的一件事是什么
2. 今天学到或看到什么新东西
3. 有什么想对明天说的

保持小雪球的说话风格。
"""


# ── 工具函数 ─────────────────────────────────────────────────────────────────

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


def _extract_tags(text: str) -> str:
    m = re.search(r"\[TAGS:\s*([^\]]+)\s*\]", text)
    if m:
        return m.group(1).strip()
    if "美食" in text or "烹饪" in text or "烘焙" in text:
        return "美食,烹饪"
    if "博美" in text or "狗" in text or "宠物" in text:
        return "宠物,动物"
    if "游戏" in text:
        return "游戏"
    return "生活"


class AIError(Exception):
    pass


# ── AI 大脑 ───────────────────────────────────────────────────────────────────

class CyberHuman:
    def __init__(self) -> None:
        self.profile = PROFILE
        self._emotion_state: str = "平静"
        self._emotion_intensity: float = 0.5
        logger.info("CyberHuman v2.0 initialized")

    def _get_emotion_context(self) -> str:
        intensity = self._emotion_intensity
        state = self._emotion_state
        if intensity > 0.75:
            modifier = "非常"
        elif intensity > 0.55:
            modifier = "有点"
        elif intensity > 0.35:
            modifier = ""
        else:
            modifier = "略微"
        return f"[当前情绪：{modifier}{state}]"

    def set_emotion(self, state: str, intensity: float = 0.5) -> None:
        self._emotion_state = state
        self._emotion_intensity = intensity

    def think_about(
        self,
        content: str,
        source: str = "互联网",
        keywords: Optional[list[str]] = None,
    ) -> tuple[str, int]:
        """
        核心方法：浏览内容 → 检索记忆 → 生成想法 → 保存记忆。
        返回 (thought_text, importance)
        """
        emotion_ctx = self._get_emotion_context()

        memory_context = ""
        if keywords:
            try:
                from memory import get_db
                db = get_db()
                related = db.recall_related(keywords, limit=5)
                if related:
                    mem_lines = "【相关记忆】\n"
                    for m in related:
                        tier = m.get("tier", "短期")
                        mem_lines += f"- [{tier}] {m.get('thought', m.get('thought', ''))[:60]}...\n"
                    memory_context = mem_lines
                    logger.debug(f"think_about: retrieved {len(related)} related memories")
            except Exception as e:
                logger.warning(f"recall_related failed: {e}")

        prompt = _build_think_prompt(emotion_ctx, content, source, memory_context)
        resp = self._call_llm(prompt, system=None)
        thought = resp.content
        importance = _extract_importance(thought)

        try:
            from memory import get_db, Thought
            db = get_db()
            tags = _extract_tags(thought)
            tier = "长期" if importance >= 7 else ("中期" if importance >= 4 else "短期")
            thought_obj = Thought(
                timestamp=datetime.now().isoformat(),
                source=source,
                thought=thought,
                emotion=self._emotion_state,
                importance=importance,
                tier=tier,
                tags=tags,
            )
            db.add_thought(thought_obj)
        except Exception as e:
            logger.warning(f"save_thought failed: {e}")

        logger.info(f"think_about: source={source}, importance={importance}, len={len(thought)}")
        return thought, importance

    def analyze_feed(
        self,
        feed_content: str,
        keywords: Optional[list[str]] = None,
    ) -> tuple[str, int, str]:
        """
        投喂内容分析：提取标签 + 结合记忆 + 生成想法。
        返回 (thought_text, importance, tags)
        """
        emotion_ctx = self._get_emotion_context()

        memory_context = ""
        if keywords:
            try:
                from memory import get_db
                db = get_db()
                related = db.recall_related(keywords, limit=3)
                if related:
                    mem_lines = "【相关记忆】\n"
                    for m in related:
                        tier = m.get("tier", "短期")
                        mem_lines += f"- [{tier}] {m.get('thought', m.get('thought', ''))[:60]}...\n"
                    memory_context = mem_lines
            except Exception as e:
                logger.warning(f"recall_related in analyze_feed failed: {e}")

        tag_prompt = _build_tag_extract_prompt(feed_content)
        try:
            tag_resp = self._call_llm(tag_prompt, system=None, temperature=0.3)
            tags = tag_resp.content.strip().strip("[]").strip()
        except Exception as e:
            logger.warning(f"tag extract failed: {e}")
            tags = "生活"

        thought_prompt = _build_feed_think_prompt(emotion_ctx, feed_content, memory_context)
        resp = self._call_llm(thought_prompt, system=None)
        thought = resp.content
        importance = _extract_importance(thought)

        try:
            from memory import get_db, Thought, FeedRecord
            db = get_db()
            tier = "长期" if importance >= 7 else ("中期" if importance >= 4 else "短期")
            thought_obj = Thought(
                timestamp=datetime.now().isoformat(),
                source="投喂",
                thought=thought,
                emotion=self._emotion_state,
                importance=importance,
                tier=tier,
                tags=tags,
            )
            db.add_thought(thought_obj)
            feed_record = FeedRecord(
                timestamp=datetime.now().isoformat(),
                user_content=feed_content[:500],
                ai_thought=thought,
                tags=tags,
                emotion=self._emotion_state,
                importance=importance,
            )
            db.add_feed(feed_record)
        except Exception as e:
            logger.warning(f"save feed thought failed: {e}")

        logger.info(f"analyze_feed: importance={importance}, tags={tags}, len={len(thought)}")
        return thought, importance, tags

    def reflect_on_memories(self) -> str:
        """睡前回顾最高importance的记忆"""
        emotion_ctx = self._get_emotion_context()
        try:
            from memory import get_db
            db = get_db()
            top = db.get_top_memories(limit=3)
            if not top:
                return ""
            prompt = _build_reflect_prompt(emotion_ctx, top)
            resp = self._call_llm(prompt, system=None)
            return resp.content
        except Exception as e:
            logger.warning(f"reflect_on_memories failed: {e}")
            return ""

    def chat(
        self,
        user_input: str,
        history: Optional[list[dict[str, str]]] = None,
    ) -> str:
        """对话模式"""
        emotion_ctx = self._get_emotion_context()
        history_lines = ""
        for msg in (history or [])[-6:]:
            role = "小雪球" if msg["role"] == "assistant" else "你"
            history_lines += f"{role}：{msg['content']}\n"

        prompt = f"""你现在是「{PROFILE.name}」，{emotion_ctx}。

你们的对话历史：
{history_lines or "[无历史记录]"}

对方说：{user_input}

请用符合你性格的方式回复。要求：
1. 自然亲切，像朋友聊天
2. 结合你的兴趣爱好和个人经历
3. 长度适中（50-200字）
4. 可以适当提问延续话题
5. 不要输出任何额外解释"""

        try:
            resp = self._call_llm(prompt, system=SYSTEM_PROMPT)
            logger.info(f"chat: user_input={user_input[:50]!r}")
            return resp.content
        except Exception as e:
            logger.warning(f"chat failed: {e}")
            return "emmm...我现在有点迷糊，等我想想再说~"

    def _call_llm(
        self,
        prompt: str,
        system: Optional[str] = None,
        max_retries: int = 3,
        temperature: Optional[float] = None,
    ) -> LLMResponse:
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        last_err: Exception = Exception("initial")
        for attempt in range(max_retries):
            try:
                start = time.monotonic()
                kwargs: dict[str, Any] = {
                    "model": config.DEEPSEEK_MODEL,
                    "messages": messages,
                    "temperature": temperature if temperature is not None else config.LLM_TEMPERATURE,
                    "max_tokens": config.LLM_MAX_TOKENS,
                }
                completion = _get_client().chat.completions.create(**kwargs)
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
