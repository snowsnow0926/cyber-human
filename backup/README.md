# 赛博人类 🤖

一个能自己上网冲浪、思考、写日记的 AI Agent。

## 它能做什么？

- 🌐 自动逛贴吧、B站、看新闻
- 💭 对看到的内容产生自己的想法
- 🧠 记住看过的东西和想过的念头
- 📝 每天写日记总结
- 💬 你可以直接跟它聊天

## 快速开始

```bash
# 装依赖
pip install -r requirements.txt

# 跑一轮冲浪
python3 main.py

# 跟它聊天
python3 main.py --chat

# 设置定时任务（每天自动跑）
python3 main.py --auto
```

## 定时任务（让赛博人类每天自动冲浪）

```bash
crontab -e
# 添加下面这行，每天早8点和晚8点各跑一次
0 8,20 * * * cd /home/ubuntu/cyber-human && /home/ubuntu/cyber-human/venv/bin/python3 main.py --auto >> daily.log 2>&1
```

## 项目结构

```
cyber-human/
├── main.py           # 主入口
├── cyber_human.py    # 大脑（性格 + AI API）
├── memory.py         # 记忆（SQLite 数据库）
├── browser.py        # 上网（抓取网页内容）
├── requirements.txt  # Python 依赖
└── cyber_memory.db   # 记忆数据库（自动生成）
```

## v0.1 功能

- ✅ 逛贴吧（指定吧的最新帖子）
- ✅ 用 AI 对内容产生想法
- ✅ 记忆存储（SQLite）
- ✅ 每日日记
- ✅ 直接聊天
- ✅ 定时自动运行

## 计划中

- [ ] B站视频内容抓取
- [ ] 小黑盒游戏资讯
- [ ] 性格系统完善
- [ ] 情绪系统
- [ ] Web 管理界面
- [ ] 多个赛博人类同时管理

## License

MIT License - 完全开源，自由使用、修改、分发。
