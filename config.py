#!/usr/bin/env python3
"""
配置管理模块
所有配置统一从此模块读取，禁止硬编码。
API Key 检查延迟到首次实际使用时，避免级联导入失败。
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


# ── 路径配置 ──────────────────────────────────────────────────────────
BASE_DIR: Path = Path(__file__).parent.resolve()
DB_PATH: Path = Path(os.getenv("DB_PATH", str(BASE_DIR / "cyber_memory.db"))).resolve()
LOG_DIR: Path = Path(os.getenv("LOG_DIR", str(BASE_DIR / "logs"))).resolve()

# ── API 配置（延迟验证，使用前通过 require_api_key() 检查）──────────────
DEEPSEEK_API_KEY: str = os.getenv("DEEPSEEK_API_KEY", "")
DEEPSEEK_BASE_URL: str = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
DEEPSEEK_MODEL: str = os.getenv("DEEPSEEK_MODEL", "deepseek-v4-flash")


def require_api_key() -> str:
    """Ensure API key is set before use. Raises if missing."""
    if not DEEPSEEK_API_KEY:
        raise RuntimeError(
            "[FATAL] DEEPSEEK_API_KEY environment variable is not set. "
            "Copy .env.example to .env and fill in your API key."
        )
    return DEEPSEEK_API_KEY


# ── Flask / Web 配置 ───────────────────────────────────────────────────
FLASK_HOST: str = os.getenv("FLASK_HOST", "0.0.0.0")
FLASK_PORT: int = int(os.getenv("FLASK_PORT", "5010"))
FLASK_DEBUG: bool = os.getenv("FLASK_DEBUG", "False").lower() in ("true", "1", "yes")

# ── LLM 参数 ───────────────────────────────────────────────────────────
LLM_TEMPERATURE: float = float(os.getenv("LLM_TEMPERATURE", "0.8"))
LLM_MAX_TOKENS: int = int(os.getenv("LLM_MAX_TOKENS", "1024"))
LLM_TIMEOUT: int = int(os.getenv("LLM_TIMEOUT", "60"))

# ── 浏览器 / 抓取配置 ────────────────────────────────────────────────
BROWSER_HEADLESS: bool = os.getenv("BROWSER_HEADLESS", "True").lower() in ("true", "1", "yes")
PLAYWRIGHT_INSTALLED: bool = os.getenv("PLAYWRIGHT_INSTALLED", "False").lower() in ("true", "1", "yes")

# ── 日志配置 ─────────────────────────────────────────────────────────
LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO").upper()
LOG_FORMAT: str = os.getenv(
    "LOG_FORMAT",
    "%(asctime)s | %(levelname)-8s | %(name)s:%(lineno)d | %(message)s"
)
LOG_FILE: Path = LOG_DIR / os.getenv("LOG_FILENAME", "cyber_human.log")
LOG_MAX_BYTES: int = int(os.getenv("LOG_MAX_BYTES", str(10 * 1024 * 1024)))  # 10 MB
LOG_BACKUP_COUNT: int = int(os.getenv("LOG_BACKUP_COUNT", "5"))

# ── 应用开关 ─────────────────────────────────────────────────────────
ENABLE_CHAT_CACHE: bool = os.getenv("ENABLE_CHAT_CACHE", "True").lower() in ("true", "1", "yes")
