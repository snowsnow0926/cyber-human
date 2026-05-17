# 测试清单 v2.0 - 赛博人类 CyberHuman

> 本清单用于 v2.0 重构后功能验证。每次代码更新后按顺序执行 P0 → P1 → P2。
> 更新日期：2026-05-17

---

## 环境准备（首次运行）

```bash
# 1. 确认 .env 文件存在且包含 DEEPSEEK_API_KEY
# 2. 确认 Python 版本 >= 3.10
python --version

# 3. 安装依赖（新增了部分包）
pip install -r requirements.txt

# 4. 启动 Web 服务
py web.py
# 浏览器打开 http://localhost:5010
```

---

## P0 - 静态检查（无需运行服务）

| # | 测试项 | 命令 | 预期结果 | 状态 |
|---|--------|------|---------|------|
| P0-1 | Python 语法检查 | `py -m py_compile memory.py cyber_human.py daily_life.py browser.py character.py web.py main.py` | 无输出 | |
| P0-2 | 无 bare `except:` | `rg "except:\s*$" --type py` | 无匹配 | |
| P0-3 | `.env` 不在 git | `git ls-files .env` | 无输出 | |
| P0-4 | 废弃模块已删除 | 确认 friends.py, knowledge.py, emotion.py, memory_core.py, weather.py 不存在 | 文件不存在 | |
| P0-5 | API 路由完整性 | 检查 web.py 是否有所有必需路由 | 无 import 错误 | |
| P0-6 | JS 语法检查 | `node --check static/js/app.js`（如 Node 可用） | 无 SyntaxError | |

---

## P1 - 服务启动与页面加载

| # | 测试项 | 操作 | 预期结果 | 状态 |
|---|--------|------|---------|------|
| P1-1 | 服务启动 | `py web.py`，浏览器打开 http://localhost:5010 | 无报错，页面正常显示 | |
| P1-2 | 标签导航 | 点击各标签按钮（今日浏览/想法/日记/投喂/统计/聊天/控制） | 标签切换正常 | |
| P1-3 | 今日浏览 | 默认标签页 | 显示浏览记录列表，无报错 | |
| P1-4 | 想法 | 点击「想法」标签 | 显示想法列表，带标签和重要度 | |
| P1-5 | 日记 | 点击「日记」标签 | 显示日记列表 | |
| P1-6 | 投喂-界面 | 点击「投喂」标签 | 显示大文本框 + 提交按钮 + 历史记录 | |
| P1-7 | 投喂-提交 | 在文本框输入测试内容，点击「投喂给 AI」 | 显示"AI 正在分析..."后显示结果 | |
| P1-8 | 投喂-历史 | 投喂后查看历史 | 新记录出现在列表顶部 | |
| P1-9 | 统计 | 点击「统计」 | 显示数字卡片 + 记忆层级饼图 | |
| P1-10 | 聊天 | 切换到「聊天」标签，输入文字发送 | 小雪球回复对话 | |
| P1-11 | 控制-模拟 | 点击「模拟一天」 | 日志显示"模拟已启动" | |
| P1-12 | 控制-清除 | 点击「清除今日」 | 确认后今日数据清空 | |
| P1-13 | 时间线 | 点击「时间线」，选择日期 | 显示该日各时段活动 | |
| P1-14 | 深色模式 | 点击右上角月亮按钮 | 界面切换深色/浅色主题 | |

---

## P2 - 控制面板模拟（需实际运行）

| # | 测试项 | 操作 | 预期结果 | 状态 |
|---|--------|------|---------|------|
| P2-1 | 模拟一天 | 控制面板 → 「模拟一天」 | 日志逐时段显示（起床/早餐/上网学习...），完成后 UI 自动刷新 | |
| P2-2 | 想法生成 | 模拟结束后 | 「想法」标签有新条目，带来源、情绪、标签、重要度 | |
| P2-3 | 记忆层级 | 多次模拟后查看统计 | 饼图显示短期/中期/长期分布 | |
| P2-4 | 投喂触发想法 | 投喂内容后切换到「想法」 | 新想法出现在列表顶部 | |
| P2-5 | 单时段模拟 | `py main.py --slot "起床"` | 仅执行起床时段，无报错 | |
| P2-6 | 命令行对话 | `py main.py --chat`，输入 `你好` | 小雪球回复 | |

