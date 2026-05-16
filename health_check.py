#!/usr/bin/env python3
"""赛博人类健康检查 - 每5分钟检查web是否在线"""
from __future__ import annotations

import subprocess
from datetime import datetime
from pathlib import Path

import requests

LOG: Path = Path("/home/ubuntu/cyber-human/health.log")
URL: str = "http://localhost:5010/?tab=stats"

try:
    from logger import get_logger
    _logger = get_logger(__name__)
except ImportError:
    _logger = None


def _log(level: str, msg: str) -> None:
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    if _logger:
        getattr(_logger, level.lower())(msg)
    else:
        try:
            LOG.parent.mkdir(parents=True, exist_ok=True)
            with open(LOG, "a", encoding="utf-8") as f:
                print(f"[{ts}] {level} {msg}", file=f)
        except OSError:
            pass


try:
    r = requests.get(URL, timeout=10)
    if r.status_code != 200:
        _log("error", f"Web挂了: {r.status_code}")
        subprocess.run(
            ["/home/ubuntu/cyber-human/venv/bin/python3", "/home/ubuntu/cyber-human/web.py"],
            cwd="/home/ubuntu/cyber-human",
        )
except Exception as e:
    _log("error", f"健康检查失败: {e}")
