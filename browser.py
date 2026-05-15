"""
赛博人类 - 上网模块

负责从各个网站获取内容。
使用公开 API 获取热门内容和搜索结果。
"""

import requests
import feedparser
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
        """获取知乎热榜（explore API）"""
        try:
            session = requests.Session()
            session.headers.update(self.HEADERS)
            resp = session.get(
                "https://www.zhihu.com/api/v3/explore/guest/feeds?limit=" + str(limit + 3),
                headers={"Accept": "application/json"},
                timeout=10
            )
            data = resp.json()
            results = []
            for item in data.get("data", [])[:limit]:
                target = item.get("target", {})
                question = target.get("question", {})
                title = question.get("title", "") or target.get("excerpt", "")[:80]
                if title:
                    api_url = target.get("url", "")
                    answer_id = api_url.split("/")[-1] if "/" in api_url else ""
                    qid = question.get("id", "") or target.get("id", "")
                    if qid and answer_id:
                        web_url = "https://www.zhihu.com/question/" + str(qid) + "/answer/" + str(answer_id)
                    else:
                        web_url = api_url
                    results.append({
                        "title": title[:80],
                        "summary": target.get("excerpt", "")[:200],
                        "url": web_url,
                        "stat": "赞同 " + str(target.get("voteup_count", 0))
                    })
            return results if results else [{"title": "知乎热榜暂无", "summary": "", "url": ""}]
        except Exception as e:
            return [{"title": "知乎抓取失败", "summary": str(e), "url": ""}]
    
    def get_ithome_hot(self, limit: int = 5) -> list:
        """获取IT之家热文（RSS）"""
        try:
            feed = feedparser.parse("https://www.ithome.com/rss/")
            results = []
            for entry in feed.entries[:limit]:
                title = entry.get("title", "")
                summary = entry.get("summary", "")[:200] if entry.get("summary") else ""
                url = entry.get("link", "")
                results.append({"title": title[:80], "summary": summary, "url": url, "stat": ""})
            return results if results else [{"title": "IT之家暂无", "summary": "", "url": ""}]
        except Exception as e:
            return [{"title": "IT之家失败", "summary": str(e), "url": ""}]
    
    def get_people_hot(self, limit: int = 5) -> list:
        """获取人民网要闻（RSS）"""
        try:
            feed = feedparser.parse("http://www.people.com.cn/rss/politics.xml")
            results = []
            for entry in feed.entries[:limit]:
                title = entry.get("title", "")
                summary = entry.get("summary", "")[:200] if entry.get("summary") else ""
                url = entry.get("link", "")
                results.append({"title": title[:80], "summary": summary, "url": url, "stat": ""})
            return results if results else [{"title": "人民网暂无", "summary": "", "url": ""}]
        except Exception as e:
            return [{"title": "人民网失败", "summary": str(e), "url": ""}]

