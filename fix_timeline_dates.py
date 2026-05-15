"""Add date navigation to timeline tab"""
with open('/home/ubuntu/cyber-human/web.py') as f:
    c = f.read()

# Step 1: Accept date param from URL
old = "today = __import__('datetime').date.today().isoformat()\n    now = __import__('datetime').datetime.now()"
new = """today = __import__('datetime').date.today().isoformat()
    view_date = request.args.get("date", today)
    is_today = view_date == today
    now = __import__('datetime').datetime.now()
    
    # Calculate prev/next dates
    from datetime import timedelta
    view_dt = __import__('datetime').datetime.strptime(view_date, "%Y-%m-%d").date()
    prev_date = (view_dt - timedelta(days=1)).isoformat()
    next_date = (view_dt + timedelta(days=1)).isoformat()
    # Date in Chinese
    weekdays = ["周一","周二","周三","周四","周五","周六","周日"]
    view_weekday = weekdays[view_dt.weekday()]
    date_display = view_date + " " + view_weekday
    if is_today:
        date_display += "（今天）"""

c = c.replace(old, new)

# Step 2: Change timeline queries to use view_date instead of today
old = """    c = mem.conn.execute("""
        SELECT time_slot, label, content, is_event, event_type, token_cost, source_platform
        FROM daily_schedule WHERE date = ? ORDER BY time_slot
    """, (today,))"""
new = """    c = mem.conn.execute("""
        SELECT time_slot, label, content, is_event, event_type, token_cost, source_platform
        FROM daily_schedule WHERE date = ? ORDER BY time_slot
    """, (view_date,))"""

c = c.replace(old, new)

# Step 3: Add date display to the timeline header
old = """    {% elif tab == "timeline" %}
    <!-- 日程总览（所有时间块） -->
    <div class="card">
        <h2>📋 今日日程</h2>"""

new = """    {% elif tab == "timeline" %}
    <!-- 日期导航 -->
    <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:12px;padding:10px 14px;background:#1a1a2e;border-radius:12px;border:1px solid #2a2a4e">
        <a href="?tab=timeline&date={{ prev_date }}" style="color:#888;text-decoration:none;font-size:20px">‹</a>
        <div style="text-align:center">
            <div style="font-size:15px;color:#fff;font-weight:bold">{{ date_display }}</div>
            <form style="margin-top:6px;display:flex;gap:6px" method="GET" action="/cyber-human/">
                <input type="hidden" name="tab" value="timeline">
                <input type="date" name="date" value="{{ view_date }}" style="background:#222;color:#fff;border:1px solid #444;border-radius:6px;padding:4px 8px;font-size:12px">
                <button type="submit" style="background:#444;color:#fff;border:none;border-radius:6px;padding:4px 10px;font-size:12px;cursor:pointer">跳转</button>
            </form>
        </div>
        <a href="?tab=timeline&date={{ next_date }}" style="color:#888;text-decoration:none;font-size:20px">›</a>
    </div>
    
    {% elif tab == "timeline" %}
    <!-- 日程总览（所有时间块） -->
    <div class="card">
        <h2>📋 日程</h2>"""

c = c.replace(old, new)

# Step 4: Add view_date, date_display, prev_date, next_date, is_today to template kwargs
old = """        past_events=past_events,"""
new = """        view_date=view_date,
        date_display=date_display,
        prev_date=prev_date,
        next_date=next_date,
        is_today=is_today,
        past_events=past_events,"""

c = c.replace(old, new)

# Step 5: Fix current_activity - only show for today
old = """    <div style="text-align:center;padding:14px;background:linear-gradient(135deg,#1a1a2e,#2a1a3e);border-radius:12px;margin-bottom:16px;border:1px solid #3a2a4e">
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
    </div>"""

new = """    {% if is_today %}
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
    {% endif %}"""

c = c.replace(old, new)

with open('/home/ubuntu/cyber-human/web.py', 'w') as f:
    f.write(c)

print("Done")
