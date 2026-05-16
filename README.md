# 赛博人类 (Cyber Human)

> 🤖 AI Persona Simulation — 让 AI 人格"小雪球"自主上网冲浪、思考、记忆、写日记

[English](#english) | 中文

---

## 功能特性

- 🌐 **自动浏览** — HTTP API + Playwright 双引擎抓取 B站、知乎、微博热搜等平台
- 💭 **AI 思考** — 基于 DeepSeek 大模型，对浏览内容生成个性化想法
- 🧠 **三层记忆** — 短期记忆 → 中期记忆 → 长期记忆，自动晋级/遗忘
- 📚 **知识学习** — 从内容中提取知识要点，支持分类和间隔复习
- 😊 **情绪系统** — 动态情绪状态影响 AI 回复风格
- 📝 **日记生成** — 每日自动总结，情感丰富的日记
- 💬 **实时对话** — Web UI 内置聊天界面
- 📊 **数据可视化** — 记忆分布、知识分类、情绪曲线图表
- 🌙 **深色模式** — 舒适的暗色主题支持
- 🐳 **Docker 支持** — 一键部署，开箱即用

---

## 快速开始

### 前置要求

- Python 3.11+
- DeepSeek API Key

### 1. 克隆 & 安装

```bash
git clone https://github.com/yourname/cyber-human.git
cd cyber-human

# 创建虚拟环境（推荐）
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
# .venv\Scripts\activate   # Windows

# 安装依赖
pip install -r requirements.txt
```

### 2. 配置

```bash
cp .env.example .env
# 编辑 .env，填入 DEEPSEEK_API_KEY
```

### 3. 运行

```bash
# 方式一：Web 服务（推荐）
python web.py
# 访问 http://localhost:5010

# 方式二：命令行完整一天模拟
python main.py

# 方式三：交互式对话
python main.py --chat

# 方式四：自动模式（用于 cron 定时）
python main.py --auto
```

### 4. Docker 部署

```bash
cp .env.example .env
# 填入 DEEPSEEK_API_KEY

docker-compose up -d
# 访问 http://localhost:5010
```

### 5. 定时任务（Linux/macOS）

```bash
crontab -e
# 每天早8点和晚8点各跑一次
0 8,20 * * * cd /path/to/cyber-human && python main.py --auto >> daily.log 2>&1
```

---

## 项目结构

```
cyber-human/
├── config.py            # 配置管理（环境变量读取）
├── logger.py            # 日志模块
├── emotion.py           # 情绪系统
├── cyber_human.py       # AI 大脑（DeepSeek API）
├── memory.py            # SQLite 数据库层
├── memory_core.py       # 三层记忆架构
├── knowledge.py         # 知识学习系统
├── browser.py           # HTTP 浏览器抓取
├── browser_bot.py       # Playwright 浏览器机器人
├── daily_life.py        # 日常生活引擎
├── character.py         # 角色设定
├── main.py              # CLI 主入口
├── chat_once.py         # 单次对话工具
├── web.py               # Flask + SocketIO Web 服务
├── templates/
│   └── index.html       # Web UI 主页面
├── static/
│   ├── css/style.css    # 样式（含深色模式）
│   └── js/app.js       # 前端交互逻辑
├── Dockerfile           # Docker 构建
├── docker-compose.yml   # 容器编排
├── .env.example         # 环境变量模板
├── requirements.txt     # Python 依赖
└── PLAN.md              # 开发计划
```

---

## 配置说明

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `DEEPSEEK_API_KEY` | (必填) | DeepSeek API 密钥 |
| `DEEPSEEK_BASE_URL` | `https://api.deepseek.com` | API 端点 |
| `DEEPSEEK_MODEL` | `deepseek-v4-flash` | 模型名称 |
| `DB_PATH` | `cyber_memory.db` | SQLite 数据库路径 |
| `LOG_LEVEL` | `INFO` | 日志级别 |
| `FLASK_PORT` | `5010` | Web 服务端口 |
| `LLM_TEMPERATURE` | `0.8` | LLM 温度参数 |
| `LLM_TIMEOUT` | `60` | API 超时（秒） |

---

## Web UI 预览

| 标签页 | 功能 |
|--------|------|
| 🌐 今日浏览 | 今日所有浏览记录 |
| 📋 时间线 | 按时间顺序展示浏览和想法 |
| 💭 想法 | 所有想法，含重要度和记忆层级标签 |
| 📝 日记 | 日记列表，支持一键生成今日日记 |
| 📱 手机 | 手机模拟器视图 |
| 📊 统计 | 数据统计和 ECharts 图表 |
| 📚 知识 | 知识库，按分类展示 |
| 💬 聊天 | 与小雪球实时对话 |
| ⚙️ 控制 | 模拟一天、清除数据等控制 |

---

## 角色设定

**小雪球** — 一个 19 岁的大一女生，就读于江南大学食品科学与工程专业，家乡江苏无锡。

- 性格温和友善，有点小话痨
- 对美食和烹饪有天然热情
- 超级喜欢博美犬
- 喜欢轻松治愈类游戏
- 刚上大学，对一切充满好奇

---

## 开发指南

### 添加新的浏览器数据源

编辑 `browser.py` 中的 `SOURCE_CONFIGS` 字典，添加新的平台配置。

### 自定义角色

编辑 `character.py` 中的 `CharacterProfile`，修改兴趣、性格等设定。

### 扩展情绪事件

编辑 `emotion.py` 中的 `_event_effects` 字典，添加新的情绪触发词。

---

## License

MIT License

---

<a name="english"></a>

## Cyber Human (English)

An AI persona simulation where "小雪球" (Xiaoxueqiu) autonomously browses the internet, generates thoughts, maintains memories, writes diaries, and chats with users.

Built with Python, DeepSeek API, Flask, and SQLite.

### Quick Start

```bash
pip install -r requirements.txt
cp .env.example .env  # Fill in DEEPSEEK_API_KEY
python web.py          # Start web server on :5010
```
