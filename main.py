#!/usr/bin/env python3
"""
主程序入口
模拟小雪球的完整一天
"""

from __future__ import annotations

import argparse
import logging
import sys
import time
from datetime import datetime
from typing import Optional

import config
from logger import get_logger, main_logger
from memory import get_db
from memory_core import get_consolidation
from daily_life import DailyLifeEngine, get_engine
from emotion import get_emotion_system

logger = get_logger(__name__)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="赛博人类 - 小雪球的 AI 模拟")
    parser.add_argument(
        "--auto", action="store_true",
        help="自动模式：运行完整一天后自动退出（用于 cron 定时任务）",
    )
    parser.add_argument(
        "--chat", action="store_true",
        help="交互式对话模式",
    )
    parser.add_argument(
        "--slot", type=str, default="",
        help="只运行指定的时段（标签名）",
    )
    parser.add_argument(
        "--simulate-date", type=str, default="",
        help="模拟指定日期（YYYY-MM-DD）",
    )
    parser.add_argument(
        "--consolidate", action="store_true",
        help="只运行记忆巩固程序",
    )
    return parser.parse_args()


def run_full_day() -> None:
    logger.info("=" * 50)
    logger.info("赛博人类 · 小雪球 · 每日模拟开始")
    logger.info("=" * 50)

    engine = get_engine()

    try:
        results = engine.run_full_day()
        slot_count = len(results)
        thought_count = sum(
            len(r.get("thoughts", [])) for r in results
            if "error" not in r
        )
        logger.info(f"今日模拟完成：共 {slot_count} 个时段，{thought_count} 条想法")
    except Exception as e:
        logger.error(f"模拟过程中出错: {e}", exc_info=True)
        sys.exit(1)

    logger.info("=" * 50)
    logger.info("赛博人类 · 每日模拟结束")
    logger.info("=" * 50)


def run_single_slot(slot_label: str) -> None:
    engine = get_engine()
    from daily_life import TIME_BLOCKS
    target = next((s for s in TIME_BLOCKS if s["label"] == slot_label), None)
    if not target:
        logger.error(f"未找到时段: {slot_label}")
        available = ", ".join(s["label"] for s in TIME_BLOCKS)
        logger.error(f"可用时段: {available}")
        sys.exit(1)
    logger.info(f"运行单个时段: {target['label']}")
    try:
        result = engine._execute_block(target)
        logger.info(f"时段完成: {result}")
    except Exception as e:
        logger.error(f"时段运行出错: {e}", exc_info=True)
        sys.exit(1)


def run_chat_mode() -> None:
    from cyber_human import get_ai
    ai = get_ai()
    logger.info("进入交互式对话模式（输入 exit 或 quit 退出）")
    # 确保 logger 的 console handler 输出 INFO 级别（chat 模式需要）
    for h in logger.handlers:
        if isinstance(h, logging.StreamHandler) and h.stream == sys.stdout:
            h.setLevel(logging.INFO)
    print("\n=== 赛博人类 \xb7 小雪球 ===")
    print("你好呀！我是小雪球~有什么想聊的吗？\n")
    history: list[dict[str, str]] = []
    while True:
        try:
            user_input = input("你: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n再见啦~")
            break
        if not user_input:
            continue
        if user_input.lower() in ("exit", "quit", "退出", "q"):
            print("再见啦~下次再聊~")
            break
        try:
            reply = ai.chat(user_input, history)
            print(f"小雪球: {reply}\n")
            history.append({"role": "user", "content": user_input})
            history.append({"role": "assistant", "content": reply})
            if len(history) > 20:
                history = history[-20:]
        except Exception as e:
            print(f"小雪球：（emmm...好像出了点问题）{e}")
            logger.error(f"Chat error: {e}")


def run_consolidation() -> None:
    logger.info("运行记忆巩固程序...")
    mc = get_consolidation()
    result = mc.consolidate()
    logger.info(f"记忆巩固完成: {result}")


def main() -> None:
    args = parse_args()

    if args.consolidate:
        run_consolidation()
        return

    if args.slot:
        run_single_slot(args.slot)
        return

    if args.chat:
        run_chat_mode()
        return

    if args.auto:
        run_full_day()
        return

    run_full_day()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("用户中断，程序退出")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)
