"""
赛博人类 - 上网模块

负责从各个网站获取内容。
使用公开 API 获取热门内容和搜索结果。
"""

import requests
import json
import re

class Browser:
    """
    赛博人类的"眼睛"——用来在网上获取信息。
    """
    
    HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                      "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    def get_bilibili_hot(self, limit: int = 5) -> list:
        """获取B站热门视频"""
        try:
            resp = requests.get(
                "https://api.bilibili.com/x/web-interface/ranking/v2",
                headers=self.HEADERS, timeout=10
            )
            data = resp.json()
            if data.get("code") == 0:
                videos = data["data"]["list"][:limit]
                results = []
                for v in videos:
                    results.append({
                        "title": v.get("title", ""),
                        "summary": v.get("desc", "")[:200],
                        "url": f"https://www.bilibili.com/video/{v.get('bvid', '')}",
                        "stat": f"播放{v.get('stat',{}).get('view','?')} 点赞{v.get('stat',{}).get('like','?')}"
                    })
                return results
            return [{"title": f"B站API返回: {data.get('message', '?')}", "summary": "", "url": ""}]
        except Exception as e:
            return [{"title": "B站抓取失败", "summary": str(e), "url": ""}]
    
    def get_bilibili_search(self, keyword: str, limit: int = 3) -> list:
        """去B站搜索"""
        try:
            resp = requests.get(
                f"https://api.bilibili.com/x/web-interface/search/type?search_type=video&keyword={keyword}",
                headers=self.HEADERS, timeout=10
            )
            data = resp.json()
            if data.get("code") == 0:
                results = []
                for v in data.get("data", {}).get("result", [])[:limit]:
                    results.append({
                        "title": v.get("title", "").replace("<em>", "").replace("</em>", ""),
                        "summary": v.get("description", "")[:200],
                        "url": f"https://www.bilibili.com/video/{v.get('bvid', '')}"
                    })
                return results
            return [{"title": f"B站搜索: {keyword}", "summary": "", "url": ""}]
        except Exception as e:
            return [{"title": "B站搜索失败", "summary": str(e), "url": ""}]
    
    def get_baidu_hot(self, limit: int = 5) -> list:
        """获取百度热搜"""
        try:
            resp = requests.get(
                "https://top.baidu.com/board?tab=realtime",
                headers=self.HEADERS, timeout=10
            )
            resp.encoding = "utf-8"
            # 从页面提取热搜词
            titles = re.findall(r'"word":"(.*?)"', resp.text)
            results = []
            for t in titles[:limit]:
                results.append({
                    "title": t,
                    "summary": f"百度热搜: {t}",
                    "url": f"https://www.baidu.com/s?wd={t}"
                })
            return results if results else [{"title": "百度热搜暂无数据", "summary": "", "url": ""}]
        except Exception as e:
            return [{"title": "百度热搜抓取失败", "summary": str(e), "url": ""}]

    def get_zhihu_hot(self, limit: int = 5) -> list:
        """获取知乎热榜"""
        try:
            resp = requests.get(
                "https://www.zhihu.com/api/v3/feed/topstory/hot-lists/total?limit=10",
                headers={**self.HEADERS, "Accept": "application/json"},
                timeout=10
            )
            data = resp.json()
            results = []
            for item in data.get("data", [])[:limit]:
                target = item.get("target", {})
                title = target.get("title", "")
                if title:
                    results.append({
                        "title": title,
                        "summary": f"知乎热榜",
                        "url": target.get("url", "")
                    })
            return results if results else [{"title": "知乎热榜暂无", "summary": "", "url": ""}]
        except Exception as e:
            return [{"title": "知乎抓取失败", "summary": str(e), "url": ""}]

    def get_douyin_hot(self, limit: int = 5) -> list:
        """获取抖音热搜"""
        try:
            resp = requests.get(
                "https://www.douyin.com/aweme/v1/web/hot/search/list/",
                headers={
                    **self.HEADERS,
                    "Referer": "https://www.douyin.com/",
                },
                timeout=10
            )
            data = resp.json()
            items = data.get("data", {}).get("word_list", [])
            results = []
            for item in items[:limit]:
                word = item.get("word", "")
                hot_value = item.get("hot_value", 0)
                if word:
                    results.append({
                        "title": word,
                        "summary": f"抖音热搜 · 热度 {hot_value}",
                        "url": f"https://www.douyin.com/search/{word}",
                        "stat": f"热度:{hot_value}"
                    })
            return results if results else [{"title": "抖音热搜暂无", "summary": "", "url": ""}]
        except Exception as e:
            return [{"title": "抖音抓取失败", "summary": str(e), "url": ""}]

    def get_xiaohongshu_hot(self, limit: int = 3) -> list:
        """模拟小红书热门内容（简化版）"""
        # 小红书没有公开API，先放个占位
        return [{"title": "小红书热门内容（待接入）", "summary": "", "url": ""}]
