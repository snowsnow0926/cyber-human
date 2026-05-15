"""Test more URLs"""
import sys
sys.path.insert(0, '/home/ubuntu/cyber-human')
from browser_bot import BrowserBot

with BrowserBot(headless=True) as bot:
    test_urls = [
        ("豆瓣热映", "https://movie.douban.com/cinema/nowplaying/"),
        ("豆瓣排行榜", "https://movie.douban.com/chart"),
        ("小黑盒", "https://www.xiaoheihe.cn/"),
        ("小红书登录后", "https://www.xiaohongshu.com/explore"),
    ]
    
    for name, url in test_urls:
        print(f"\n=== {name} ===")
        try:
            ok = bot.goto(url)
            if ok:
                import time; time.sleep(3)
                # Scroll a bit to load content
                bot.scroll_down(times=2, wait=1)
                body = bot.get_text()
                lines = [l.strip() for l in body.split('\n') if l.strip() and len(l.strip()) > 10]
                print(f"  Loaded, {len(body)} chars, {len(lines)} useful lines")
                for line in lines[:5]:
                    print(f"  > {line[:60]}")
        except Exception as e:
            print(f"  Error: {str(e)[:80]}")
