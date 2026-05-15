"""Test if Playwright + Chromium works"""
from playwright.sync_api import sync_playwright
p = sync_playwright().start()
b = p.chromium.launch(headless=True)
print("PLAYWRIGHT OK!")
page = b.new_page()
page.goto("https://www.baidu.com")
title = page.title()
print("Baidu title:", title)
page.close()
b.close()
p.stop()
print("ALL OK!")
