#!/usr/bin/env python3
"""
单次对话工具
快速与 AI 对话，无需启动完整服务
"""

from __future__ import annotations

import sys
from logger import get_logger
from cyber_human import get_ai

logger = get_logger(__name__)


def chat_once(message: str) -> str:
    """
    单次对话
    Args:
        message: 用户输入
    Returns:
        AI 回复内容
    """
    try:
        ai = get_ai()
        reply = ai.chat(message)
        logger.info(f"chat_once: {message[:30]!r} -> {reply[:50]!r}")
        return reply
    except Exception as e:
        logger.error(f"chat_once failed: {e}")
        return f"抱歉，出了点问题：{e}"


def main() -> None:
    if len(sys.argv) < 2:
        print("用法: python chat_once.py <消息>")
        print("示例: python chat_once.py 你好呀！")
        sys.exit(1)

    message = " ".join(sys.argv[1:])
    print(f"\n你: {message}")
    print("小雪球: ", end="", flush=True)
    reply = chat_once(message)
    print(reply)


if __name__ == "__main__":
    main()
