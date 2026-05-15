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
    <title>🐩 赛博人类 - 小蓝</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { 
            font-family: -apple-system, 'Segoe UI', sans-serif;
            background: #0f0f1a; color: #e0e0e0;
            max-width: 800px; margin: 0 auto; padding: 20px;
        }
        h1 { color: #7eb8ff; margin-bottom: 5px; font-size: 24px; }
        .subtitle { color: #888; font-size: 14px; margin-bottom: 20px; }
        .card {
            background: #1a1a2e; border-radius: 12px;
            padding: 16px; margin-bottom: 16px;
            border: 1px solid #2a2a4e;
        }
        .card h2 { color: #7eb8ff; font-size: 16px; margin-bottom: 10px; }
        .entry { 
            padding: 10px 0; border-bottom: 1px solid #2a2a4e;
        }
        .entry:last-child { border: none; }
        .source { color: #5a9eff; font-size: 12px; }
        .title { color: #fff; font-size: 14px; margin: 4px 0; }
        .thought { color: #b0b0c0; font-size: 13px; line-height: 1.5; }
        .time { color: #666; font-size: 11px; }
        .mood { color: #ffd700; }
        .chat-box { 
            display: flex; gap: 8px; margin-top: 10px;
        }
        .chat-box input {
            flex: 1; padding: 10px; border-radius: 8px;
            border: 1px solid #2a2a4e; background: #1a1a2e;
            color: #fff; font-size: 14px;
        }
        .chat-box button {
            padding: 10px 20px; border-radius: 8px;
            border: none; background: #5a9eff; color: #fff;
            font-size: 14px; cursor: pointer;
        }
        .chat-box button:hover { background: #4a8eef; }
        #chat-response {
            margin-top: 10px; padding: 12px;
            background: #12122a; border-radius: 8px;
            color: #b0b0c0; font-size: 14px; line-height: 1.6;
            min-height: 60px; white-space: pre-wrap;
        }
        .nav { display: flex; gap: 8px; margin-bottom: 16px; }
        .nav a {
            padding: 6px 14px; border-radius: 6px;
            background: #1a1a2e; color: #888; text-decoration: none;
            font-size: 13px;
        }
        .nav a.active { background: #5a9eff; color: #fff; }
        .status-dot {
            display: inline-block; width: 8px; height: 8px;
            border-radius: 50%; margin-right: 6px;
        }
        .online { background: #4ade80; }
        .empty { color: #666; font-style: italic; padding: 10px 0; }
        .stat-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; }
        .stat-item {
            background: #12122a; border-radius: 8px; padding: 12px;
            text-align: center;
        }
        .stat-num { color: #fff; font-size: 20px; font-weight: bold; }
        .stat-label { color: #888; font-size: 12px; margin-top: 4px; }
    </style>
</head>
<body>
    <h1>🐩 小蓝</h1>
    <div class="subtitle">赛博人类 · 生于 {{ birthday }}</div>

    <div class="nav">
        <a href="?tab=browse" class="{{ 'active' if tab == 'browse' else '' }}">🌐 今日浏览</a>
        <a href="?tab=thoughts" class="{{ 'active' if tab == 'thoughts' else '' }}">💭 想法</a>
        <a href="?tab=diary" class="{{ 'active' if tab == 'diary' else '' }}">📝 日记</a>
        <a href="?tab=phone" class="{{ 'active' if tab == 'phone' else '' }}">📱 手机</a>
        <a href="?tab=stats" class="{{ 'active' if tab == 'stats' else '' }}">📊 统计</a>
        <a href="?tab=chat" class="{{ 'active' if tab == 'chat' else '' }}">💬 聊天</a>
    </div>

    {% if tab == "chat" %}
    <div class="card">
        <h2>💬 跟小蓝聊天</h2>
        <div class="chat-box">
            <input type="text" id="chat-input" placeholder="说点什么……"
                   onkeydown="if(event.key==='Enter') sendChat()">
            <button onclick="sendChat()">发送</button>
        </div>
        <div id="chat-response">小蓝在等你说第一句话……</div>
    </div>
    <script>
        async function sendChat() {
            const input = document.getElementById('chat-input');
            const response = document.getElementById('chat-response');
            const msg = input.value.trim();
            if (!msg) return;
            response.textContent = '小蓝正在思考……';
            const res = await fetch('chat_api', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({message: msg})
            });
            const data = await res.json();
            response.textContent = data.reply;
            input.value = '';
        }
    </script>

    {% elif tab == "diary" %}
        {% for d in diaries %}
        <div class="card">
            <h2>📝 {{ d[0] }}</h2>
            <div class="mood">心情: {{ d[2] or '未记录' }}</div>
            <div class="thought" style="margin-top:8px">{{ d[1] }}</div>
        </div>
        {% else %}
        <div class="card"><div class="empty">还没有日记</div></div>
        {% endfor %}

    {% elif tab == "phone" %}
    <div class="card" style="max-width:380px;margin:0 auto">
        <h2 style="text-align:center">📱 小雪球的手机</h2>
        <div style="background:#000;border-radius:20px;padding:16px 12px 24px;
                    color:#fff;font-size:13px;margin-top:8px">
            <div style="text-align:center;font-size:11px;color:#555;padding:4px 0 12px">
                🔋 100% · 📶 5G · {{ time_now[:10] }}
            </div>
            {% for n in notifications %}
            <div style="background:#1c1c1e;border-radius:12px;padding:12px;margin-bottom:8px;
                        border-left:3px solid {{ n.color }}">
                <div style="color:#888;font-size:11px">{{ n.app }}</div>
                <div style="color:#fff;margin:4px 0;font-size:13px">{{ n.title }}</div>
                <div style="color:#aaa;font-size:11px">{{ n.time }}</div>
            </div>
            {% else %}
            <div style="text-align:center;padding:40px 0;color:#555">
                📱 小雪球的手机还没收到任何推送
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
        <div style="font-size:13px;color:#888;line-height:1.8">
            <div>今日消耗: <strong style="color:#fff;">{{ stats.today_tokens }}</strong> tokens</div>
            <div>总消耗: <strong style="color:#fff;">{{ stats.total_tokens }}</strong> tokens</div>
            <div>API调用次数: <strong style="color:#fff;">{{ stats.api_calls }}</strong> 次</div>
            <div style="margin-top:8px;font-size:11px;color:#555">
                按 DeepSeek V4 Flash 价格估算<br>
                今日费用: ~¥{{ stats.today_cost }}
                · 总计费用: ~¥{{ stats.total_cost }}
            </div>
        </div>
    </div>

    {% elif tab == "thoughts" %}
    <div class="card">
        <h2>💭 全部想法</h2>
        {% for t in thoughts_all %}
        <div class="entry">
            <div class="source">{{ t[2] }}</div>
            <div class="thought">{{ t[3] }}</div>
            <div class="time">{{ t[1][:16] }}</div>
        </div>
        {% else %}
        <div class="empty">还没有想法</div>
        {% endfor %}
    </div>

    {% else %}
    <!-- browse tab (default) -->
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
</body>
</html>
"""


def get_token_stats(mem):
    """从数据库读取 token 统计"""
    today = __import__('datetime').date.today().isoformat()
    
    c = mem.conn.execute("SELECT COALESCE(SUM(total_tokens), 0) FROM token_usage WHERE timestamp LIKE ?", (f"{today}%",))
    today_tokens = c.fetchone()[0]
    
    c = mem.conn.execute("SELECT COALESCE(SUM(total_tokens), 0) FROM token_usage")
    total_tokens = c.fetchone()[0]
    
    c = mem.conn.execute("SELECT COUNT(*) FROM token_usage WHERE timestamp LIKE ?", (f"{today}%",))
    api_calls = c.fetchone()[0]
    
    # DeepSeek V4 Flash ≈ ¥1/百万token
    today_cost = round(today_tokens / 1000000, 4)
    total_cost = round(total_tokens / 1000000, 4)
    
    return {
        "today_tokens": today_tokens,
        "total_tokens": total_tokens,
        "api_calls": api_calls,
        "today_cost": today_cost,
        "total_cost": total_cost
    }


@app.route("/")
def index():
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
        SELECT source, title, timestamp FROM browse_log
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
            "time": r[2][11:16],
            "color": app_colors.get(src, "#5a9eff")
        })
    
    stats = {
        "browse": bc, "thoughts": tc,
        "diaries": dc, "sources": sc,
        **get_token_stats(mem)
    }
    
    mem.close()
    
    today = __import__('datetime').date.today().isoformat()
    
    return render_template_string(HTML_TEMPLATE,
        tab=tab,
        browse=browse,
        thoughts=thoughts,
        thoughts_all=thoughts_all,
        diaries=diaries,
        stats=stats,
        notifications=notifications,
        time_now=today,
        birthday="2026-05-15"
    )


@app.route("/chat_api", methods=["POST"])
def chat_api():
    data = request.get_json()
    msg = data.get("message", "")
    
    human = CyberHuman(name="小蓝")
    mem = Memory()
    
    recent = mem.get_recent_thoughts(3)
    context = ""
    for r in recent:
        context += f"你之前看到了: {r[3][:80]}...\n"
    
    full_msg = msg
    if context:
        full_msg = f"{msg}\n\n(你之前看到的:\n{context})"
    
    reply, token_info = human.chat_with_tokens(full_msg)
    
    # 记录 token 消耗
    if token_info:
        mem.conn.execute(
            "INSERT INTO token_usage (timestamp, prompt_tokens, completion_tokens, total_tokens) VALUES (?, ?, ?, ?)",
            (__import__('datetime').datetime.now().isoformat(),
             token_info.get("prompt_tokens", 0),
             token_info.get("completion_tokens", 0),
             token_info.get("total_tokens", 0))
        )
        mem.conn.commit()
    
    mem.close()
    return jsonify({"reply": reply})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5010, debug=False)
