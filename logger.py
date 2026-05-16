#!/usr/bin/env python3
"""
日志模块
统一日志配置，替换所有 print() 调用
"""

import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Optional

import config


def get_logger(name: str) -> logging.Logger:
    """
    获取指定名称的 logger。
    使用示例:
        logger = get_logger(__name__)
        logger.info("Hello world")
    """
    logger = logging.getLogger(name)

    if logger.handlers:
        return logger

    logger.setLevel(getattr(logging, config.LOG_LEVEL, logging.INFO))

    formatter = logging.Formatter(config.LOG_FORMAT)

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.WARNING)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    try:
        file_handler = RotatingFileHandler(
            filename=config.LOG_FILE,
            maxBytes=config.LOG_MAX_BYTES,
            backupCount=config.LOG_BACKUP_COUNT,
            encoding="utf-8",
        )
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    except OSError as e:
        fallback = config.LOG_DIR / "cyber_human.log"
        try:
            fallback.parent.mkdir(parents=True, exist_ok=True)
            file_handler = RotatingFileHandler(
                filename=fallback,
                maxBytes=config.LOG_MAX_BYTES,
                backupCount=config.LOG_BACKUP_COUNT,
                encoding="utf-8",
            )
            file_handler.setLevel(logging.DEBUG)
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)
        except OSError:
            pass

    logger.propagate = False
    return logger


# 预创建的全局 logger
main_logger = get_logger("cyber_human")
