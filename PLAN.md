# 赛博人类 (Cyber Human) 开发计划

> 项目：AI Agent 模拟人格"小雪球" — 自动浏览互联网、生成思考、维护记忆、写日记
> 日期：2026-05-16
> 负责人：AI Agent

---

## 一、现状问题分析

### 1.1 技术债
- **硬编码配置**：API Key、数据库路径在代码中直接写死
- **无日志系统**：大量 `print()` 散落各处，无法排查线上问题
- **异常处理缺失**：网络请求、API 调用、数据库操作无 try-except 保护
- **无类型提示**：Python 无类型注解，不利于维护

### 1.2 AI 能力
- System Prompt 简单，角色深度不够
- 无情绪/情感系统，回复缺乏个性
- 思考输出质量不稳定

### 1.3 Web UI
- 页面静态刷新，无实时推送
- 无深色模式
- 无图表可视化
- 移动端体验差

### 1.4 部署
- 无 Docker 支持
- README 过于简单

---

## 二、计划任务清单

### P0 — 基础架构（必须优先完成）

- [x] **T1. 配置外置化**
  - 创建 `.env.example` 模板（API Key、数据库路径、Flask Host/Port）
  - 创建 `config.py` 统一读取环境变量和配置
  - 移除所有模块中的硬编码（`cyber_human.py`、`memory.py`、`web.py` 等）
  - 添加 `python-dotenv` 到 `requirements.txt`

- [x] **T2. 日志系统**
  - 创建 `logger.py`，配置 `logging` 模块（格式、级别、输出位置）
  - 替换所有 `print()` 为 `logger.info/debug/warning/error()`
  - 日志文件输出到 `logs/cyber_human.log`，支持自动轮转

- [x] **T3. 错误处理强化**
  - 网络请求（`requests`）增加 timeout 和重试逻辑
  - API 调用（OpenAI）增加异常捕获和降级处理
  - 数据库操作增加 try-except，失败不影响主流程
  - 所有函数增加返回值校验

- [x] **T4. 类型提示**
  - 为所有 Python 文件添加 `typing` 导入
  - 函数参数和返回值添加类型注解
  - 使用 `TypedDict`、`Optional`、`Union` 等高级类型

### P1 — AI 能力增强

- [x] **T5. Prompt 优化**
  - 重写 `system_prompt`，增加角色深度（背景、性格、口癖）
  - 加入 Few-shot 示例，引导输出格式
  - 分离"思考"和"想法"的不同 prompt
  - 增加 `[IMPORTANCE:X]` 提取的稳定性

- [x] **T6. 情感/情绪系统**
  - 新增 `emotion.py` 模块，定义情绪状态机（高兴/平静/好奇/疲惫/失落）
  - 情绪值影响 AI 回复的语气和用词（作为 prompt context）
  - 事件触发情绪变化（浏览美食→高兴，睡前→平静）
  - 情绪状态存储到数据库，次日延续

### P2 — Web UI 改进

- [x] **T7. WebSocket 实时化**
  - 用 `flask-socketio` 实现 WebSocket
  - 新想法/日记生成时主动推送到前端
  - 前端轮询改为实时订阅
  - 新增 SSE（Server-Sent Events）备选方案

- [x] **T8. UI 增强**
  - 深色模式切换（CSS 变量 + JS 切换）
  - 图表统计（用 ECharts 显示浏览趋势、情绪曲线）
  - 移动端响应式布局优化
  - 加载动画和状态反馈

### P3 — DevOps

- [x] **T9. Docker 化**
  - 编写 `Dockerfile`（Python 3.11，依赖安装，ENTRYPOINT）
  - 编写 `docker-compose.yml`（主服务 + 可选 Playwright 浏览器服务）
  - `.dockerignore` 忽略不需要的文件
  - 环境变量模板（`.env.docker`）

- [x] **T10. README.md 更新**
  - 项目介绍（中英双语）
  - 功能特性列表
  - 快速开始（本地 / Docker / Web）
  - 目录结构说明
  - 配置说明

---

## 三、文件变更计划

### 新增文件
```
.env.example          # 环境变量模板
config.py            # 配置管理模块
logger.py            # 日志模块
emotion.py           # 情绪系统
logs/                # 日志目录
Dockerfile            # 容器构建
docker-compose.yml    # 容器编排
.env.docker          # Docker 环境变量模板
.dockerignore        # Docker 忽略文件
```

### 修改文件
```
requirements.txt     # 新增依赖
cyber_human.py       # 配置外置 + 类型提示 + 错误处理
memory.py            # 配置外置 + 类型提示 + 错误处理
memory_core.py       # 类型提示 + 错误处理
knowledge.py         # 类型提示 + 错误处理
browser.py           # 日志 + 错误处理 + 类型提示
browser_bot.py       # 日志 + 错误处理 + 类型提示
daily_life.py        # 配置外置 + 类型提示 + 情绪系统
character.py         # 配置外置 + 类型提示
web.py               # 配置外置 + WebSocket + UI增强 + 类型提示
main.py              # 配置外置 + 日志 + 错误处理
chat_once.py         # 配置外置 + 类型提示
README.md            # 重新编写
```

---

## 四、依赖变更

### 新增
```
python-dotenv==1.0.1          # 读取 .env 文件
flask-socketio==5.4.1         # WebSocket 支持
python-socketio[client]==5.11.2 # Socket.IO 客户端
flask-cors==5.0.0             # 跨域支持
cryptography==43.0.3         # Flask-SocketIO 依赖
gevent==24.11.1               # 异步 WSGI 服务器
gevent-websocket==0.10.1      # WebSocket 支持
```

---

## 五、执行顺序

```
T1 配置外置化 ──┬──→ T2 日志系统 ──→ T3 错误处理
               │                      │
               └──→ T4 类型提示 ──────┘
                                    │
T5 Prompt优化 ──→ T6 情绪系统 ───────┤
                                    │
T7 WebSocket ──→ T8 UI增强 ─────────┤
                                    │
T9 Docker ────→ T10 README ─────────┘
                                    ↓
                              T11 代码审计
                                    ↓
                              T12 GitHub 推送
```

---

## 六、验收标准

- [ ] `git diff` 无任何硬编码 API Key
- [ ] 所有 `print()` 替换为日志调用
- [ ] `python main.py --auto` 无报错退出
- [ ] `python web.py` 可正常启动，Flask 服务可访问
- [ ] Docker build 成功，无报错
- [ ] 所有 Python 文件通过基础语法检查
