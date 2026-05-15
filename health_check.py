#!/usr/bin/env python3
"""赛博人类健康检查 - 每5分钟检查web是否在线"""
import requests, sys, subprocess

URL = "http://localhost:5010/?tab=stats"
LOG = "/home/ubuntu/cyber-human/health.log"

try:
    r = requests.get(URL, timeout=10)
    if r.status_code != 200:
        print("Web挂了: " + str(r.status_code), file=open(LOG, "a"))
        subprocess.run(["/home/ubuntu/cyber-human/venv/bin/python3", "/home/ubuntu/cyber-human/web.py"], 
                      cwd="/home/ubuntu/cyber-human")
except Exception as e:
    print("健康检查失败: " + str(e), file=open(LOG, "a"))