---

## P3 - 数据库验证

| # | 测试项 | 命令 | 预期结果 | 状态 |
|---|--------|------|---------|------|
| P3-1 | thoughts 表有新字段 | `sqlite3 cyber_memory.db ".schema thoughts"` | 包含 tags, last_recalled, recall_count 列 | |
| P3-2 | feed_log 表存在 | `sqlite3 cyber_memory.db ".schema feed_log"` | 显示 CREATE TABLE feed_log | |
| P3-3 | WAL 模式 | `sqlite3 cyber_memory.db "PRAGMA journal_mode;"` | `wal` | |
| P3-4 | Token 记录 | `sqlite3 cyber_memory.db "SELECT COUNT(*) FROM token_usage;"` | `> 0`（运行过模拟后） | |
| P3-5 | 记忆层级 | `sqlite3 cyber_memory.db "SELECT tier, COUNT(*) FROM thoughts GROUP BY tier;"` | 分布合理 | |

---

## P4 - 投喂功能专项

| # | 测试项 | 操作 | 预期结果 | 状态 |
|---|--------|------|---------|------|
| P4-1 | 投喂美食内容 | 粘贴美食相关帖子 | 标签包含"美食"，想法与内容相关 | |
| P4-2 | 投喂空内容 | 不输入直接点提交 | 显示"请输入内容" | |
| P4-3 | 投喂长内容 | 粘贴超长文本（>5000字） | 返回错误提示 | |
| P4-4 | 投喂后想法联动 | 投喂后访问「想法」标签 | 新想法显示 source="投喂" | |
| P4-5 | WebSocket 推送 | 投喂时打开 F12 Console | 无 WebSocket 报错 | |

---

## P5 - 回归测试

| # | 测试项 | 验证方式 | 状态 |
|---|--------|---------|------|
| R1 | 数据库读写 | 运行模拟后刷新页面，数据应增加 | |
| R2 | 想法生成 | 运行模拟后「想法」标签有新条目 | |
| R3 | 记忆巩固 | `py main.py --once` 日志显示 `consolidate` 相关日志 | |
| R4 | WebSocket 推送 | 模拟结束后 UI 自动刷新数据（无需手动刷新） | |
| R5 | 聊天对话 | 在聊天标签多轮对话正常 | |

---

## 问题排查

| 症状 | 可能原因 | 解决方法 |
|------|---------|---------|
| 所有按钮无响应 | JS 语法错误 | 浏览器 F12 Console 查看 `SyntaxError` |
| 页面空白 | 静态文件 404 | 确认 static/js/app.js 等文件存在 |
| 投喂失败 | API 调用报错 | 后端未启动或 API Key 无效 |
| 模拟启动失败 | /api/control/simulate 路由缺失 | 检查 web.py 路由定义 |
| 想法标签不显示 | memory.py 返回字段名不匹配 | 检查 Thoughts 模型字段名与 SQL 列名 |
| GitHub push 失败 | 网络问题 | 检查代理设置或稍后重试 |

---

## 文件变更记录（v2.0）

### 新增
- `memory.py` — tag+importance 记忆系统
- `README-v2.md` — v2.0 功能说明
- `TEST_CHECKLIST-v2.md` — 本测试清单

### 重写
- `cyber_human.py` — 记忆→想法闭环 + 投喂分析
- `daily_life.py` — 简化时段引擎
- `browser.py` — HTTPBrowser 类
- `character.py` — 精简角色设定
- `web.py` — 极简 Flask 路由 + 投喂 API
- `static/js/app.js` — 极简前端 + 投喂 UI
- `templates/index.html` — 移除知识/朋友圈，新增投喂标签
- `main.py` — 简化入口

### 删除
- `friends.py` — 朋友圈系统
- `knowledge.py` — 知识库
- `emotion.py` — 情绪系统
- `memory_core.py` — 巩固逻辑并入 memory.py
- `holiday.py` — 节日系统
- `health_check.py` — 健康检查
- `weather.py` — 天气系统
- `browser_bot.py` — Playwright 爬虫
