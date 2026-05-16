#!/usr/bin/env python3
"""browser.py - 赛博人类浏览器模块 (HTTP API)"""

from __future__ import annotations

import random
import re
from dataclasses import dataclass
from typing import Any, Optional

import requests
from bs4 import BeautifulSoup

from logger import get_logger

logger = get_logger(__name__)

requests_session = requests.Session()
requests_session.headers.update({
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/html, application/xml",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
})


@dataclass
class BrowseResult:
    source: str
    title: str
    summary: str
    url: str
    category: str


class HTTPBrowser:
    """通过 HTTP API 抓取内容的浏览器"""

    SOURCE_CONFIGS = {
        "bilibili": {
            "url": "https://api.bilibili.com/x/web-interface/ranking/v2?rid=0&type=all",
            "method": "json",
            "parser": "_parse_bilibili",
        },
        "baidu": {
            "url": "https://top.baidu.com/board?tab=realtime",
            "method": "html",
            "parser": "_parse_baidu",
        },
        "zhihu": {
            "url": "https://www.zhihu.com/api/v4/columns/recommend/items?limit=10&offset=0",
            "method": "json",
            "parser": "_parse_zhihu",
        },
        "ithome": {
            "url": "https://www.ithome.com/rss/",
            "method": "rss",
            "parser": "_parse_rss",
        },
        "people": {
            "url": "http://www.people.com.cn/rss/opml.xml",
            "method": "rss",
            "parser": "_parse_rss",
        },
        "xiaohongshu": {
            "url": "https://www.xiaohongshu.com/explore",
            "method": "html",
            "parser": "_parse_xiaohongshu",
        },
    }

    def __init__(self) -> None:
        self.session = requests_session
        logger.info("HTTPBrowser initialized")

    def fetch(
        self, source: str, timeout: int = 10
    ) -> list[BrowseResult]:
        cfg = self.SOURCE_CONFIGS.get(source)
        if not cfg:
            logger.warning(f"Unknown source: {source}")
            return []

        try:
            logger.debug(f"Fetching {source}: {cfg['url']}")
            resp = self.session.get(cfg["url"], timeout=timeout)
            resp.raise_for_status()
            parser = getattr(self, cfg["parser"])
            results = parser(resp, source)
            logger.info(f"Fetched {len(results)} items from {source}")
            return results
        except requests.Timeout:
            logger.warning(f"Timeout fetching {source}")
        except requests.HTTPError as e:
            logger.warning(f"HTTP error fetching {source}: {e}")
        except Exception as e:
            logger.error(f"Unexpected error fetching {source}: {e}")
        return []

    def _parse_bilibili(self, resp, source):
        try:
            data = resp.json().get("data", {}).get("list", [])
            return [
                BrowseResult(
                    source="B站",
                    title=item.get("title", ""),
                    summary=item.get("desc", "")[:200],
                    url=f"https://www.bilibili.com/video/{item.get('bvid', '')}",
                    category="娱乐",
                )
                for item in data[:10]
                if item.get("title")
            ]
        except Exception as e:
            logger.warning(f"Failed to parse bilibili response: {e}")
            return []

    def _parse_baidu(self, resp, source):
        try:
            soup = BeautifulSoup(resp.text, "html.parser")
            items = soup.select(".c-single-text-ellipsis")[:10]
            return [
                BrowseResult(
                    source="百度热搜",
                    title=item.get_text(strip=True),
                    summary="",
                    url="https://top.baidu.com",
                    category="综合",
                )
                for item in items
            ]
        except Exception as e:
            logger.warning(f"Failed to parse baidu response: {e}")
            return []

    def _parse_zhihu(self, resp, source):
        try:
            data = resp.json().get("data", [])
            return [
                BrowseResult(
                    source="知乎",
                    title=item.get("title", ""),
                    summary=item.get("intro", "")[:200],
                    url=item.get("url", ""),
                    category="知识",
                )
                for item in data[:10]
                if item.get("title")
            ]
        except Exception as e:
            logger.warning(f"Failed to parse zhihu response: {e}")
            return []

    def _parse_rss(self, resp, source):
        try:
            soup = BeautifulSoup(resp.text, "xml")
            items = soup.find_all("item")[:10]
            source_name = "IT之家" if "ithome" in resp.url else "人民网"
            return [
                BrowseResult(
                    source=source_name,
                    title=item.title.get_text(strip=True) if item.title else "",
                    summary=item.description.get_text(strip=True)[:200]
                    if item.description else "",
                    url=item.link.get_text(strip=True) if item.link else "",
                    category="科技" if source_name == "IT之家" else "新闻",
                )
                for item in items
                if item.title
            ]
        except Exception as e:
            logger.warning(f"Failed to parse RSS response: {e}")
            return []

    def _parse_xiaohongshu(self, resp, source):
        """解析小红书探索页，提取标题文本"""
        try:
            titles = re.findall(
                r'<span[^>]*class="[^"]*title[^"]*"[^>]*>(.*?)</span>',
                resp.text
            )
            results = []
            for t in titles[:10]:
                clean_t = t.strip()[:80]
                if clean_t:
                    results.append(
                        BrowseResult(
                            source="小红书",
                            title=clean_t,
                            summary="",
                            url=f"https://www.xiaohongshu.com/search/result?keyword={clean_t}",
                            category="生活",
                        )
                    )
            if not results:
                soup = BeautifulSoup(resp.text, "html.parser")
                for sel in [".note-item .title", "[class*=title]"]:
                    elements = soup.select(sel)[:10]
                    if elements:
                        results = [
                            BrowseResult(
                                source="小红书",
                                title=e.get_text(strip=True)[:80],
                                summary="",
                                url="https://www.xiaohongshu.com/explore",
                                category="生活",
                            )
                            for e in elements if e.get_text(strip=True)
                        ]
                        break
            return results
        except Exception as e:
            logger.warning(f"Failed to parse xiaohongshu response: {e}")
            return []

    def browse_random(
        self,
        interests: Optional[list[str]] = None,
        max_results: int = 5,
    ) -> list[BrowseResult]:
        sources = list(self.SOURCE_CONFIGS.keys())
        random.shuffle(sources)
        results: list[BrowseResult] = []
        for src in sources:
            if len(results) >= max_results:
                break
            items = self.fetch(src)
            if interests:
                items = [
                    it for it in items
                    if any(kw in it.title for kw in interests)
                ]
            results.extend(items[:2])
        return results[:max_results]


def get_browser() -> HTTPBrowser:
    return HTTPBrowser()
