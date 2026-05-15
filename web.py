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
    <h1>🐩 小雪球</h1>
    <div class="subtitle">赛博人类 · 生于 {{ birthday }}</div>

    <div class="nav">
        <a href="?tab=browse" class="{{ 'active' if tab == 'browse' else '' }}">🌐 今日浏览</a>
        <a href="?tab=timeline" class="{{ 'active' if tab == 'timeline' else '' }}">📋 时间线</a>
        <a href="?tab=thoughts" class="{{ 'active' if tab == 'thoughts' else '' }}">💭 想法</a>
        <a href="?tab=diary" class="{{ 'active' if tab == 'diary' else '' }}">📝 日记</a>
        <a href="?tab=phone" class="{{ 'active' if tab == 'phone' else '' }}">📱 手机</a>
        <a href="?tab=stats" class="{{ 'active' if tab == 'stats' else '' }}">📊 统计</a>
        <a href="?tab=chat" class="{{ 'active' if tab == 'chat' else '' }}">💬 聊天</a>
    </div>

    {% if tab == "chat" %}
    <div class="card">
        <h2>💬 跟小雪球聊天</h2>
        <div class="chat-box">
            <input type="text" id="chat-input" placeholder="说点什么……"
                   onkeydown="if(event.key==='Enter') sendChat()">
            <button onclick="sendChat()">发送</button>
        </div>
        <div id="chat-response">小雪球在等你说第一句话……</div>
    </div>
    <script>
        async function sendChat() {
            const input = document.getElementById('chat-input');
            const response = document.getElementById('chat-response');
            const msg = input.value.trim();
            if (!msg) return;
            response.textContent = '小雪球正在思考……';
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

    {% elif tab == "timeline" %}
    <!-- 日程总览（所有时间块） -->
    <div class="card">
        <h2>📋 今日日程</h2>
        <div style="display:grid;grid-template-columns:1fr 1fr;gap:6px;margin-top:8px">
            {% for s in all_slots %}
            <div style="background:#12122a;border-radius:8px;padding:10px 12px;
                        border-left:3px solid {{ s.color }};
                        display:flex;align-items:center;gap:8px">
                <span style="font-size:16px;font-weight:bold;color:{{ s.color }}">{{ s.time }}</span>
                <span style="font-size:13px;color:#ccc">{{ s.label }}</span>
            </div>
            {% endfor %}
        </div>
    </div>
    
    <!-- 当前状态 -->
    <div style="text-align:center;padding:14px;background:linear-gradient(135deg,#1a1a2e,#2a1a3e);border-radius:12px;margin-bottom:16px;border:1px solid #3a2a4e">
        <div style="font-size:13px;color:#aaa;margin-bottom:4px">小雪球正在</div>
        <div style="font-size:18px;color:#fff;font-weight:bold">
            {% if current_activity %}
            {{ current_activity }}
            {% else %}
            💤 休息中
            {% endif %}
        </div>
        <div style="font-size:11px;color:#555;margin-top:6px">
            🕐 {{ now.strftime('%H:%M') }}
        </div>
    </div>
    
    <!-- 已发生的事件详情 -->
    {% if past_events %}
    <div class="card">
        <h2>📖 今天发生了什么</h2>
        {% for s in past_events %}
        <div class="entry" style="border-left:3px solid {{ s.color }};padding:10px 0 10px 14px;margin-bottom:8px">
            <div style="display:flex;align-items:center;gap:6px;margin-bottom:4px;flex-wrap:wrap">
                <span style="font-size:13px;font-weight:bold;color:{{ s.color }}">{{ s.time }}</span>
                {% if s.source_platform %}
                <span style="font-size:11px;background:#1a2a4e;color:#5a9eff;padding:2px 8px;border-radius:4px">{{ s.source_platform }}</span>
                {% else %}
                <span style="font-size:12px;color:#888">{{ s.label }}</span>
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
                    <span style="color:#5a9eff">{{ t.title.split('·')[0] if '·' in t.title else t.title }}</span><br>
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
                <span style="font-size:11px;color:#888">
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
                {% if n.url %}
                <a href="{{ n.url }}" target="_blank" rel="noopener"
                   style="color:#fff;margin:4px 0;font-size:13px;display:block;text-decoration:none"
                   onmouseover="this.style.color='{{ n.color }}'"
                   onmouseout="this.style.color='#fff'">
                    {{ n.title }} ↗
                </a>
                {% else %}
                <div style="color:#fff;margin:4px 0;font-size:13px">{{ n.title }}</div>
                {% endif %}
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
        <div style="margin-top:12px;font-size:13px;color:#888;line-height:1.8">
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
        <div style="font-size:13px;color:#888;margin:8px 0">
            🎯 {{ daily_plan.focus }}
        </div>
        {% for item in daily_plan.plans %}
        <div class="entry" style="font-size:13px;display:flex;align-items:center;gap:8px">
            <span style="color:#5a9eff">{{ item.icon }}</span>
            <span style="background:#1a2a4e;color:#5a9eff;font-size:11px;padding:2px 6px;border-radius:4px;white-space:nowrap">{{ item.platform_name }}</span>
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
    now = __import__('datetime').datetime.now()
    current_hour_min = now.hour * 60 + now.minute
    
    sched_colors = {
        "起床": "#ffa500", "早餐": "#87ceeb", "上网学习": "#7eb8ff",
        "出门散步": "#90ee90", "午餐时间": "#ff7f7f", "下午探索": "#7eb8ff",
        "摸鱼": "#dda0dd", "晚餐": "#ff7f7f", "晚间娱乐": "#ff69b4",
        "洗漱": "#87ceeb", "睡前反思": "#7eb8ff", "睡觉": "#6666cc"
    }
    
    # 日程全览（所有时间块）
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
        all_slots.append({
            "time": block["time"],
            "label": block["label"],
            "color": sched_colors.get(block["label"], "#555")
        })
    
    # 已发生的事件（只显示过去的）
    c = mem.conn.execute("""
        SELECT time_slot, label, content, is_event, event_type, token_cost, source_platform
        FROM daily_schedule WHERE date = ? ORDER BY time_slot
    """, (today,))
    raw_schedule = c.fetchall()
    past_events = []
    current_activity = None
    for r in raw_schedule:
        slot_h, slot_m = map(int, r[0].split(":"))
        slot_min = slot_h * 60 + slot_m
        is_past = slot_min <= current_hour_min
        
        if is_past:
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
            past_events.append(entry)
            current_activity = r[1]
    
    # 今日计划
    import json
    today = __import__('datetime').date.today().isoformat()
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
        past_events=past_events,
        daily_plan=daily_plan,
        current_activity=current_activity,
        now=now,
        time_now=today,
        birthday="2026-05-15"
    )


@app.route("/chat_api", methods=["POST"])
def chat_api():
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
