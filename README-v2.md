# CyberHuman v2.0 功能说明

> 更新日期：2026-05-17
> 版本：v2.0

---

## 一、项目概述

CyberHuman（赛博人类）是一个 AI 人格模拟系统，让"小雪球"——一个 19 岁江南大学大一女生——每天自主上网、思考、生成记忆。

v2.0 以**记忆系统**为核心重构，架构极简化，AI 生成的想法会自动保存并影响后续思考。

---

## 二、核心模块

### 2.1 `memory.py` — 记忆系统（架构核心）

**数据模型：**

- `Thought` — 想法记录，含 tag 标签、importance 重要度、tier 层级、recall_count 召回次数
- `BrowseRecord` — 浏览记录
- `DiaryEntry` — 日记
- `FeedRecord` — 投喂记录

**关键方法：**

| 方法 | 说明 |
|------|------|
| `save_thought(content, tags, emotion, importance)` | 保存想法，自动判断 tier |
| `recall_related(keywords, limit)` | 关键词检索记忆，召回时 importance +1 |
| `decay_all()` | 每日睡前，短期记忆 importance -= 1 |
| `consolidate()` | 升降级：importance≥4 升中期，≥7+召回≥2 升长期 |
| `forget_memory(id)` | importance≤1 时删除 |
| `get_top_memories(limit)` | 获取印象最深的记忆（睡前反思用） |

**记忆层级：**
- 短期：importance 1-3，每日衰减
- 中期：importance 4-6
- 长期：importance 7-10

### 2.2 `cyber_human.py` — AI 大脑

**核心方法：**

| 方法 | 说明 |
|------|------|
| `think_about(content, source, keywords)` | 浏览内容 → 检索记忆 → 生成想法 → 保存记忆 |
| `analyze_feed(feed_content, keywords)` | 投喂分析：提取标签 + 生成想法 + 保存记忆 |
| `reflect_on_memories()` | 睡前回顾 Top 3 记忆，生成一句话回顾 |
| `chat(user_input, history)` | 对话模式 |
| `_call_llm(prompt, ...)` | LLM 调用，重试 3 次，自动提取 importance |

**关键设计：**
- `think_about()` 会在生成想法前调用 `recall_related()`，把相关记忆注入 prompt
- `analyze_feed()` 分两步：先提取标签，再生成想法，确保标签准确

### 2.3 `daily_life.py` — 12 时段引擎

**时段结构：**
- 08:00 起床（routine，30% AI 事件）
- 08:30 早餐（routine）
- 09:00 上网学习（browse）
- 11:00 出门散步（routine）
- 12:00 午餐时间（routine）
- 14:00 下午探索（browse）
- 16:00 下午茶/摸鱼（routine）
- 18:00 晚餐/刷热搜（browse）
- 20:00 晚间娱乐（browse）
- 22:00 洗漱整理（routine）
- 23:00 睡前反思（reflect）
- 00:00 进入梦乡（sleep）

**每日结束自动调用：**
- `memory.decay_all()` — 记忆衰减
- `memory.consolidate()` — 升降级

### 2.4 `browser.py` — 多平台爬虫

支持平台：B站热门、百度热搜、知乎热榜、IT之家、人民网、小红书

**方法：**
- `fetch(source, timeout)` — 抓取指定平台
- `browse_random(max_results)` — 随机抓取

### 2.5 `character.py` — 角色设定

- 兴趣关键词判断（两层：快速过滤 + AI 判断）
- `should_be_interested(title, summary)` — 是否感兴趣

### 2.6 `web.py` — Flask API

**简化后的路由：**

| 路由 | 方法 | 说明 |
|------|------|------|
| `/` | GET | 渲染 index.html |
| `/api/today` | GET | 今日浏览+想法 |
| `/api/thoughts` | GET | 全部想法，支持 `?tag=` 筛选 |
| `/api/timeline` | GET | 时间线视图，含日期回退 |
| `/api/stats` | GET | 统计数据 |
| `/api/diary` | GET | 日记列表 |
| `/api/diary/today` | POST | 手动写日记 |
| `/api/chat` | POST | 聊天对话 |
| `/api/feed` | POST | **投喂信息给 AI** |
| `/api/feed/history` | GET | 投喂历史 |
| `/api/control/simulate` | POST | 触发全天模拟 |
| `/api/control/clear` | POST | 清除今日数据 |
| `/api/status` | GET | 系统状态 |

