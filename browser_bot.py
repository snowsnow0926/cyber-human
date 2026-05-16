#!/usr/bin/env python3
"""
浏览器机器人模块 (Playwright)
通过真实浏览器抓取需要登录或 JS 渲染的页面
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Any, Optional

from logger import get_logger

logger = get_logger(__name__)


@dataclass
class BotBrowseResult:
    source: str
    title: str
    summary: str
    url: str
    category: str


class PlaywrightNotAvailable(Exception):
    pass


class BrowserBot:
    """
    使用 Playwright 进行浏览器自动化抓取。
    需要先运行: pip install playwright && playwright install chromium
    """

    SOURCE_CONFIGS: list[dict[str, Any]] = [
        {
            "name": "weibo",
            "url": "https://s.weibo.com/topic?q=%E7%83%AD%E7%82%B9",
            "selector": ".txt",
            "title_attr": "text",
        },
        {
            "name": "douban_movie",
            "url": "https://movie.douban.com/chart",
            "selector": "tr.item",
            "title_attr": "text",
        },
    ]

    _playwright_available: Optional[bool] = None

    def __init__(self) -> None:
        self._check_playwright()
        logger.info("BrowserBot initialized")

    def _check_playwright(self) -> None:
        if BrowserBot._playwright_available is None:
            try:
                import importlib.util
                spec = importlib.util.find_spec("playwright")
                BrowserBot._playwright_available = spec is not None
                if BrowserBot._playwright_available:
                    logger.info("Playwright is available")
                else:
                    logger.warning("Playwright not installed, BrowserBot will use fallback")
            except Exception:
                BrowserBot._playwright_available = False

    def fetch(self, source_name: str = "weibo") -> list[BotBrowseResult]:
        if not BrowserBot._playwright_available:
            logger.info(f"Playwright not available, returning fallback for {source_name}")
            return self._fallback_browse(source_name)

        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            return self._fallback_browse(source_name)

        cfg = next((c for c in self.SOURCE_CONFIGS if c["name"] == source_name), None)
        if not cfg:
            return []

        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                context = browser.new_context(
                    user_agent=(
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/120.0.0.0 Safari/537.36"
                    )
                )
                page = context.new_page()
                page.goto(cfg["url"], wait_until="networkidle", timeout=15000)
                elements = page.query_selector_all(cfg["selector"])
                results: list[BotBrowseResult] = []
                for el in elements[:10]:
                    text = el.text_content() or ""
                    if len(text.strip()) > 5:
                        results.append(BotBrowseResult(
                            source=source_name,
                            title=text.strip()[:100],
                            summary=text.strip()[:200],
                            url=cfg["url"],
                            category="社交",
                        ))
                browser.close()
                logger.info(f"BrowserBot fetched {len(results)} items from {source_name}")
                return results
        except Exception as e:
            logger.warning(f"BrowserBot failed for {source_name}: {e}")
            return self._fallback_browse(source_name)

    def _fallback_browse(self, source_name: str) -> list[BotBrowseResult]:
        fallbacks: dict[str, list[BotBrowseResult]] = {
            "weibo": [
                BotBrowseResult("微博热搜", "微博热搜占位内容1", "微博热搜占位摘要1", "https://weibo.com", "社交"),
                BotBrowseResult("微博热搜", "微博热搜占位内容2", "微博热搜占位摘要2", "https://weibo.com", "社交"),
            ],
            "douban_movie": [
                BotBrowseResult("豆瓣电影", "豆瓣电影占位内容", "豆瓣电影占位摘要", "https://douban.com", "娱乐"),
            ],
        }
        items = fallbacks.get(source_name, [])
        logger.info(f"BrowserBot fallback: {len(items)} items for {source_name}")
        return items


def get_browser_bot() -> BrowserBot:
    return BrowserBot()
