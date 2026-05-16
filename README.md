# Cyber Human — AI Persona "Xiaoxueqiu"

[中文](#chinese) | [English](#english)

---

> An AI persona simulation where **Xiaoxueqiu** (小雪球), a 19-year-old freshman at Jiangnan University, autonomously lives her daily life — browsing the internet, thinking about what she reads, writing diaries, building memories, and chatting with you.

---

<a name="english"></a>

## 🌟 Features

### 🕐 12-Slot Daily Life Engine
A full day is divided into 12 time slots — *wake up, breakfast, morning study, walk, lunch, afternoon explore, tea break, dinner, evening entertainment, shower, bedtime reflection, sleep*. Each slot runs independently with different behavior:
- **Routine slots** (70% template / 30% AI-generated mini-events)
- **Browse slots** (weighted source selection → fetch → interest check → thought + knowledge)
- **Reflect slot** (AI bedtime reflection)
- **Sleep slot**

### 🌐 Multi-Source Browsing
Fetches real-time content from:
- Baidu Hot Search (百度热搜)
- Bilibili Trending (B站热门)
- Zhihu Hot List (知乎热榜)
- Xiaohongshu (小红书)
- IThome, People.cn RSS feeds

### 🧠 Intelligent Content Processing
All fetched content is saved as browse history. Then:
- **Interesting content** → AI generates personalized thoughts + extracts knowledge points (token-consuming)
- **Uninteresting content** → Marked as "not interested, didn't click" (zero token cost)
- Mimics real human browsing behavior naturally

### ✨ AI-Generated Micro-Events
30% of routine slots trigger AI to generate unique mini-stories (e.g., "A stray cat rubbed against my ankle when I stepped outside..."), creating unpredictable daily narratives.

### 📖 Timeline UI
Grouped timeline view showing the full day at a glance:
- 12-slot schedule overview with event markers
- Browse and thought records nested under each time slot
- Date navigation (← → arrows + date picker)
- Supports past/future date browsing

### 📱 Phone Notifications
Simulated phone lock-screen notifications summarizing what Xiaoxueqiu browsed today.

### 🧠 3-Tier Memory System
- Short-term → Mid-term → Long-term memory auto-promotion
- Forgetting curve based on importance and recall frequency
- Night consolidation routine

### 📚 Knowledge Base
AI extracts knowledge points from browsing content, categorized by domain, with spaced repetition review.

### 😊 Emotion System
Dynamic emotional state (curious, happy, confused, scared, sad, angry, surprised, calm) that changes based on what she reads and experiences, affecting her thought style.

### 📝 Daily Diary
AI compiles the day's events into a heartfelt diary entry every night.

### 📊 Statistics Dashboard
ECharts-powered visualizations:
- Token usage & API call tracking
- Content source distribution
- Emotion history charts
- Memory tier distribution
- Browsing/thought counts

### 🕹️ Control Panel
- Clear all data
- Simulate a specific day
- Browse historical data by date

### 💬 Real-time Chat
Built-in WebSocket-powered chat interface. Talk to Xiaoxueqiu directly.

### 🌙 Dark Mode
Comfortable dark theme across all UI.

### 🐳 Docker Support
One-click deployment with docker-compose.

---

## Quick Start

```bash
# Clone & setup
git clone https://github.com/snowsnow0926/cyber-human.git
cd cyber-human
pip install -r requirements.txt

# Configure API key (DeepSeek / OpenAI compatible)
cp .env.example .env
# Edit .env, fill in DEEPSEEK_API_KEY

# Run web server
python web.py
# Open http://localhost:5010
```

### Docker

```bash
cp .env.example .env
docker-compose up -d
```

---

## Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `DEEPSEEK_API_KEY` | (required) | LLM API key |
| `DEEPSEEK_BASE_URL` | `https://api.deepseek.com` | API endpoint |
| `DEEPSEEK_MODEL` | `deepseek-v4-flash` | Model name |
| `DB_PATH` | `cyber_memory.db` | SQLite database path |
| `FLASK_PORT` | `5010` | Web server port |
| `LLM_TEMPERATURE` | `0.8` | LLM temperature |
| `LLM_TIMEOUT` | `60` | API timeout (seconds) |

---

## Project Structure

```
cyber-human/
├── config.py              # Configuration
├── logger.py              # Logging
├── emotion.py             # Emotion system
├── cyber_human.py         # AI brain (LLM interface)
├── memory.py              # SQLite database layer
├── memory_core.py         # 3-tier memory system
├── knowledge.py           # Knowledge extraction & review
├── browser.py             # HTTP browser fetcher
├── browser_bot.py         # Playwright browser bot (fallback)
├── daily_life.py          # 12-slot daily life engine
├── character.py           # Character profile (interests, personality)
├── main.py                # CLI entry point
├── web.py                 # Flask + SocketIO web server
├── templates/
│   └── index.html         # SPA web UI
├── static/
│   ├── css/style.css      # Styles + dark mode
│   └── js/app.js          # Frontend logic
├── Dockerfile
├── docker-compose.yml
├── .env.example
└── requirements.txt
```

---

## Character Profile

**Xiaoxueqiu (小雪球)** — 19-year-old freshman, majoring in Food Science & Engineering at Jiangnan University, Wuxi, Jiangsu.

- Gentle and friendly, a bit chatty
- Passionate about food and cooking
- Loves Pomeranians (can't walk past one)
- Enjoys casual cozy games
- Curious about everything as a new college student

---

## Web UI Tabs

| Tab | Description |
|-----|-------------|
| 🌐 Today's Browsing | Browsing history for today |
| 📋 Timeline | Full day timeline with grouped slots |
| 💭 Thoughts | All AI-generated thoughts with importance & memory tier |
| 📝 Diary | Daily diary entries |
| 📱 Phone | Simulated phone notification screen |
| 📊 Stats | ECharts analytics dashboard |
| 📚 Knowledge | Knowledge base organized by category |
| 💬 Chat | Real-time chat with Xiaoxueqiu |
| ⚙️ Control | Admin panel (simulate day, clear data) |

---

## Tech Stack

- **Backend:** Python 3, Flask, SocketIO, SQLite
- **Frontend:** Vanilla JS SPA, ECharts, WebSocket
- **AI:** DeepSeek API (OpenAI-compatible)
- **Scraping:** HTTP requests + BeautifulSoup, optional Playwright
- **Deployment:** Docker, PM2, nginx

---

## License

MIT

---

<a name="chinese"></a>

## 赛博人类 — AI 人格"小雪球"

> AI 人格模拟系统，让"小雪球"——一个 19 岁江南大学大一女生——每天自主上网、思考、写日记、生成记忆，与你聊天互动。

完整中文介绍请切换上方语言标签查看，或访问项目 [GitHub Pages](https://github.com/snowsnow0926/cyber-human)。

---

*Made with ❤️ for the cyber-human experiment*