### 2.7 `main.py` — 入口

| 参数 | 说明 |
|------|------|
| `--once` / `--auto` | 运行一天模拟后退出 |
| `--chat` | 交互式对话模式 |
| `--slot <标签>` | 只运行指定时段 |
| `--simulate-date YYYY-MM-DD` | 模拟指定日期 |

---

## 三、新功能：投喂系统

### 3.1 功能入口

**Web UI** — 点击「投喂」标签页，在大文本框粘贴任意内容（帖子、新闻、聊天记录等），点击「投喂给 AI」。

### 3.2 工作流程

```
用户粘贴内容
    ↓
POST /api/feed { content: "..." }
    ↓
cyber_human.analyze_feed()
    ↓
Step 1: 提取标签（AI 调用，temperature=0.3）
Step 2: 检索相关记忆（memory.recall_related）
Step 3: 生成想法（AI 调用，结合记忆上下文）
Step 4: 保存到 thoughts 表 + feed_log 表
Step 5: WebSocket 推送 thought_update
    ↓
前端显示：标签 + 想法 + 重要度
```

### 3.3 API 文档

**POST /api/feed**

Request:
```json
{
  "content": "粘贴的内容...",
  "keywords": ["可选关键词数组"]
}
```

Response:
```json
{
  "success": true,
  "thought": "AI 生成的想法文本",
  "tags": "美食,烹饪,生活",
  "importance": 7
}
```

**GET /api/feed/history?limit=50**

Response:
```json
{
  "data": [
    {
      "id": 1,
      "timestamp": "2026-05-17T...",
      "user_content": "粘贴的原文...",
      "ai_thought": "AI 生成的想法",
      "tags": "美食,烹饪",
      "emotion": "好奇",
      "importance": 7
    }
  ],
  "total": 10
}
```

---

## 四、已删除功能

以下功能在 v2.0 中已移除：

| 旧功能 | 旧路由 | 移除原因 |
|--------|--------|----------|
| 朋友圈 | `/api/moments` | 非核心，可后续按需加回 |
| 知识库 | `/api/knowledge` | Token 消耗高，实用价值低 |
| 情绪系统 | `/api/emotion` | 简化为极简状态存储 |
| 天气感知 | weather.py | 复杂度高，实用价值低 |
| 节日系统 | holiday.py | 非核心 |
| 健康检查 | health_check.py | 非核心 |
| Playwright 爬虫 | browser_bot.py | 依赖重，仅作为备用 |

---

## 五、技术栈

- **后端**：Python 3, Flask, Flask-SocketIO, SQLite (WAL 模式)
- **前端**：Vanilla JS SPA, ECharts, WebSocket
- **AI**：DeepSeek API (OpenAI-compatible)
- **爬虫**：HTTP requests + BeautifulSoup
- **部署**：Docker, 单文件启动脚本

---

## 六、配置项

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `DEEPSEEK_API_KEY` | (必填) | LLM API Key |
| `DEEPSEEK_BASE_URL` | `https://api.deepseek.com` | API 端点 |
| `DEEPSEEK_MODEL` | `deepseek-v4-flash` | 模型名 |
| `FLASK_PORT` | `5010` | Web 服务端口 |
| `LLM_TEMPERATURE` | `0.8` | LLM 温度 |
| `LLM_MAX_TOKENS` | `1024` | 最大 Token 数 |
| `DB_PATH` | `cyber_memory.db` | 数据库路径 |
| `LOG_LEVEL` | `INFO` | 日志级别 |

---

## 七、快速开始

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 配置 API Key
cp .env.example .env
# 编辑 .env 填入 DEEPSEEK_API_KEY

# 3. 启动 Web 服务
py web.py
# 浏览器打开 http://localhost:5010

# 4. 命令行模式（模拟一天）
py main.py --once
```
