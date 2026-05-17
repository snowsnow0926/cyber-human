#!/usr/bin/env python3
"""赛博人类健康检查 - 每5分钟检查web是否在线"""
from __future__ import annotations

import subprocess
import sys
from datetime import datetime
from pathlib import Path

import requests

try:
    import config
    _URL: str = f"http://localhost:{config.FLASK_PORT}/"
    _LOG: Path = config.LOG_DIR / "health.log"
except Exception:
    _URL = "http://localhost:5010/"
    _LOG = Path(__file__).parent.resolve() / "logs" / "health.log"

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
            _LOG.parent.mkdir(parents=True, exist_ok=True)
            with open(_LOG, "a", encoding="utf-8") as f:
                print(f"[{ts}] {level} {msg}", file=f)
        except OSError:
            pass


def get_health_status() -> dict:
    """返回健康检查状态（供 web.py /api/status 调用）"""
    try:
        r = requests.get(_URL, timeout=10)
        healthy = r.status_code == 200
        return {
            "healthy": healthy,
            "status_code": r.status_code,
            "checked_at": datetime.now().isoformat(),
        }
    except requests.RequestException as e:
        return {
            "healthy": False,
            "error": str(e),
            "checked_at": datetime.now().isoformat(),
        }


def _restart_if_needed() -> None:
    """检查服务状态，必要时重启"""
    status = get_health_status()
    if not status.get("healthy"):
        _log("error", f"Web挂了: {status.get('status_code', 'unknown')}")
        python_exe = sys.executable
        script_path = Path(__file__).parent.resolve() / "web.py"
        try:
            subprocess.Popen(
                [python_exe, str(script_path)],
                cwd=script_path.parent,
                creationflags=subprocess.DETACHED_PROCESS if sys.platform == "win32" else 0,
            )
            _log("info", "Web服务已重启")
        except Exception as e:
            _log("error", f"重启失败: {e}")


if __name__ == "__main__":
    _restart_if_needed()
