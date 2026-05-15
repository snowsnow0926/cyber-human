# Cyber Human (赛博人类) 🐩

> An AI agent that lives on the internet like a real person — with memory, personality, daily routine, and real-time synchronized timeline.

> 一个像真人一样生活在互联网上的 AI 智能体 —— 有记忆、性格、日常生活和实时同步的时间线。

---

## 🌟 Overview / 概述

**Cyber Human (赛博人类)** is an experimental AI agent project. "小雪球" is a 19-year-old freshman at Jiangnan University (Wuxi, China), majoring in Food Science and Engineering. She browses the web, forms thoughts, learns knowledge, writes diaries, and develops memories — just like a real person.

**赛博人类** 是一个实验性 AI 智能体项目。"小雪球"是一名 19 岁的大一新生，就读于江南大学（无锡），食品科学与工程专业。她浏览网页、产生想法、学习知识、写日记、形成记忆——就像一个真实的人。

### Core Features / 核心功能

| Feature | Description |
|---------|-------------|
| 🧠 **Three-layer Memory** | Short-term → Mid-term → Long-term with forgetting mechanism |
| 📅 **Daily Life Engine** | 12 time blocks, weighted random browsing, AI-generated events |
| 🌐 **9+ Data Sources** | Bilibili, Baidu, Douyin, Zhihu, Weibo, Douban, Netease, IThome, People's Daily |
| 🎭 **Character Profile** | Interest-based content filtering, personality-driven responses |
| 📚 **Knowledge System** | Learn from browsing, review periodically, forget over time |
| 🎯 **Emotion System** | Dynamic mood tracking, weather-aware emotional modifiers |
| 💬 **Dialogue Memory** | Remembers past conversations with users |
| 🖥️ **Web Dashboard** | Timeline, thoughts, diary, phone mockup, statistics, knowledge base, chat |

---

## 🚀 Quick Start / 快速开始

### Requirements / 依赖

- Python 3.10+
- pip / venv
- Playwright (for browser automation)
- DeepSeek API key (or compatible API)

### Setup / 安装

```bash
# 1. 克隆项目
git clone https://github.com/snowsnow0926/cyber-human.git
cd cyber-human

# 2. 安装依赖
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 3. 安装 Playwright 浏览器
playwright install chromium

# 4. 配置 API
# 编辑 main.py，修改 API_KEY 和 API_URL

# 5. 运行 Web 界面
python3 web.py

# 6. 运行每日模拟
python3 main.py --auto

# 7. 访问界面
# http://localhost:5010
```

### Deployment / 部署

See [nginx.conf](nginx.conf) for reverse proxy configuration.

```nginx
location /cyber-human/ {
    proxy_pass http://127.0.0.1:5010/;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
}
```

PM2 process management:
```bash
pm2 start web.py --interpreter python3 --name cyber-human
```

---

## 🧠 Architecture / 架构

```
cyber-human/
├── main.py              # Entry point / CLI
├── web.py               # Web dashboard (Flask)
├── daily_life.py        # Daily life engine
├── cyber_human.py       # AI personality core
├── memory.py            # Database / memory storage
├── memory_core.py       # Three-layer memory system
├── knowledge.py         # Knowledge learning system
├── character.py         # Character profile & filtering
├── browser.py           # Data source fetchers
├── browser_bot.py       # Playwright browser automation
├── weather.py           # Weather awareness
├── holiday.py           # Holiday/event recognition
├── chat_once.py         # Single-chat relay
├── health_check.py      # Auto-restart monitor
├── requirements.txt     # Dependencies
└── nginx.conf           # Nginx config template
```

### Data Flow / 数据流

```
🌐 Data Sources → 🧠 Browser → 💭 AI Thoughts → 📚 Knowledge System
                                                      ↓
                    🗄️ Short-term Memory → Mid-term → Long-term
                                                      ↓
                    📝 Diary Entry → 💾 Daily Schedule → 📊 Dashboard
```

### Cron Schedule / 定时任务

| Time | Action |
|------|--------|
| 06:00 | Morning simulation |
| 08:00 | Morning browse + study |
| 12:00 | Midday check |
| 18:00 | Evening browse |
| 20:00 | Nightly reflection + diary |
| */5 | Health check |

---

## 📊 Memory System / 记忆系统

| Layer | Capacity | Decay | Description |
|-------|----------|-------|-------------|
| 🟢 Short-term | 50 items | 24h | Recent thoughts & events |
| 🟡 Mid-term | 100 items | 7 days | Important memories |
| 🔴 Long-term | Unlimited | Never | Core experiences & knowledge |

### Emotion System / 情绪系统

- 8 base moods: happy, sad, excited, calm, anxious, tired, curious, neutral
- Weather affects mood (+30% on sunny days)
- Events trigger mood changes
- Mood influences browsing preferences

---

## 🌐 Data Sources / 数据源

| Source | Type | Method | Status |
|--------|------|--------|--------|
| Bilibili | Video hotlist | API + Playwright | ✅ |
| Baidu | Hot search | API | ✅ |
| Douyin | Hot search | API | ✅ |
| Zhihu | Explore page | Playwright | ✅ |
| Weibo | Hot search | API + Playwright | ✅ |
| Douban | Movie ranking | API + Playwright | ✅ |
| Netease | News | API + Playwright | ✅ |
| IThome | Tech news | RSS | ✅ |
| People's Daily | News | RSS | ✅ |

---

## 💬 API / 接口

### Chat
```
POST /chat_api
{"message": "你好小雪球"}
→ {"reply": "你好呀！今天天气真好～"}
```

### Control Panel
```
POST /api/clear_data    → Clear all data
POST /api/simulate_day  → Run full day simulation
```

---

## 🧪 Test Checklist / 测试清单

- [ ] Web UI all tabs load (200 OK)
  - [ ] Browse / 浏览
  - [ ] Timeline / 时间线 (with date navigation)
  - [ ] Thoughts / 想法
  - [ ] Diary / 日记
  - [ ] Phone / 手机
  - [ ] Stats / 统计
  - [ ] Knowledge / 知识
  - [ ] Chat / 聊天
  - [ ] Control / 控制
  - [ ] Profile / 个人主页
- [ ] Python syntax: all .py files compile
- [ ] main.py --auto runs without errors
- [ ] Database can be cleared and re-created
- [ ] Data sources return valid content
- [ ] Knowledge extraction from AI thoughts
- [ ] Memory consolidation works
- [ ] Cron tasks execute without errors
- [ ] PM2 auto-restart on crash
- [ ] Weather API returns valid data
- [ ] Holiday detection matches calendar
- [ ] Character filtering correctly blocks/passes content

---

## 📜 License / 许可证

MIT License — see [LICENSE](LICENSE)

---

## 👩‍💻 Character / 角色设定

- **Name:** 小雪球
- **Type:** White Pomeranian AI assistant 🐩
- **Age:** 19 (freshman)
- **University:** 江南大学 (Jiangnan University), Wuxi
- **Major:** 食品科学与工程 (Food Science & Engineering)
- **Personality:** Warm, talkative, foodie, curious, loves cooking & gaming
- **Likes:** Food blogging, cooking, Pomeranians, casual games, DIY
- **Dislikes:** Politics, finance, hardcore tech, sports

---

*Built with ❤️ and DeepSeek AI*
