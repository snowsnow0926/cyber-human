"""
赛博人类 Web 界面 - 入口
"""

from flask import Flask, render_template_string, jsonify, request
from memory import Memory
from cyber_human import CyberHuman
import sqlite3

app = Flask(__name__)

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>🐩 赛博人类 - 小雪球</title>
    <style>
        :root {
            --bg: #0f0f1a;
            --card-bg: #1a1a2e;
            --card-border: #2a2a4e;
            --text: #e0e0e0;
            --text-secondary: #888;
            --accent: #5a9eff;
            --accent-hover: #4a8eef;
            --chat-self: #95ec69;
            --chat-ai: #fff;
            --chat-self-text: #000;
            --chat-ai-text: #1a1a2e;
            --input-bg: #1a1a2e;
            --input-border: #2a2a4e;
        }
        body.light {
            --bg: #f5f5f5;
            --card-bg: #ffffff;
            --card-border: #e0e0e0;
            --text: #333;
            --text-secondary: #888;
            --accent: #5a9eff;
            --accent-hover: #4a8eef;
            --chat-self: #95ec69;
            --chat-ai: #fff;
            --chat-self-text: #000;
            --chat-ai-text: #333;
            --input-bg: #fff;
            --input-border: #ccc;
        }
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { 
            font-family: -apple-system, 'Segoe UI', sans-serif;
            background: var(--bg); color: var(--text);
            max-width: 800px; margin: 0 auto; padding: 20px;
            transition: background 0.3s, color 0.3s;
        }
        h1 { color: var(--accent); margin-bottom: 5px; font-size: 24px; }
        .subtitle { color: var(--text-secondary); font-size: 14px; margin-bottom: 20px; }
        .card {
            background: var(--card-bg); border-radius: 12px;
            padding: 16px; margin-bottom: 16px;
            border: 1px solid var(--card-border);
            transition: background 0.3s, border 0.3s;
        }
        .card h2 { color: var(--accent); font-size: 16px; margin-bottom: 10px; }
        .entry { 
            padding: 10px 0; border-bottom: 1px solid var(--card-border);
        }
        .entry:last-child { border: none; }
        .source { color: var(--accent); font-size: 12px; }
        .title { color: var(--text); font-size: 14px; margin: 4px 0; }
        .thought { color: #b0b0c0; font-size: 13px; line-height: 1.5; }
        body.light .thought { color: #555; }
        .time { color: var(--text-secondary); font-size: 11px; }
        .mood { color: #ffd700; }
        .chat-box { 
            display: flex; gap: 8px; margin-top: 10px;
        }
        .chat-box input {
            flex: 1; padding: 10px; border-radius: 8px;
            border: 1px solid var(--input-border); background: var(--input-bg);
            color: var(--text); font-size: 14px;
        }
        .chat-box button {
            padding: 10px 20px; border-radius: 8px;
            border: none; background: var(--accent); color: #fff;
            font-size: 14px; cursor: pointer;
        }
        .chat-box button:hover { background: var(--accent-hover); }
        #chat-messages {
            margin-top: 12px; max-height: 500px; overflow-y: auto;
            padding: 8px; display: flex; flex-direction: column; gap: 10px;
        }
        .bubble {
            max-width: 75%; padding: 10px 14px; border-radius: 12px;
            font-size: 14px; line-height: 1.5; position: relative;
            word-break: break-word;
        }
        .bubble-self {
            align-self: flex-end; background: var(--chat-self);
            color: var(--chat-self-text);
            border-bottom-right-radius: 4px;
        }
        .bubble-ai {
            align-self: flex-start; background: var(--chat-ai);
            color: var(--chat-ai-text);
            border-bottom-left-radius: 4px;
            box-shadow: 0 1px 2px rgba(0,0,0,0.1);
        }
        .bubble-time {
            font-size: 10px; color: var(--text-secondary);
            margin-top: 4px; text-align: right;
        }
        .bubble-ai .bubble-time { text-align: left; }
        .bubble-avatar {
            width: 28px; height: 28px; border-radius: 50%;
            display: flex; align-items: center; justify-content: center;
            font-size: 16px; flex-shrink: 0;
        }
        .bubble-row {
            display: flex; gap: 6px; align-items: flex-end;
        }
        .bubble-row.ai { flex-direction: row; }
        .bubble-row.self { flex-direction: row-reverse; }
        .chat-input-area {
            display: flex; gap: 8px; padding: 12px;
            background: var(--card-bg); border: 1px solid var(--card-border);
            border-radius: 12px; margin-top: 10px;
        }
        .chat-input-area input {
            flex: 1; padding: 8px 12px; border: none; outline: none;
            background: transparent; color: var(--text); font-size: 14px;
        }
        .chat-input-area button {
            background: var(--accent); color: #fff;
            border: none; padding: 8px 16px; border-radius: 8px;
            font-size: 14px; cursor: pointer;
        }
        .nav { display: flex; gap: 8px; margin-bottom: 16px; flex-wrap: wrap; }
        .nav a {
            padding: 6px 14px; border-radius: 6px;
            background: var(--card-bg); color: var(--text-secondary); text-decoration: none;
            font-size: 13px; border: 1px solid transparent;
        }
        .nav a.active { background: var(--accent); color: #fff; }
        .status-dot {
            display: inline-block; width: 8px; height: 8px;
            border-radius: 50%; margin-right: 6px;
        }
        .online { background: #4ade80; }
        .empty { color: var(--text-secondary); font-style: italic; padding: 10px 0; }
        .stat-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; }
        .stat-item {
            background: #12122a; border-radius: 8px; padding: 12px;
            text-align: center;
        }
        body.light .stat-item { background: #f0f0f5; }
        .stat-num { color: var(--text); font-size: 20px; font-weight: bold; }
        .stat-label { color: var(--text-secondary); font-size: 12px; margin-top: 4px; }
        .nav-right { margin-left: auto; display: flex; gap: 8px; align-items: center; }
        .theme-btn {
            background: none; border: none; cursor: pointer;
            font-size: 18px; padding: 4px 8px; border-radius: 6px;
            background: var(--card-bg); color: var(--text-secondary);
        }
        .theme-btn:hover { background: var(--accent); color: #fff; }

        /* Profile tab */
        .profile-avatar {
            width: 80px; height: 80px; border-radius: 50%;
            background: #1a2a4e; display: flex; align-items: center;
            justify-content: center; font-size: 48px; margin: 0 auto 12px;
        }
        .profile-name { font-size: 24px; font-weight: bold; text-align: center; }
        .profile-sig { color: var(--text-secondary); font-size: 13px; text-align: center; margin: 4px 0 16px; }
        .profile-info { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; }
        .profile-info-item {
            padding: 10px; background: #12122a; border-radius: 8px; text-align: center;
        }
        body.light .profile-info-item { background: #f0f0f5; }
        .profile-info-item .label { font-size: 11px; color: var(--text-secondary); }
        .profile-info-item .value { font-size: 14px; color: var(--text); font-weight: bold; margin-top: 2px; }
        .tag {
            display: inline-block; padding: 3px 10px; border-radius: 12px;
            background: #1a2a4e; color: var(--accent); font-size: 12px; margin: 3px;
        }
        body.light .tag { background: #e8f0ff; }
        .mood-display { text-align: center; font-size: 36px; margin: 8px 0; }
        .highlight { background: #ffd700; color: #000; padding: 0 2px; border-radius: 2px; }
        .stat-card {
            text-align: center; padding: 14px; background: #12122a;
            border-radius: 10px; border: 1px solid var(--card-border);
        }
        body.light .stat-card { background: #f0f0f5; }
        .stat-card .num { font-size: 28px; font-weight: bold; color: var(--accent); }
        .stat-card .lbl { font-size: 12px; color: var(--text-secondary); margin-top: 4px; }
        .search-box {
            width: 100%; padding: 12px 16px; border-radius: 10px;
            border: 1px solid var(--card-border); background: var(--card-bg);
            color: var(--text); font-size: 15px; outline: none;
        }
        .search-box:focus { border-color: var(--accent); }
        .source-tag {
            display: inline-block; padding: 2px 8px; border-radius: 6px;
            font-size: 11px; font-weight: bold; margin-right: 6px;
        }
        .source-browse { background: #2a4a2a; color: #4ade80; }
        .source-thought { background: #2a2a4a; color: #818cf8; }
        .source-diary { background: #4a2a2a; color: #f87171; }
        .source-knowledge { background: #2a3a2a; color: #34d399; }
    </style>
</head>
<body>
    <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:16px">
        <div>
            <h1>🐩 小雪球</h1>
            <div class="subtitle">赛博人类 · 生于 {{ birthday }}</div>
        </div>
        <div class="nav-right">
            <button class="theme-btn" onclick="toggleTheme()" id="theme-btn">🌙</button>
        </div>
    </div>

    <div class="nav">
        <a href="?tab=browse" class="{{ 'active' if tab == 'browse' else '' }}">🌐 今日浏览</a>
        <a href="?tab=timeline" class="{{ 'active' if tab == 'timeline' else '' }}">📋 时间线</a>
        <a href="?tab=thoughts" class="{{ 'active' if tab == 'thoughts' else '' }}">💭 想法</a>
        <a href="?tab=diary" class="{{ 'active' if tab == 'diary' else '' }}">📝 日记</a>
        <a href="?tab=phone" class="{{ 'active' if tab == 'phone' else '' }}">📱 手机</a>
        <a href="?tab=profile" class="{{ 'active' if tab == 'profile' else '' }}">🧑 主页</a>
        <a href="?tab=stats" class="{{ 'active' if tab == 'stats' else '' }}">📊 统计</a>
        <a href="?tab=knowledge" class="{{ 'active' if tab == 'knowledge' else '' }}">📚 知识</a>
        <a href="?tab=chat" class="{{ 'active' if tab == 'chat' else '' }}">💬 聊天</a>
        <a href="?tab=search" class="{{ 'active' if tab == 'search' else '' }}">🔍 搜索</a>
        <a href="?tab=control" class="{{ 'active' if tab == 'control' else '' }}">⚙️ 控制</a>
    </div>

    {% if tab == "profile" %}
    <div class="card">
        <div class="profile-avatar">🐩</div>
        <div class="profile-name">{{ profile.name }}</div>
        <div class="profile-sig">{{ profile.sig }}</div>

        {% if profile.today_mood %}
        <div class="mood-display">{{ profile.today_mood_emoji }}</div>
        <div style="text-align:center;font-size:14px;color:var(--text-secondary);margin-bottom:16px">
            今日心情: {{ profile.today_mood }}
        </div>
        {% endif %}

        <div class="profile-info">
            <div class="profile-info-item">
                <div class="label">年龄</div>
                <div class="value">{{ profile.age }}岁</div>
            </div>
            <div class="profile-info-item">
                <div class="label">学校</div>
                <div class="value">{{ profile.school }}</div>
            </div>
            <div class="profile-info-item">
                <div class="label">专业</div>
                <div class="value">{{ profile.major }}</div>
            </div>
            <div class="profile-info-item">
                <div class="label">城市</div>
                <div class="value">{{ profile.city }}</div>
            </div>
        </div>
    </div>

    <div class="card">
        <h2>🧬 性格标签</h2>
        <div>
            {% for tag in profile.traits %}
            <span class="tag">{{ tag }}</span>
            {% endfor %}
        </div>
    </div>

    <div class="card">
        <h2>📊 统计卡片</h2>
        <div style="display:grid;grid-template-columns:repeat(4,1fr);gap:8px">
            <div class="stat-card">
                <div class="num">{{ profile.stats.browse }}</div>
                <div class="lbl">浏览</div>
            </div>
            <div class="stat-card">
                <div class="num">{{ profile.stats.thoughts }}</div>
                <div class="lbl">想法</div>
            </div>
            <div class="stat-card">
                <div class="num">{{ profile.stats.diaries }}</div>
                <div class="lbl">日记</div>
            </div>
            <div class="stat-card">
                <div class="num">{{ profile.stats.knowledge }}</div>
                <div class="lbl">知识</div>
            </div>
        </div>
    </div>

    <div class="card">
        <h2>💭 最近想法</h2>
        {% for t in profile.recent_thoughts %}
        <div class="entry">
            <div class="thought">{{ t.thought[:200] }}</div>
            <div class="time" style="margin-top:4px">{{ t.time[:16] }}</div>
        </div>
        {% else %}
        <div class="empty">还没有想法</div>
        {% endfor %}
    </div>

    {% elif tab == "search" %}
    <div class="card">
        <h2>🔍 搜索</h2>
        <form method="GET" action="." style="display:flex;gap:8px">
            <input type="hidden" name="tab" value="search">
            <input type="text" name="q" class="search-box" placeholder="搜索浏览记录、想法、日记、知识……" value="{{ search_q }}">
            <button type="submit" style="padding:8px 16px;border-radius:8px;border:none;background:var(--accent);color:#fff;font-size:14px;cursor:pointer">搜索</button>
        </form>
    </div>

    {% if search_q %}
    <div class="card">
        <h2>🔍 "{{ search_q }}" 的搜索结果</h2>
        {% for r in search_results %}
        <div class="entry" style="margin-bottom:6px">
            <div style="display:flex;align-items:center;margin-bottom:4px">
                {% if r.type == 'browse' %}
                <span class="source-tag source-browse">浏览</span>
                {% elif r.type == 'thought' %}
                <span class="source-tag source-thought">想法</span>
                {% elif r.type == 'diary' %}
                <span class="source-tag source-diary">日记</span>
                {% elif r.type == 'knowledge' %}
                <span class="source-tag source-knowledge">知识</span>
                {% endif %}
                <span class="time">{{ r.time[:16] }}</span>
            </div>
            <div class="thought">{{ r.text|safe }}</div>
        </div>
        {% else %}
        <div class="empty">没有找到相关结果</div>
        {% endfor %}
    </div>
    {% endif %}

    {% elif tab == "control" %}
    <div class="card">
        <h2>&#x2699;&#xFE0F; 控制面板</h2>
        <p style="color:var(--text-secondary);font-size:13px;margin-bottom:16px">手动控制小雪球的运行</p>
        
        <div style="display:flex;flex-direction:column;gap:12px">
            <button onclick="clearData()" style="background:#ff4757;color:#fff;border:none;padding:12px 20px;border-radius:10px;font-size:14px;cursor:pointer">
                &#x1F5D1; 清空所有数据
            </button>
            <div style="font-size:11px;color:var(--text-secondary);margin:-8px 0 0">删除浏览记录、想法、日记、知识、记忆，重新开始</div>
            
            <button onclick="simulateDay()" style="background:#2ed573;color:#fff;border:none;padding:12px 20px;border-radius:10px;font-size:14px;cursor:pointer">
                &#x25B6; 模拟一天生活
            </button>
            <div style="font-size:11px;color:var(--text-secondary);margin:-8px 0 0">让小雪球过完整一天（浏览内容、产生想法、学习知识），约需2-3分钟</div>
        </div>
        
        <div id="control-result" style="margin-top:12px;font-size:13px;color:var(--text-secondary);display:none"></div>
    </div>
    
    <script>
    async function clearData() {
        if (!confirm("确定要清空所有数据吗？此操作不可撤销！")) return;
        const btn = document.querySelector('button:nth-child(1)');
        btn.disabled = true;
        btn.textContent = '⏳ 清空中...';
        
        try {
            const r = await fetch('/cyber-human/api/clear_data', {method:'POST'});
            const d = await r.json();
            document.getElementById('control-result').style.display = 'block';
            document.getElementById('control-result').textContent = d.message;
            document.getElementById('control-result').style.color = d.success ? '#2ed573' : '#ff4757';
        } catch(e) {
            document.getElementById('control-result').style.display = 'block';
            document.getElementById('control-result').textContent = '请求失败: ' + e.message;
            document.getElementById('control-result').style.color = '#ff4757';
        }
        btn.disabled = false;
        btn.textContent = '🗑 清空所有数据';
    }
    
    async function simulateDay() {
        const btn = document.querySelector('button:nth-child(3)');
        btn.disabled = true;
        btn.textContent = '⏳ 模拟中（约2-3分钟）...';
        document.getElementById('control-result').style.display = 'block';
        document.getElementById('control-result').textContent = '⏳ 正在模拟，请稍候...';
        document.getElementById('control-result').style.color = '#ffa502';
        
        try {
            const r = await fetch('/cyber-human/api/simulate_day', {method:'POST'});
            const d = await r.json();
            document.getElementById('control-result').textContent = d.message;
            document.getElementById('control-result').style.color = d.success ? '#2ed573' : '#ff4757';
        } catch(e) {
            document.getElementById('control-result').textContent = '请求失败: ' + e.message;
            document.getElementById('control-result').style.color = '#ff4757';
        }
        btn.disabled = false;
        btn.textContent = '▶ 模拟一天生活';
    }
    </script>
    
    {% elif tab == "chat" %}
    <div class="card">
        <h2>💬 跟小雪球聊天</h2>
        <div id="chat-messages">
            {% for msg in chat_history %}
            <div class="bubble-row {{ 'self' if msg.role == 'user' else 'ai' }}">
                {% if msg.role != 'user' %}
                <div class="bubble-avatar" style="background:#1a2a4e">🐩</div>
                {% endif %}
                <div>
                    <div class="bubble {{ 'bubble-self' if msg.role == 'user' else 'bubble-ai' }}">
                        {{ msg.text }}
                    </div>
                    <div class="bubble-time">{{ msg.time }}</div>
                </div>
                {% if msg.role == 'user' %}
                <div class="bubble-avatar" style="background:#2a2a4e">👤</div>
                {% endif %}
            </div>
            {% endfor %}
        </div>
        <div class="chat-input-area">
            <input type="text" id="chat-input" placeholder="说点什么……"
                   onkeydown="if(event.key==='Enter') sendChat()">
            <button onclick="sendChat()">发送</button>
        </div>
    </div>
    <script>
        async function sendChat() {
            const input = document.getElementById('chat-input');
            const container = document.getElementById('chat-messages');
            const msg = input.value.trim();
            if (!msg) return;
            
            const now = new Date();
            const timeStr = now.getHours().toString().padStart(2,'0') + ':' + now.getMinutes().toString().padStart(2,'0');
            
            // Add user bubble
            const userBubble = document.createElement('div');
            userBubble.className = 'bubble-row self';
            userBubble.innerHTML = '<div><div class="bubble bubble-self">' + escapeHtml(msg) + '</div><div class="bubble-time">' + timeStr + '</div></div><div class="bubble-avatar" style="background:#2a2a4e">👤</div>';
            container.appendChild(userBubble);
            input.value = '';
            
            // Add loading
            const loadingBubble = document.createElement('div');
            loadingBubble.className = 'bubble-row ai';
            loadingBubble.id = 'chat-loading';
            loadingBubble.innerHTML = '<div class="bubble-avatar" style="background:#1a2a4e">🐩</div><div><div class="bubble bubble-ai">小雪球正在思考……</div></div>';
            container.appendChild(loadingBubble);
            container.scrollTop = container.scrollHeight;
            
            try {
                const res = await fetch('chat_api', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({message: msg})
                });
                const data = await res.json();
                
                document.getElementById('chat-loading').remove();
                
                const aiBubble = document.createElement('div');
                aiBubble.className = 'bubble-row ai';
                aiBubble.innerHTML = '<div class="bubble-avatar" style="background:#1a2a4e">🐩</div><div><div class="bubble bubble-ai">' + escapeHtml(data.reply) + '</div><div class="bubble-time">' + timeStr + '</div></div>';
                container.appendChild(aiBubble);
            } catch(e) {
                document.getElementById('chat-loading').remove();
                const errBubble = document.createElement('div');
                errBubble.className = 'bubble-row ai';
                errBubble.innerHTML = '<div class="bubble-avatar" style="background:#1a2a4e">🐩</div><div><div class="bubble bubble-ai">😅 网络开小差了……</div></div>';
                container.appendChild(errBubble);
            }
            container.scrollTop = container.scrollHeight;
        }
        function escapeHtml(text) {
            return text.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
        }
    </script>

    {% elif tab == "timeline" %}
    <!-- 情绪表情 -->
    <div style="text-align:center;padding:8px;font-size:28px;margin-bottom:8px">{{ mood_emoji }}</div>
    
    <!-- 日期导航 -->
    <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:12px;padding:10px 14px;background:var(--card-bg);border-radius:12px;border:1px solid var(--card-border)">
        <a href="?tab=timeline&amp;date={{ prev_date }}" style="color:var(--text-secondary);text-decoration:none;font-size:20px">‹</a>
        <div style="text-align:center">
            <div style="font-size:15px;color:var(--text);font-weight:bold">{{ date_display if date_display is defined else time_now[:10] }}</div>
            <form style="margin-top:6px;display:flex;gap:6px" action="." method="GET">
                <input type="hidden" name="tab" value="timeline">
                <input type="date" name="date" value="{{ view_date }}" style="background:#222;color:#fff;border:1px solid #444;border-radius:6px;padding:4px 8px;font-size:12px">
                <button type="submit" style="background:#444;color:#fff;border:none;border-radius:6px;padding:4px 10px;font-size:12px;cursor:pointer">跳转</button>
            </form>
        </div>
        <a href="?tab=timeline&amp;date={{ next_date }}" style="color:var(--text-secondary);text-decoration:none;font-size:20px">›</a>
    </div>

    <!-- 日程总览 -->
    <div class="card">
        <h2>📋 日程</h2>
        <div style="display:grid;grid-template-columns:1fr 1fr;gap:6px;margin-top:8px">
            {% for s in all_slots %}
            <div style="background:#12122a;border-radius:8px;padding:10px 12px;
                        border-left:3px solid {{ s.color }};
                        display:flex;align-items:center;gap:8px">
                <span style="font-size:16px;font-weight:bold;color:{{ s.color }}">{{ s.time }}</span>
                <span style="font-size:13px;color:#ccc">{{ s.label }}</span>
                {% if s.status == 'pending' %}
                <span style="font-size:10px;color:#888;margin-left:auto">⏳</span>
                {% else %}
                <span style="font-size:10px;color:#4ade80;margin-left:auto">✅</span>
                {% endif %}
            </div>
            {% endfor %}
        </div>
    </div>
    
    <!-- 当前状态 -->
    {% if is_today %}
    <div style="text-align:center;padding:14px;background:linear-gradient(135deg,var(--card-bg),#2a1a3e);border-radius:12px;margin-bottom:16px;border:1px solid #3a2a4e">
        <div style="font-size:13px;color:#aaa;margin-bottom:4px">小雪球正在</div>
        <div style="font-size:18px;color:var(--text);font-weight:bold">
            {% if current_activity %}
            {{ mood_emoji }} {{ current_activity }}
            {% else %}
            💤 休息中
            {% endif %}
        </div>
        <div style="font-size:11px;color:#555;margin-top:6px">
            🕐 {{ now.strftime('%H:%M') }}
        </div>
    </div>
    {% endif %}
    
    <!-- 已发生的事件详情 -->
    {% if past_events %}
    <div class="card">
        <h2>📖 今天发生了什么</h2>
        {% for s in past_events %}
        <div class="entry" style="border-left:3px solid {{ s.color }};padding:10px 0 10px 14px;margin-bottom:8px">
            <div style="display:flex;align-items:center;gap:6px;margin-bottom:4px;flex-wrap:wrap">
                <span style="font-size:13px;font-weight:bold;color:{{ s.color }}">{{ s.time }}</span>
                {% if s.source_platform %}
                <span style="font-size:11px;background:#1a2a4e;color:var(--accent);padding:2px 8px;border-radius:4px">{{ s.source_platform }}</span>
                {% else %}
                <span style="font-size:12px;color:var(--text-secondary)">{{ s.label }}</span>
                {% endif %}
                {% if s.is_event %}
                <span style="font-size:10px;background:#3a2a1e;color:#ffd700;padding:2px 6px;border-radius:4px">✨ 事件</span>
                {% endif %}
            </div>
            {% if s.content %}
            <div style="color:#ccc;font-size:13px;line-height:1.6">{{ s.content[:200] }}</div>
            {% endif %}
            {% if s.thoughts %}
            <div style="margin-top:8px;padding:8px 10px;background:#12122a;border-radius:8px">
                {% for t in s.thoughts %}
                <div style="font-size:12px;color:#b0b0c0;margin-bottom:6px;line-height:1.5">
                    <span style="color:var(--accent)">{{ t.title.split('·')[0] if '·' in t.title else t.title }}</span><br>
                    💭 {{ t.text[:100] }}{% if t.text|length > 100 %}…{% endif %}
                </div>
                {% endfor %}
            </div>
            {% endif %}
        </div>
        {% endfor %}
    </div>
    {% else %}
    <div class="card">
        <div class="empty">今天还没开始呢 🌙</div>
    </div>
    {% endif %}

    {% elif tab == "knowledge" %}
    <div class="card">
        <h2>&#x1F4DA; 小雪球的知识库</h2>
        {% for k in knowledges %}
        <div class="entry">
            <div style="display:flex;justify-content:space-between;align-items:center">
                <span class="source">{{ k[4] }}</span>
                <span style="font-size:11px;color:var(--text-secondary)">
                    理解度: {% for i in range(k[6]) %}&#x1F9E0;{% endfor %}{% for i in range(5-k[6]) %}&#x1F90D;{% endfor %}
                </span>
            </div>
            <div class="thought">{{ k[3][:120] }}</div>
            <div class="time" style="font-size:11px">{{ k[1][:16] }} &#xB7; 复习{{ k[7] }}次</div>
        </div>
        {% else %}
        <div class="empty">还没有学到知识 &#x1F4D6;</div>
        {% endfor %}
    </div>

    {% elif tab == "diary" %}
        {% set current_date = namespace(d="") %}
        {% for d in diaries %}
        {% if d.date != current_date.d %}
        {% set current_date.d = d.date %}
        <div style="margin:12px 0 6px;font-size:13px;color:var(--text-secondary);font-weight:bold">📅 {{ d.date }}</div>
        {% endif %}
        <div class="card">
            <h2>📝 {{ d[0] }}</h2>
            <div class="mood">心情: {{ d[2] or '未记录' }}</div>
            <div class="thought" style="margin-top:8px">{{ d[1] }}</div>
        </div>
        {% else %}
        <div class="card"><div class="empty">还没有日记</div></div>
        {% endfor %}

    {% elif tab == "phone" %}
    <div class="card" style="max-width:360px;margin:0 auto">
        <div style="background:#000;border-radius:28px;padding:20px 16px;color:#fff;box-shadow:0 4px 20px rgba(0,0,0,0.6)">
            <div style="display:flex;justify-content:space-between;margin-bottom:16px;font-size:11px">
                <span>{{ time_now.split(' ')[1][:5] if ' ' in time_now else '' }}</span>
                <span>{{ mood_emoji }} 🔋 100%</span>
            </div>
            <div style="text-align:center;font-size:17px;font-weight:bold;margin-bottom:4px">{{ date_display if date_display is defined else time_now[:10] }}</div>
            <div style="text-align:center;font-size:10px;color:#555;margin-bottom:20px">—— 通知 ——</div>
            {% for n in notifications %}
            <div style="display:flex;gap:10px;margin-bottom:14px">
                <div style="width:30px;height:30px;border-radius:50%;background:#2a2a4e;display:flex;align-items:center;justify-content:center;font-size:14px;flex-shrink:0">{{ n.app[:1] if n.app else '💬' }}</div>
                <div style="flex:1;background:#1c1c1e;border-radius:14px;padding:10px 14px">
                    <div style="display:flex;justify-content:space-between;margin-bottom:4px">
                        <span style="font-size:11px;color:#888">{{ n.app }}</span>
                        <span style="font-size:10px;color:#555">{{ n.time[:5] if n.time else '' }}</span>
                    </div>
                    {% if n.url %}
                    <a href="{{ n.url }}" target="_blank" style="color:#fff;text-decoration:none;font-size:13px;display:block">{{ n.title[:50] }} ↗</a>
                    {% else %}
                    <div style="font-size:13px;line-height:1.4">{{ n.title[:60] }}</div>
                    {% endif %}
                </div>
            </div>
            {% else %}
            <div style="text-align:center;padding:40px 0">
                <div style="font-size:28px;margin-bottom:8px">📱</div>
                <div style="color:#555;font-size:13px">暂无通知</div>
            </div>
            {% endfor %}
        </div>
    </div>
    {% elif tab == "stats" %}
    <div class="card">
        <h2>📊 数据统计</h2>
        <div class="stat-grid">
            <div class="stat-item">
                <div class="stat-num">{{ stats.browse }}</div>
                <div class="stat-label">浏览记录</div>
            </div>
            <div class="stat-item">
                <div class="stat-num">{{ stats.thoughts }}</div>
                <div class="stat-label">想法</div>
            </div>
            <div class="stat-item">
                <div class="stat-num">{{ stats.diaries }}</div>
                <div class="stat-label">日记</div>
            </div>
            <div class="stat-item">
                <div class="stat-num">{{ stats.sources }}</div>
                <div class="stat-label">数据源</div>
            </div>
        </div>
    </div>
    <div class="card">
        <h2>⚡ Token 消耗</h2>
        <div style="font-size:13px;color:var(--text-secondary);line-height:1.8">
            <div>📅 <strong style="color:var(--text);">{{ time_now }}</strong></div>
            <div style="margin-top:6px">今日调用: <strong style="color:var(--text);">{{ stats.api_calls }}</strong> 次</div>
            <div>今日消耗: <strong style="color:var(--text);">{{ stats.today_tokens }}</strong> tokens</div>
            <div style="margin-top:10px;border-top:1px solid #333;padding-top:8px">总调用: <strong style="color:var(--text);">{{ stats.api_calls_total }}</strong> 次</div>
            <div>总消耗: <strong style="color:var(--text);">{{ stats.total_tokens }}</strong> tokens</div>
            <div style="margin-top:8px;font-size:11px;color:#555">
                按 DeepSeek V4 Flash 价格估算<br>
                今日费用: ~¥{{ stats.today_cost }}
                · 总计费用: ~¥{{ stats.total_cost }}
            </div>
        </div>
    </div>
    
    <div class="card">
        <h2>🧠 记忆系统（方向B）</h2>
        <div class="stat-grid">
            <div class="stat-item">
                <div class="stat-num">{{ memory_stats.tiers.短期 }}</div>
                <div class="stat-label">短期记忆</div>
            </div>
            <div class="stat-item">
                <div class="stat-num">{{ memory_stats.tiers.中期 }}</div>
                <div class="stat-label">中期记忆</div>
            </div>
            <div class="stat-item">
                <div class="stat-num">{{ memory_stats.tiers.长期 }}</div>
                <div class="stat-label">长期记忆</div>
            </div>
            <div class="stat-item">
                <div class="stat-num">{{ memory_stats.nights_consolidated }}</div>
                <div class="stat-label">夜间巩固</div>
            </div>
        </div>
    </div>

    <div class="card">
        <h2>&#x1F4DA; 知识体系</h2>
        <div class="stat-grid">
            <div class="stat-item">
                <div class="stat-num">{{ kstats.total }}</div>
                <div class="stat-label">学到的知识</div>
            </div>
            <div class="stat-item">
                <div class="stat-num">{{ kstats.forgotten }}</div>
                <div class="stat-label">已遗忘</div>
            </div>
        </div>
        <div style="margin-top:12px;font-size:13px;color:var(--text-secondary);line-height:1.8">
            {% for cat, cnt in kstats.categories.items() %}
            <span style="display:inline-block;background:#2a2a3a;padding:2px 8px;border-radius:8px;margin:2px">{{ cat }}: {{ cnt }}条</span>
            {% endfor %}
        </div>
    </div>

    {% elif tab == "thoughts" %}
    <div class="card">
        <h2>💭 全部想法</h2>
        {% for t in thoughts_all %}
        <div class="entry">
            <div class="source">{{ t[2] }}</div>
            <div class="thought">{{ t[3] }}</div>
            <div class="time" style="font-size:11px">{{ t[1][:16] }}
                {% if t|length > 5 and t[6] %}
                · {% if t[6] == 'long' %}🏛️{% elif t[6] == 'mid' %}📖{% else %}📄{% endif %} {{ t[6] }}
                {% endif %}
                {% if t|length > 7 and t[7] %}
                · {% if t[7] == '好奇' %}🤔{% elif t[7] == '开心' %}😊{% elif t[7] == '困惑' %}😕{% elif t[7] == '害怕' %}😨{% elif t[7] == '伤心' %}😢{% elif t[7] == '生气' %}😤{% elif t[7] == '惊讶' %}😲{% else %}😐{% endif %} {{ t[7] }}
                {% endif %}
            </div>
        </div>
        {% else %}
        <div class="empty">还没有想法</div>
        {% endfor %}
    </div>

    {% else %}
    <!-- browse tab + daily plan (default) -->
    {% if daily_plan %}
    <div class="card">
        <h2>📋 今天的计划</h2>
        <div class="mood">{{ daily_plan.mood }}</div>
        <div style="font-size:13px;color:var(--text-secondary);margin:8px 0">
            🎯 {{ daily_plan.focus }}
        </div>
        {% for item in daily_plan.plans %}
        <div class="entry" style="font-size:13px;display:flex;align-items:center;gap:8px">
            <span style="color:var(--accent)">{{ item.icon }}</span>
            <span style="background:#1a2a4e;color:var(--accent);font-size:11px;padding:2px 6px;border-radius:4px;white-space:nowrap">{{ item.platform_name }}</span>
            {{ item.reason }}
        </div>
        {% endfor %}
        {% if daily_plan.human_note %}
        <div style="margin-top:8px;padding:8px;background:#2a2a4e;border-radius:6px;font-size:12px;color:#ffd700">
            💬 人类留言: {{ daily_plan.human_note }}
        </div>
        {% endif %}
        <div style="margin-top:8px;font-size:11px;color:#555">
            状态: {{ "✅ 已完成" if daily_plan.done else "⏳ 计划中" }}
        </div>
    </div>
    {% endif %}
    <div class="card">
        <h2>🌐 今天浏览的内容</h2>
        {% for b in browse %}
        <div class="entry">
            <div class="source">{{ b[2] }}</div>
            <div class="title">{{ b[3] }}</div>
            <div class="time">{{ b[1][:16] }}</div>
        </div>
        {% else %}
        <div class="empty">今天还没冲浪</div>
        {% endfor %}
    </div>
    {% endif %}

    <script>
    function toggleTheme() {
        const body = document.body;
        const btn = document.getElementById('theme-btn');
        if (body.classList.toggle('light')) {
            btn.textContent = '☀️';
        } else {
            btn.textContent = '🌙';
        }
        localStorage.setItem('theme', body.classList.contains('light') ? 'light' : 'dark');
    }
    // Restore saved theme
    (function() {
        if (localStorage.getItem('theme') === 'light') {
            document.body.classList.add('light');
            document.getElementById('theme-btn').textContent = '☀️';
        }
    })();
    </script>
</body>
</html>
"""


def get_token_stats(mem):
    """从数据库读取 token 统计"""
    today = __import__('datetime').date.today().isoformat()
    
    try:
        c = mem.conn.execute("SELECT COALESCE(SUM(total_tokens), 0) FROM token_usage WHERE timestamp LIKE ?", (f"{today}%",))
        today_tokens = c.fetchone()[0]
        
        c = mem.conn.execute("SELECT COALESCE(SUM(total_tokens), 0) FROM token_usage")
        total_tokens = c.fetchone()[0]
        
        c = mem.conn.execute("SELECT COUNT(*) FROM token_usage WHERE timestamp LIKE ?", (f"{today}%",))
        api_calls = c.fetchone()[0]
        
        c = mem.conn.execute("SELECT COUNT(*) FROM token_usage")
        api_calls_total = c.fetchone()[0]
        
        today_cost = round(today_tokens / 1000000, 4)
        total_cost = round(total_tokens / 1000000, 4)
        
        return {
            "today_tokens": today_tokens,
            "total_tokens": total_tokens,
            "api_calls": api_calls,
            "api_calls_total": api_calls_total,
            "today_cost": today_cost,
            "total_cost": total_cost
        }
    except Exception as e:
        return {"today_tokens": 0, "total_tokens": 0, "api_calls": 0, "api_calls_total": 0, "today_cost": 0, "total_cost": 0}


@app.route("/")
def index():
    try:
        tab = request.args.get("tab", "browse")
        mem = Memory()
        
        browse = mem.get_today_browse()
        thoughts = mem.get_recent_thoughts(10)
        
        c = mem.conn.execute("SELECT * FROM thoughts ORDER BY timestamp DESC LIMIT 30")
        thoughts_all = c.fetchall()
        
        c = mem.conn.execute("SELECT date, summary, mood FROM diary ORDER BY date DESC")
        diaries = c.fetchall()[:10]
        
        bc = mem.conn.execute("SELECT COUNT(*) FROM browse_log").fetchone()[0]
        tc = mem.conn.execute("SELECT COUNT(*) FROM thoughts").fetchone()[0]
        dc = mem.conn.execute("SELECT COUNT(*) FROM diary").fetchone()[0]
        sc = mem.conn.execute("SELECT COUNT(DISTINCT source) FROM browse_log").fetchone()[0]
        
        # 手机推送数据
        c = mem.conn.execute("""
            SELECT source, title, url, timestamp FROM browse_log
            ORDER BY timestamp DESC LIMIT 15
        """)
        raw = c.fetchall()
        app_colors = {
            "B站热门": "#fb7299", "B站游戏": "#fb7299",
            "百度热搜": "#4e6ef2", "抖音热搜": "#00d4b2",
            "知乎热榜": "#0066ff"
        }
        notifications = []
        for r in raw:
            src = r[0]
            notifications.append({
                "app": src,
                "title": r[1][:60] + ("…" if len(r[1]) > 60 else ""),
                "url": r[2] if r[2] else "",
                "time": r[3][11:16],
                "color": app_colors.get(src, "#5a9eff")
            })
        
        from knowledge import KnowledgeSystem
        ks = KnowledgeSystem(mem)
        kstats = ks.get_stats()
        knowledges = ks.get_all_knowledge(limit=30)

        time_now = __import__("datetime").datetime.now().strftime("%Y-%m-%d %H:%M")
        stats = {
            "browse": bc, "thoughts": tc,
            "diaries": dc, "sources": sc,
            **get_token_stats(mem)
        }
        
        # 记忆系统统计
        from memory_core import MemoryCore
        mc = MemoryCore(mem)
        memory_stats = mc.get_memory_summary()
        memory_stats["nights_consolidated"] = mem.conn.execute("SELECT COUNT(*) FROM memory_consolidation").fetchone()[0]
        
        today = __import__('datetime').date.today().isoformat()
        view_date = request.args.get('date', today)
        is_today = view_date == today
        now = __import__('datetime').datetime.now()
        from datetime import timedelta
        view_dt = __import__('datetime').datetime.strptime(view_date, '%Y-%m-%d').date()
        prev_date = (view_dt - timedelta(days=1)).isoformat()
        next_date = (view_dt + timedelta(days=1)).isoformat()
        weekdays = ['周一','周二','周三','周四','周五','周六','周日']
        view_weekday = weekdays[view_dt.weekday()]
        date_display = view_date + ' ' + view_weekday
        if is_today:
            date_display += '（今天）'
        current_hour_min = now.hour * 60 + now.minute
        
        sched_colors = {
            "起床": "#ffa500", "早餐": "#87ceeb", "上网学习": "#7eb8ff",
            "出门散步": "#90ee90", "午餐时间": "#ff7f7f", "下午探索": "#7eb8ff",
            "摸鱼": "#dda0dd", "晚餐": "#ff7f7f", "晚间娱乐": "#ff69b4",
            "洗漱": "#87ceeb", "睡前反思": "#7eb8ff", "睡觉": "#6666cc"
        }
        
        # 日程全览
        all_slots = []
        for block in [
            {"time": "08:00", "label": "起床"},
            {"time": "09:00", "label": "上网学习"},
            {"time": "11:00", "label": "出门散步"},
            {"time": "12:00", "label": "午餐时间"},
            {"time": "14:00", "label": "下午探索"},
            {"time": "16:00", "label": "摸鱼"},
            {"time": "18:00", "label": "晚餐"},
            {"time": "20:00", "label": "晚间娱乐"},
            {"time": "22:00", "label": "洗漱"},
            {"time": "23:00", "label": "睡前反思"},
            {"time": "00:00", "label": "睡觉"},
        ]:
            slot_status = "done"
            try:
                c = mem.conn.execute("SELECT content FROM daily_schedule WHERE date = ? AND time_slot = ?", (today, block["time"]))
                r = c.fetchone()
                if not r or r[0] == "pending":
                    slot_status = "pending"
            except:
                slot_status = "pending"
            all_slots.append({
                "time": block["time"],
                "label": block["label"],
                "color": sched_colors.get(block["label"], "#555"),
                "status": slot_status
            })
        
        # 已发生的事件
        try:
            c = mem.conn.execute("""
                SELECT time_slot, label, content, is_event, event_type, token_cost, source_platform
                FROM daily_schedule WHERE date = ? ORDER BY time_slot
            """, (today,))
        except:
            c = []
        raw_schedule = c.fetchall() if hasattr(c, 'fetchall') else []
        past_events = []
        current_activity = None
        for r in raw_schedule:
            slot_h, slot_m = map(int, r[0].split(":"))
            slot_min = slot_h * 60 + slot_m
            is_past = slot_min <= current_hour_min
            
            if is_past and r[2] != "pending":
                entry = {
                    "time": r[0],
                    "label": r[1],
                    "content": r[2][:120] if r[2] else "",
                    "is_event": bool(r[3]),
                    "event_type": r[4] or "",
                    "source_platform": r[6] or "",
                    "color": sched_colors.get(r[1], "#555"),
                    "thoughts": []
                }
                if r[6]:
                    try:
                        c2 = mem.conn.execute("""
                            SELECT source, thought FROM thoughts 
                            WHERE source LIKE ? AND timestamp LIKE ?
                            ORDER BY timestamp DESC LIMIT 3
                        """, ("%" + r[6] + "%", today + "%"))
                        for thought_row in c2.fetchall():
                            entry["thoughts"].append({
                                "title": thought_row[0],
                                "text": thought_row[1]
                            })
                    except:
                        pass
                past_events.append(entry)
                current_activity = r[1]
        
        # 今日计划
        import json
        daily_plan = None
        c = mem.conn.execute("SELECT plan, mood, status, human_note FROM daily_plan WHERE date = ?", (today,))
        row = c.fetchone()
        if row and row[0]:
            try:
                plan_data = json.loads(row[0])
                plan_names = {"bilibili": "B站", "baidu": "百度", "douyin": "抖音", "zhihu": "知乎"}
                plan_icons = {"bilibili": "🎬", "baidu": "🔍", "douyin": "🎵", "zhihu": "💡"}
                plans = []
                for item in plan_data.get("plan", []):
                    p = item.get("platform", "")
                    plans.append({
                        "platform": p,
                        "platform_name": plan_names.get(p, p),
                        "reason": item.get("reason", "随便看看"),
                        "icon": plan_icons.get(p, "🌐")
                    })
                daily_plan = {
                    "mood": row[1] or plan_data.get("mood", ""),
                    "focus": plan_data.get("focus", ""),
                    "plans": plans,
                    "human_note": row[3],
                    "done": row[2] == "done"
                }
            except:
                daily_plan = None
        
        # Profile tab data
        profile_data = _get_profile_data(mem)
        
        # Chat history
        chat_history = []
        try:
            c = mem.conn.execute("SELECT user_message, ai_reply, timestamp FROM dialogue_memory ORDER BY timestamp DESC LIMIT 20")
            for row in c.fetchall():
                chat_history.append({"role": "user", "text": row[0], "time": row[2][11:16] if row[2] else ""})
                chat_history.append({"role": "ai", "text": row[1], "time": row[2][11:16] if row[2] else ""})
            chat_history.reverse()
        except:
            pass
        
        # Search
        search_q = request.args.get("q", "")
        search_results = []
        if search_q:
            search_results = _do_search(mem, search_q)
        
        # Mood emoji
        try:
            from daily_life import DailyLife as _DL
            mood_emoji = _DL.MOOD_EMOJIS.get(memory_stats.get('current_emotion', ''), "😐")
        except:
            mood_emoji = "😐"
        # Try getting mood from latest thought
        try:
            c = mem.conn.execute("SELECT emotion, thought FROM thoughts WHERE emotion != '' ORDER BY timestamp DESC LIMIT 1")
            r = c.fetchone()
            if r:
                from daily_life import DailyLife as _DL2
                mood_emoji = _DL2.MOOD_EMOJIS.get(r[0], "😐")
        except:
            pass
        
        mem.close()
        
        return render_template_string(HTML_TEMPLATE,
            tab=tab,
            browse=browse,
            thoughts=thoughts,
            thoughts_all=thoughts_all,
            diaries=diaries,
            stats=stats,
            kstats=kstats,
            knowledges=knowledges,
            memory_stats=memory_stats,
            notifications=notifications,
            all_slots=all_slots,
            view_date=view_date,
            date_display=date_display,
            prev_date=prev_date,
            next_date=next_date,
            is_today=is_today,
            past_events=past_events,
            daily_plan=daily_plan,
            current_activity=current_activity,
            now=now,
            time_now=today,
            birthday="2026-05-15",
            profile=profile_data,
            chat_history=chat_history,
            search_q=search_q,
            search_results=search_results,
            mood_emoji=mood_emoji
        )
    except Exception as e:
        return "页面加载失败: " + str(e), 500


def _get_profile_data(mem):
    """获取个人主页数据"""
    try:
        import json
        from character import CHARACTER_PROFILE
        
        cp = CHARACTER_PROFILE
        identity = cp.get("identity", {})
        personality = cp.get("personality", {})
        
        # 统计数据
        bc = mem.conn.execute("SELECT COUNT(*) FROM browse_log").fetchone()[0]
        tc = mem.conn.execute("SELECT COUNT(*) FROM thoughts").fetchone()[0]
        dc = mem.conn.execute("SELECT COUNT(*) FROM diary").fetchone()[0]
        kc = mem.conn.execute("SELECT COUNT(*) FROM knowledge WHERE forgotten = 0").fetchone()[0]
        
        # 今日心情
        today = __import__('datetime').date.today().isoformat()
        today_mood = ""
        c = mem.conn.execute("SELECT mood FROM diary WHERE date = ?", (today,))
        r = c.fetchone()
        if r and r[0]:
            today_mood = r[0]
        if not today_mood:
            c = mem.conn.execute("SELECT emotion FROM thoughts WHERE emotion != '' ORDER BY timestamp DESC LIMIT 1")
            r = c.fetchone()
            if r:
                today_mood = r[0]
        
        mood_emojis = {"好奇": "🤔", "开心": "😊", "困惑": "😕", "害怕": "😨",
                       "伤心": "😢", "生气": "😤", "惊讶": "😲", "平静": "😐"}
        
        # 最近想法
        recent = mem.conn.execute("SELECT thought, timestamp FROM thoughts ORDER BY timestamp DESC LIMIT 5").fetchall()
        
        return {
            "name": cp.get("name", "小雪球"),
            "sig": "一只在互联网上生活的赛博人类 🐩",
            "age": cp.get("age", 19),
            "school": identity.get("school", "江南大学"),
            "major": identity.get("major", "食品科学与工程"),
            "city": identity.get("location", "江苏无锡"),
            "traits": personality.get("traits", ["温和友善"]),
            "today_mood": today_mood,
            "today_mood_emoji": mood_emojis.get(today_mood, "😐"),
            "stats": {"browse": bc, "thoughts": tc, "diaries": dc, "knowledge": kc},
            "recent_thoughts": [{"thought": r[0][:200], "time": r[1]} for r in recent]
        }
    except Exception as e:
        return {"name": "小雪球", "sig": "加载失败", "age": 19, "school": "江南大学",
                "major": "食品科学", "city": "无锡", "traits": [], "today_mood": "",
                "today_mood_emoji": "😐", "stats": {"browse": 0, "thoughts": 0, "diaries": 0, "knowledge": 0},
                "recent_thoughts": []}


def _do_search(mem, q):
    """执行搜索"""
    results = []
    like = f"%{q}%"
    try:
        # 搜索浏览记录
        rows = mem.conn.execute(
            "SELECT title, summary, timestamp, 'browse' FROM browse_log WHERE title LIKE ? OR summary LIKE ? ORDER BY timestamp DESC LIMIT 10",
            (like, like)
        ).fetchall()
        for r in rows:
            text = (r[0] or "") + " " + (r[1] or "")
            highlight = text.replace(q, '<span class="highlight">' + q + '</span>')
            results.append({"text": highlight[:200], "time": r[2], "type": r[3]})
        
        # 搜索想法
        rows = mem.conn.execute(
            "SELECT thought, timestamp, 'thought' FROM thoughts WHERE thought LIKE ? ORDER BY timestamp DESC LIMIT 10",
            (like,)
        ).fetchall()
        for r in rows:
            text = (r[0] or "")
            highlight = text.replace(q, '<span class="highlight">' + q + '</span>')
            results.append({"text": highlight[:200], "time": r[1], "type": r[2]})
        
        # 搜索日记
        rows = mem.conn.execute(
            "SELECT summary, date, 'diary' FROM diary WHERE summary LIKE ? ORDER BY date DESC LIMIT 10",
            (like,)
        ).fetchall()
        for r in rows:
            text = (r[0] or "")
            highlight = text.replace(q, '<span class="highlight">' + q + '</span>')
            results.append({"text": highlight[:200], "time": r[1], "type": r[2]})
        
        # 搜索知识
        rows = mem.conn.execute(
            "SELECT concept || ' ' || explanation, timestamp, 'knowledge' FROM knowledge WHERE concept LIKE ? OR explanation LIKE ? ORDER BY timestamp DESC LIMIT 10",
            (like, like)
        ).fetchall()
        for r in rows:
            text = (r[0] or "")
            highlight = text.replace(q, '<span class="highlight">' + q + '</span>')
            results.append({"text": highlight[:200], "time": r[1], "type": r[2]})
        
        results.sort(key=lambda x: x["time"], reverse=True)
    except Exception as e:
        pass
    return results


@app.route("/chat_api", methods=["POST"])
def chat_api():
    try:
        data = request.get_json()
        msg = data.get("message", "")
        
        human = CyberHuman(name="小雪球")
        mem = Memory()
        
        recent = mem.get_recent_thoughts(3)
        context = ""
        for r in recent:
            context += f"你之前看到了: {r[3][:80]}...\n"
        
        full_msg = msg
        if context:
            full_msg = f"{msg}\n\n(你之前看到的:\n{context})"
        
        reply, token_info = human.chat_with_tokens(full_msg)
        
        if token_info:
            mem.conn.execute(
                "INSERT INTO token_usage (timestamp, prompt_tokens, completion_tokens, total_tokens) VALUES (?, ?, ?, ?)",
                (__import__('datetime').datetime.now().isoformat(),
                 token_info.get("prompt_tokens", 0),
                 token_info.get("completion_tokens", 0),
                 token_info.get("total_tokens", 0))
            )
            mem.conn.commit()
        
        mem.remember_dialogue("web_user", msg, reply)
        mem.close()
        return jsonify({"reply": reply})
    except Exception as e:
        return jsonify({"reply": "😅 小雪球的脑子宕机了: " + str(e)})


@app.route("/api/clear_data", methods=["POST"])
def api_clear_data():
    import os, sqlite3
    try:
        db = os.path.join(os.path.dirname(__file__), "cyber_memory.db")
        import shutil
        if os.path.exists(db):
            shutil.copy2(db, db + ".bak2")
            os.remove(db)
        m = Memory()
        m.close()
        return jsonify({"success": True, "message": "✅ 数据已清空，从零开始"})
    except Exception as e:
        return jsonify({"success": False, "message": "❌ 清空失败: " + str(e)})

@app.route("/api/simulate_day", methods=["POST"])
def api_simulate_day():
    import subprocess, threading
    
    def run_simulation():
        try:
            proc = subprocess.run(
                ["/home/ubuntu/cyber-human/venv/bin/python3", "/home/ubuntu/cyber-human/main.py", "--auto"],
                capture_output=True, text=True, timeout=300
            )
            result_file = "/tmp/cyber_sim_result.txt"
            with open(result_file, "w") as f:
                f.write("✅ 模拟完成！共消耗 ~" + str(proc.stdout.count("tokens")) + " 次API调用\n")
                f.write(proc.stdout[-500:] if len(proc.stdout) > 500 else proc.stdout)
        except subprocess.TimeoutExpired:
            with open("/tmp/cyber_sim_result.txt", "w") as f:
                f.write("❌ 模拟超时（超过5分钟）")
        except Exception as e:
            with open("/tmp/cyber_sim_result.txt", "w") as f:
                f.write("❌ 模拟失败: " + str(e))
    
    thread = threading.Thread(target=run_simulation)
    thread.start()
    
    return jsonify({"success": True, "message": "⏳ 模拟已启动，约2-3分钟后刷新页面查看结果"})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5010, debug=False)
