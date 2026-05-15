"""Test Playwright sources: 小红书, 小黑盒, 豆瓣"""
import sys
sys.path.insert(0, '/home/ubuntu/cyber-human')
from browser_bot import BrowserBot

with BrowserBot(headless=True) as bot:
    test_urls = [
        ("小红书", "https://www.xiaohongshu.com/explore"),
        ("小黑盒", "https://api.xiaoheihe.cn/bbs/web/api/feed/hot"),
        ("豆瓣电影", "https://movie.douban.com/"),
        ("网易新闻", "https://news.163.com/"),
    ]
    
    for name, url in test_urls:
        print(f"\n=== {name} ===")
        try:
            ok = bot.goto(url)
            if ok:
                import time; time.sleep(3)
                body = bot.get_text()[:500]
                print(f"  Page loaded, {len(body)} chars")
                print(f"  First 200: {body[:200].replace(chr(10), ' ')}")
            else:
                print("  Failed to load")
        except Exception as e:
            print(f"  Error: {str(e)[:80]}")
