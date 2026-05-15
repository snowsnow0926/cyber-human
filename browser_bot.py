"""
赛博人类 v0.5 - Playwright 浏览器模块

用真正的浏览器上网，解锁所有平台（微博/小红书/知乎正文/...）
"""

import os
import sys
import re
import json
import time
from datetime import datetime


class BrowserBot:
    """
    赛博人类的"眼睛和手"——真正的浏览器。
    
    用 Playwright 操控 Chromium，可以：
    - 打开任意网页
    - 阅读完整内容（不仅仅是API给的标题）
    - 滚动翻页
    - 填写表单、点击按钮
    - 截图（以后用）
    
    注意：Playwright 是一个 Python 库，不是视觉浏览器。
    它打开一个"无头"（看不见的）Chromium 浏览器来干活。
    """
    
    # 假装成正常的浏览器，不让网站发现是机器人
    USER_AGENT = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/125.0.0.0 Safari/537.36"
    )
    
    def __init__(self, headless=True, timeout=30000):
        """
        初始化浏览器。
        
        headless: True=无头模式（看不见窗口，省资源）
                  False=有头模式（能看见浏览器窗口，调试用）
        timeout:  页面的最长等待时间（毫秒）
        """
        self.headless = headless
        self.timeout = timeout
        self.browser = None
        self.context = None
        self.page = None
        self._log("Playwright 浏览器模块已初始化")
    
    def _log(self, msg):
        print("  [BrowserBot] " + msg)
    
    def start(self):
        """启动浏览器（打开Chromium）"""
        try:
            from playwright.sync_api import sync_playwright
            
            self._playwright = sync_playwright().start()
            self.browser = self._playwright.chromium.launch(
                headless=self.headless,
                args=[
                    "--no-sandbox",
                    "--disable-setuid-sandbox",
                    "--disable-dev-shm-usage",
                ]
            )
            self.context = self.browser.new_context(
                user_agent=self.USER_AGENT,
                viewport={"width": 1920, "height": 1080},
                locale="zh-CN",
                timezone_id="Asia/Shanghai"
            )
            self.page = self.context.new_page()
            self.page.set_default_timeout(self.timeout)
            self._log("Chromium 浏览器已启动")
            return True
        except Exception as e:
            self._log("启动失败: " + str(e))
            return False
    
    def close(self):
        """关闭浏览器"""
        try:
            if self.page:
                self.page.close()
            if self.context:
                self.context.close()
            if self.browser:
                self.browser.close()
            if hasattr(self, '_playwright'):
                self._playwright.stop()
            self._log("浏览器已关闭")
        except Exception as e:
            self._log("关闭出错: " + str(e))
    
    def __enter__(self):
        self.start()
        return self
    
    def __exit__(self, *args):
        self.close()
    
    # -------- 打开网页 --------
    
    def goto(self, url):
        """打开一个网页"""
        try:
            self._log("打开: " + url)
            self.page.goto(url, wait_until="networkidle")
            time.sleep(1)
            return True
        except Exception as e:
            self._log("打开失败: " + str(e))
            return False
    
    def get_text(self, selector=None):
        """
        获取页面文字。
        如果有 selector: 只返回匹配的元素文字
        如果没有: 返回整页文字
        """
        try:
            if selector:
                elements = self.page.query_selector_all(selector)
                texts = [el.text_content().strip() for el in elements if el.text_content()]
                return "\n".join(texts)
            else:
                return self.page.inner_text("body")
        except Exception as e:
            self._log("获取文字失败: " + str(e))
            return ""
    
    def scroll_down(self, times=1, wait=1):
        """向下滚动页面"""
        try:
            for i in range(times):
                self.page.evaluate("window.scrollBy(0, window.innerHeight)")
                time.sleep(wait)
            self._log("向下滚动了 " + str(times) + " 屏")
            return True
        except Exception as e:
            return False
    
    # -------- 知乎 --------
    
    def get_zhihu_hot_page(self, limit=5):
        """
        从知乎热榜HTML页面获取内容。
        
        因为知乎的API不给标题，但网页版是完整的。
        这个方法直接打开热榜页，提取问题列表。
        """
        self._log("正在抓取知乎热榜页面...")
        
        ok = self.goto("https://www.zhihu.com/hot")
        if not ok:
            return []
        
        time.sleep(2)
        
        results = []
        try:
            # 知乎热榜的问题列表
            items = self.page.query_selector_all(".HotList-item,.hot-list-item,[class*=HotItem]")
            
            if not items or len(items) == 0:
                # 备用方案：摘取所有大标题
                self._log("未找到标准热榜元素，尝试备用方案")
                titles = self.page.query_selector_all("h2,h3,h4")
                for t in titles[:limit+5]:
                    text = t.text_content().strip()
                    if len(text) > 5 and len(text) < 100:
                        results.append({
                            "title": text,
                            "summary": "",
                            "url": "",
                            "stat": ""
                        })
                        if len(results) >= limit:
                            break
            else:
                for item in items[:limit]:
                    title_el = item.query_selector("h2,a[href*=question]")
                    title = title_el.text_content().strip() if title_el else ""
                    
                    # 提取回答数/热度
                    stat_el = item.query_selector(".HotList-itemMetrics,.HotItem-metrics")
                    stat = stat_el.text_content().strip() if stat_el else ""
                    
                    # 提取链接
                    link_el = item.query_selector("a[href*=question]")
                    href = ""
                    if link_el:
                        href = link_el.get_attribute("href") or ""
                        if href.startswith("/"):
                            href = "https://www.zhihu.com" + href
                    
                    if title:
                        results.append({
                            "title": title[:80],
                            "summary": "",
                            "url": href,
                            "stat": stat
                        })
                
        except Exception as e:
            self._log("提取失败: " + str(e))
        
        return results
    
    # -------- B站热门（增强版） --------
    
    def get_bilibili_hot_data(self, limit=5):
        """
        用浏览器打开B站热门页，提取视频标题+播放量+描述。
        
        相比API版，浏览器能读到更多信息（播放量、时长等）。
        """
        self._log("正在抓取B站热门页...")
        
        ok = self.goto("https://www.bilibili.com/v/popular/hot")
        if not ok:
            return []
        
        time.sleep(3)
        
        results = []
        try:
            cards = self.page.query_selector_all(".video-card")
            
            if cards and len(cards) > 0:
                for card in cards[:limit]:
                    # 获取卡片所有文字
                    full_text = card.text_content().strip()
                    lines = [l.strip() for l in full_text.split("\n") if l.strip()]
                    
                    if not lines:
                        continue
                    
                    # 第一行是标题
                    title = lines[0]
                    
                    # 获取链接
                    link_el = card.query_selector("a")
                    href = link_el.get_attribute("href") or "" if link_el else ""
                    if href.startswith("//"):
                        href = "https:" + href
                    
                    # 查找播放量和点赞
                    stat = ""
                    for line in lines:
                        if "万" in line or "播放" in line or "点赞" in line:
                            stat = line
                            break
                    
                    results.append({
                        "title": title[:80],
                        "summary": "",
                        "url": href,
                        "stat": stat
                    })
            else:
                # 备用方案
                links = self.page.query_selector_all("a")
                for link in links[:limit*5]:
                    href = link.get_attribute("href") or ""
                    if "video/BV" not in href:
                        continue
                    title = link.text_content().strip()
                    if len(title) < 4:
                        continue
                    if href.startswith("//"):
                        href = "https:" + href
                    results.append({
                        "title": title[:80],
                        "summary": "",
                        "url": href,
                        "stat": ""
                    })
                    if len(results) >= limit:
                        break
            
            self._log("获取到 %d 个B站视频" % len(results))
        except Exception as e:
            self._log("B站抓取失败: " + str(e))
        
        return results
    
    # -------- 通用：从任意页面提取正文 --------
    
    def get_page_content(self, url, limit_chars=3000):
        """
        打开任意网页，提取正文内容。
        
        这个方法是通用的——不限定知乎。
        打开任何网页都能读。
        """
        ok = self.goto(url)
        if not ok:
            return {"title": "打开失败", "text": "", "url": url}
        
        time.sleep(1)
        
        title = self.page.title()
        text = self.get_text()[:limit_chars]
        
        return {"title": title, "text": text, "url": url}
    
    # -------- 微博热搜 --------
    
    def get_weibo_hot(self, limit=5, cookie_file=None):
        """
        获取微博热搜（用 requests 直接调 JSON API）。
        
        注意：这个 API 有时会被拦截。
        备选方案：用 requests 直接调 weibo.com 热搜页。
        """
        self._log("正在抓取微博热搜...")
        
        results = []
        try:
            import requests as req
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Referer": "https://weibo.com/",
                "Accept": "application/json, text/plain, */*"
            }
            resp = req.get(
                "https://weibo.com/ajax/side/hotSearch",
                headers=headers,
                timeout=10
            )
            data = resp.json()
            realtime = data.get("data", {}).get("realtime", [])
            
            for item in realtime[:limit]:
                word = item.get("word", "") or item.get("title", "")
                num = item.get("raw_hot", "") or item.get("num", "")
                label = item.get("label_name", "")
                icon = ""
                if label == "热":
                    icon = "🔥"
                elif label == "沸":
                    icon = "💥"
                elif label == "爆":
                    icon = "💣"
                
                results.append({
                    "title": word[:80],
                    "summary": icon + " " + str(num) if num else "",
                    "url": "https://s.weibo.com/weibo?q=" + word,
                    "stat": icon + label
                })
        except Exception as e:
            self._log("微博抓取失败: " + str(e))
        
        return results
    
    # -------- 混合模式 --------
        """
        混合模式获取知乎：先用API（我们的修复版），
        如果API结果不够好，用浏览器补。
        """
        # 先用API
        from browser import Browser
        b = Browser()
        api_results = b.get_zhihu_hot(limit)
        
        # 检查API结果的质量
        if len(api_results) >= limit and api_results[0].get("title", "") != "知乎热榜暂无":
            self._log("API结果够用，跳过浏览器")
            return api_results
        
        # API不够好，用浏览器
        self._log("API不够用，启动浏览器补采")
        return self.get_zhihu_hot_page(limit)
