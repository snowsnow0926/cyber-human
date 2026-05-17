#!/usr/bin/env python3
"""
Web 服务模块
Flask + Flask-SocketIO，提供 8 个标签页的 Web UI
"""

from __future__ import annotations

import json
import os
import random
import time
from datetime import date, datetime
from functools import wraps
from threading import Thread
from typing import Any, Callable, Optional

# 修复 Flask-SocketIO 与 Flask 3.1+ 的兼容性问题（ctx.session 只读）
# 仅在首次启动时修补一次，且有完整性保护
import flask_socketio as _fso
import inspect as _ins
_sfp = _ins.getsourcefile(_fso)
_patched_marker = _sfp + ".session_patch_done"
import os as _os
if not _os.path.exists(_patched_marker):
    try:
        with open(_sfp, encoding="utf-8") as _f:
            _sl = _f.readlines()
        _modified = False
        for _i, _l in enumerate(_sl):
            if "ctx.session = session_obj" in _l:
                if _l.strip().startswith("#"):
                    break
                _sl[_i] = "                # ctx.session is read-only in Flask 3.1+\n"
                _modified = True
                break
        if _modified:
            with open(_sfp, "w", encoding="utf-8") as _f:
                _f.writelines(_sl)
            with open(_patched_marker, "w") as _f:
                _f.write("1")
    except Exception:
        pass

from flask import (
    Flask,
    jsonify,
    render_template,
    request,
    send_from_directory,
)
from flask_cors import CORS
from flask_socketio import SocketIO, emit, join_room, leave_room

import config
from logger import get_logger

logger = get_logger(__name__)

app = Flask(__name__, static_folder="static", template_folder="templates")
app.config["SECRET_KEY"] = os.getenv(
    "FLASK_SECRET_KEY",
    "cyber-human-default-secret-change-in-production"
)
_cors_origins = os.getenv("CORS_ORIGINS", "http://localhost:5010,http://127.0.0.1:5010").split(",")
CORS(app, origins=_cors_origins)
socketio = SocketIO(
    app,
    cors_allowed_origins="*",
    async_mode="threading",
    ping_timeout=60,
    ping_interval=25,
)


def make_response(fn: Callable) -> Callable:
    @wraps(fn)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        try:
            return fn(*args, **kwargs)
        except Exception as e:
            logger.error(f"API error in {fn.__name__}: {e}", exc_info=True)
            return jsonify({"error": str(e), "code": 500}), 500
    return wrapper


# ── 路由 ────────────────────────────────────────────────────────────────────

@app.route("/")
@make_response
def index() -> Any:
    return render_template("index.html")


@app.route("/api/today/browses")
@make_response
def api_today_browses() -> Any:
    from memory import get_db
    db = get_db()
    items = db.get_today_browses()
    # 去重 + 空摘要补标题
    seen = set()
    deduped = []
    for i in items:
        t = i.get("title", "")
        if t not in seen:
            seen.add(t)
            if not i.get("summary", "").strip():
                i["summary"] = t[:60]
            deduped.append(i)
    return jsonify({"data": deduped, "total": len(deduped)})


@app.route("/api/today/thoughts")
@make_response
def api_today_thoughts() -> Any:
    from memory import get_db
    db = get_db()
    items = db.get_today_thoughts()
    return jsonify({"data": items, "total": len(items)})


@app.route("/api/timeline")
@make_response
def api_timeline() -> Any:
    from memory import get_db
    db = get_db()
    req_date = request.args.get("date", "").strip()
    target_date = req_date

    # Fallback: if no data exists for the requested date, use the most recent date with data
    if req_date:
        schedule = db.get_schedule_by_date(req_date)
        thoughts = db.get_thoughts_by_date(req_date)
        browses = db.get_browses_by_date(req_date)
        if not schedule and not thoughts and not browses:
            # No data for this date — find the most recent date that has data
            try:
                with db.get_cursor() as cursor:
                    rows = cursor.execute("""
                        SELECT date FROM (
                            SELECT date FROM daily_schedule
                            UNION
                            SELECT DISTINCT substr(timestamp, 1, 10) as date FROM browse_log
                            UNION
                            SELECT DISTINCT substr(timestamp, 1, 10) as date FROM thoughts
                        ) ORDER BY date DESC LIMIT 1
                    """).fetchall()
                    if rows:
                        target_date = rows[0][0]
                        schedule = db.get_schedule_by_date(target_date)
                        thoughts = db.get_thoughts_by_date(target_date)
                        browses = db.get_browses_by_date(target_date)
            except Exception as e:
                logger.warning(f"Timeline fallback failed: {e}")
    else:
        schedule = db.get_today_schedule()
        thoughts = db.get_today_thoughts()
        browses = db.get_today_browses()

    # 按 time_slot 分组
    slot_map: dict[str, dict[str, Any]] = {}
    for s in schedule:
        ts = s.get("time_slot", "00:00")
        slot_map[ts] = {
            "time_slot": ts,
            "label": s.get("label", ""),
            "activity_type": s.get("activity_type", ""),
            "content": s.get("content", ""),
            "is_event": s.get("is_event", 0),
            "event_type": s.get("event_type", ""),
            "token_cost": s.get("token_cost", 0),
            "browses": [],
            "thoughts": [],
        }

    # 排序时间槽（小时数值升序）；注意 "00:00"（午夜）排在最后以便正确处理跨天情况
    browse_slot_order = ["08:00", "09:00", "11:00", "12:00", "14:00", "16:00", "18:00", "20:00", "22:00", "23:00", "00:00"]

    def _assign_slot(h: str) -> str:
        """将小时字符串分配到最近的时间槽。小时 00 属于 00:00 槽。
        使用整数比较避免字符串字典序陷阱。"""
        hour = int(h) if h.isdigit() else -1
        if hour < 0:
            return "00:00"
        if hour == 0:
            return "00:00"
        # 找最接近且不超过的小时槽
        best = "00:00"
        for bs in browse_slot_order[:-1]:  # 跳过末尾的 "00:00"
            slot_hour = int(bs[:2])
            if slot_hour <= hour:
                best = bs
        return best

    for b in browses:
        ts = b.get("timestamp", "")
        h = ts[11:13] if len(ts) >= 13 else ""
        assigned = _assign_slot(h)
        if assigned not in slot_map:
            slot_map[assigned] = {
                "time_slot": assigned,
                "label": "",
                "activity_type": "browse",
                "content": "",
                "is_event": 0,
                "event_type": "",
                "token_cost": 0,
                "browses": [],
                "thoughts": [],
            }
        slot_map[assigned]["browses"].append(b)

    # 将想法分配到对应的时间槽
    for t in thoughts:
        ts = t.get("timestamp", "")
        h = ts[11:13] if len(ts) >= 13 else ""
        assigned = _assign_slot(h)
        if assigned not in slot_map:
            slot_map[assigned] = {
                "time_slot": assigned,
                "label": "",
                "activity_type": "",
                "content": "",
                "is_event": 0,
                "event_type": "",
                "token_cost": 0,
                "browses": [],
                "thoughts": [],
            }
        slot_map[assigned]["thoughts"].append(t)

    # 按 time_slot 排序输出
    groups = []
    for bs in browse_slot_order:
        if bs in slot_map:
            groups.append(slot_map[bs])
    # 添加不在排序列表中的
    for ts, g in sorted(slot_map.items()):
        if g not in groups:
            groups.append(g)

    return jsonify({
        "groups": groups,
        "schedule": schedule,
        "thoughts": thoughts,
        "browses": browses,
        "shown_date": target_date,
    })


@app.route("/api/thoughts")
@make_response
def api_all_thoughts() -> Any:
    from memory import get_db
    db = get_db()
    try:
        limit = int(request.args.get("limit", "100"))
    except (ValueError, TypeError):
        limit = 100
    items = db.get_all_thoughts(limit)
    return jsonify({"data": items, "total": len(items)})


@app.route("/api/diary")
@make_response
def api_diary() -> Any:
    from memory import get_db
    db = get_db()
    items = db.get_all_diary()
    return jsonify({"data": items, "total": len(items)})


@app.route("/api/diary/today", methods=["POST"])
@make_response
def api_write_diary() -> Any:
    from memory import get_db
    from emotion import get_emotion_system
    from cyber_human import get_ai
    db = get_db()
    emotion = get_emotion_system()
    ai = get_ai()
    today = datetime.now().strftime("%Y-%m-%d")
    thoughts = db.get_today_thoughts()
    browses = db.get_today_browses()
    context = f"今天共浏览了 {len(browses)} 条内容，产生了 {len(thoughts)} 条想法。"
    prompt = f"""你是「小雪球」，{emotion.get_prompt_context()}。
请根据以下信息写今日日记：{context}
要求：自然真实，200-300字，情感丰富。"""
    try:
        response = ai._call_llm(prompt, system=None)
        diary_text = response.content
        from memory import DiaryEntry
        db.add_diary(DiaryEntry(date=today, summary=diary_text, mood=emotion.current.state.value))
        socketio.emit("diary_update", {"date": today, "summary": diary_text}, room="web")
        return jsonify({"success": True, "diary": diary_text})
    except Exception as e:
        logger.error(f"Write diary failed: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/stats")
@make_response
def api_stats() -> Any:
    from memory import get_db
    from emotion import get_emotion_system
    db = get_db()
    emotion = get_emotion_system()
    stats = db.get_stats()
    emotion_data = emotion.to_dict()
    knowledge_stats = db.get_knowledge_stats()
    return jsonify({
        **stats,
        "emotion": emotion_data,
        "knowledge": knowledge_stats,
    })


@app.route("/api/knowledge")
@make_response
def api_knowledge() -> Any:
    from memory import get_db
    db = get_db()
    items = db.get_all_knowledge()
    return jsonify({"data": items, "total": len(items)})


@app.route("/api/notifications")
@make_response
def api_notifications() -> Any:
    """手机通知栏数据"""
    from memory import get_db
    db = get_db()
    try:
        brows = db.get_today_browses()
    except Exception:
        brows = []
    app_colors = {
        "B站热门": "#fb7299", "B站游戏": "#fb7299",
        "百度热搜": "#4e6ef2", "抖音热搜": "#00d4b2",
        "知乎热榜": "#0066ff"
    }
    notifications = []
    for b in brows:
        src = b.get("source", "未知")
        title = b.get("title", "")[:60]
        if len(b.get("title", "")) > 60:
            title += "..."
        ts = b.get("timestamp", "")
        notifications.append({
            "app": src,
            "title": title,
            "url": b.get("url", ""),
            "time": ts[11:16] if len(ts) >= 16 else "",
            "color": app_colors.get(src, "#5a9eff")
        })
    return jsonify({"data": notifications, "total": len(notifications)})


@app.route("/api/profile")
@make_response
def api_profile() -> Any:
    """个人主页数据"""
    from memory import get_db
    from character import get_profile
    from emotion import get_emotion_system
    db = get_db()
    cp = get_profile()
    emotion = get_emotion_system()

    try:
        bc = len(db.get_today_browses())
        tc = len(db.get_today_thoughts())
        dc = len(db.get_all_diary())
        kc = len(db.get_all_knowledge())
        kc_count = kc
    except Exception:
        bc = tc = dc = kc_count = 0

    try:
        stats_data = db.get_stats()
        kstats = db.get_knowledge_stats()
    except Exception:
        stats_data = {}
        kstats = {}

    try:
        # 最近想法
        recent = db.get_all_thoughts(limit=5)
        recent_thoughts = [{"thought": t.get("thought","")[:200], "time": t.get("timestamp","")} for t in recent]
    except Exception:
        recent_thoughts = []

    mood = emotion.current.state.value if emotion.current else "\u5e73\u9759"
    # emoji computed right below

    emojis = {"\u597d\u5947": "\U0001f914", "\u5f00\u5fc3": "\U0001f60a", "\u56f0\u60d1": "\U0001f615",
              "\u5bb3\u6015": "\U0001f628", "\u4f24\u5fc3": "\U0001f622", "\u751f\u6c14": "\U0001f624",
              "\u60ca\u8bb6": "\U0001f632", "\u5e73\u9759": "\U0001f610"}
    mood_emoji = emojis.get(mood, "\U0001f610")

    identity = cp.to_dict() if hasattr(cp, 'to_dict') else {}
    traits = cp.personality_traits if hasattr(cp, 'personality_traits') else []

    return jsonify({
        "name": getattr(cp, 'name', '\u5c0f\u96ea\u7403'),
        "sig": "\u4e00\u53ea\u5728\u4e92\u8054\u7f51\u4e0a\u751f\u6d3b\u7684\u8d5b\u535a\u4eba\u7c7b \U0001f429",
        "age": getattr(cp, 'age', 19),
        "school": getattr(cp, 'school', '\u6c5f\u5357\u5927\u5b66'),
        "major": getattr(cp, 'major', '\u98df\u54c1\u79d1\u5b66\u4e0e\u5de5\u7a0b'),
        "city": getattr(cp, 'location', '\u6c5f\u82cf\u65e0\u9521'),
        "traits": traits,
        "today_mood": mood,
        "today_mood_emoji": mood_emoji,
        "stats": {"browse": bc, "thoughts": tc, "diaries": dc, "knowledge": kc_count,
                  "total_tokens": stats_data.get("total_tokens", 0),
                  "total_cost": stats_data.get("total_tokens", 0) * 0.000001},
        "recent_thoughts": recent_thoughts,
    })


@app.route("/api/search")
@make_response
def api_search() -> Any:
    """搜索浏览记录、想法、日记、知识"""
    from memory import get_db
    db = get_db()
    q = request.args.get("q", "").strip()
    if not q:
        return jsonify({"data": [], "total": 0})

    results = []
    like = f"%{q}%"

    try:
        # 搜索浏览记录
        with db.get_cursor() as cursor:
            rows = cursor.execute(
                "SELECT title, timestamp FROM browse_log WHERE title LIKE ? OR summary LIKE ? ORDER BY timestamp DESC LIMIT 10",
                (like, like)
            ).fetchall()
            for r in rows:
                text = r[0] or ""
                results.append({"text": text[:200], "time": r[1] or "", "type": "browse"})

            # 搜索想法
            rows = cursor.execute(
                "SELECT thought, timestamp FROM thoughts WHERE thought LIKE ? ORDER BY timestamp DESC LIMIT 10",
                (like,)
            ).fetchall()
            for r in rows:
                text = r[0] or ""
                results.append({"text": text[:200], "time": r[1] or "", "type": "thought"})

            # 搜索日记
            rows = cursor.execute(
                "SELECT summary, date FROM diary WHERE summary LIKE ? ORDER BY date DESC LIMIT 10",
                (like,)
            ).fetchall()
            for r in rows:
                text = r[0] or ""
                results.append({"text": text[:200], "time": r[1] or "", "type": "diary"})

            # 搜索知识
            rows = cursor.execute(
                "SELECT concept || ' ' || explanation, timestamp FROM knowledge WHERE concept LIKE ? OR explanation LIKE ? ORDER BY timestamp DESC LIMIT 10",
                (like, like)
            ).fetchall()
            for r in rows:
                text = r[0] or ""
                results.append({"text": text[:200], "time": r[1] or "", "type": "knowledge"})

        results.sort(key=lambda x: x["time"], reverse=True)
    except Exception as e:
        logger.warning(f"Search failed: {e}")

    return jsonify({"data": results, "total": len(results), "query": q})

@app.route("/api/chat", methods=["POST"])
@make_response
def api_chat() -> Any:
    from cyber_human import get_ai
    ai = get_ai()
    data = request.get_json() or {}
    user_input = data.get("message", "")
    history = data.get("history", [])
    if not user_input:
        return jsonify({"error": "empty message"}), 400
    try:
        reply = ai.chat(user_input, history)
        socketio.emit("chat_reply", {"reply": reply, "user": user_input}, room="web")
        return jsonify({"reply": reply})
    except Exception as e:
        logger.error(f"Chat error: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/emotion")
@make_response
def api_emotion() -> Any:
    from emotion import get_emotion_system
    emotion = get_emotion_system()
    return jsonify(emotion.to_dict())


@app.route("/api/emotion/event", methods=["POST"])
@make_response
def api_emotion_event() -> Any:
    from emotion import get_emotion_system
    emotion = get_emotion_system()
    data = request.get_json() or {}
    event = data.get("event", "")
    if event:
        emotion.apply_event(event)
        socketio.emit("emotion_update", emotion.to_dict(), room="web")
    return jsonify(emotion.to_dict())


@app.route("/api/moments")
@make_response
def api_moments() -> Any:
    """获取朋友圈动态列表"""
    from friends import get_friends_system
    fs = get_friends_system()
    try:
        limit = int(request.args.get("limit", "30"))
    except (ValueError, TypeError):
        limit = 30
    return jsonify({"data": fs.get_all_moments(limit), "total": 0})


@app.route("/api/moments/<int:moment_id>/like", methods=["POST"])
@make_response
def api_moment_like(moment_id: int) -> Any:
    """切换小雪球对动态的点赞状态"""
    from friends import get_friends_system
    fs = get_friends_system()
    liked = fs.toggle_like(moment_id)
    return jsonify({"success": True, "liked": liked})


@app.route("/api/moments/<int:moment_id>/comments")
@make_response
def api_moment_comments(moment_id: int) -> Any:
    """获取动态的评论列表"""
    from friends import get_friends_system
    fs = get_friends_system()
    return jsonify({"data": fs.get_comments(moment_id)})


@app.route("/api/moments/<int:moment_id>/comment", methods=["POST"])
@make_response
def api_moment_comment(moment_id: int) -> Any:
    """小雪球发表评论"""
    from friends import get_friends_system
    fs = get_friends_system()
    data = request.get_json() or {}
    content = data.get("content", "").strip()
    if not content:
        return jsonify({"error": "empty comment"}), 400
    fs.add_comment(moment_id, content)
    return jsonify({"success": True})


@app.route("/api/moments/generate", methods=["POST"])
@make_response
def api_generate_moments() -> Any:
    """手动生成朋友圈动态（供控制面板调用）"""
    from friends import get_friends_system
    fs = get_friends_system()
    moments = fs.generate_daily_moments(count=3)
    return jsonify({"success": True, "count": len(moments)})


@app.route("/api/control/clear_browses", methods=["POST"])
@make_response
def api_clear_browses() -> Any:
    from memory import get_db
    from datetime import date
    db = get_db()
    today = date.today().isoformat()
    try:
        with db.get_cursor() as cursor:
            cursor.execute(
                "DELETE FROM browse_log WHERE timestamp LIKE ?",
                (f"{today}%",),
            )
            affected = cursor.rowcount
        logger.info(f"Cleared {affected} browse records for today")
        return jsonify({"success": True, "cleared": affected})
    except Exception as e:
        logger.error(f"Failed to clear browses: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/control/clear_data", methods=["POST"])
@make_response
def api_clear_data() -> Any:
    """清空所有数据"""
    from memory import get_db
    db = get_db()
    results = {}
    try:
        with db.get_cursor() as cursor:
            cursor.execute("DELETE FROM browse_log")
            results["browses"] = cursor.rowcount
            cursor.execute("DELETE FROM thoughts")
            results["thoughts"] = cursor.rowcount
            cursor.execute("DELETE FROM diary")
            results["diaries"] = cursor.rowcount
            cursor.execute("DELETE FROM knowledge")
            results["knowledge"] = cursor.rowcount
            cursor.execute("DELETE FROM token_usage")
            results["tokens"] = cursor.rowcount
            cursor.execute("DELETE FROM daily_schedule")
            results["schedule"] = cursor.rowcount
            cursor.execute("DELETE FROM memory_consolidation")
            results["consolidation"] = cursor.rowcount
            cursor.execute("DELETE FROM emotions")
            results["emotions"] = cursor.rowcount
        logger.info(f"Cleared all data: {results}")
        return jsonify({"success": True, "cleared": results})
    except Exception as e:
        logger.error(f"Failed to clear all data: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/status")
@make_response
def api_status() -> Any:
    """系统状态：天气、节假日、健康信息"""
    weather_info = {}
    holiday_info = {}
    health_info = {}
    try:
        from weather import get_weather
        weather_info = get_weather()
    except Exception as e:
        weather_info = {"error": str(e)}
    try:
        from holiday import get_holiday_info
        holiday_info = get_holiday_info()
    except Exception as e:
        holiday_info = {"error": str(e)}
    try:
        from health_check import get_health_status
        health_info = get_health_status()
    except Exception as e:
        health_info = {"error": str(e)}
    return jsonify({
        "weather": weather_info,
        "holiday": holiday_info,
        "health": health_info,
    })


@app.route("/api/control/simulate_day", methods=["POST"])
@make_response
def api_simulate_day() -> Any:
    from daily_life import get_engine
    data = request.get_json(silent=True) or {}
    sim_date = data.get("date", "").strip()
    def run_sim():
        try:
            engine = get_engine()
            results = engine.run_full_day(sim_date)
            socketio.emit("sim_complete", {"slots": len(results), "date": sim_date}, room="web")
        except Exception as e:
            logger.error(f"Simulate day error: {e}")
            socketio.emit("sim_error", {"error": str(e)}, room="web")
    Thread(target=run_sim, daemon=True).start()
    return jsonify({"status": "started", "date": sim_date or "today"})


# ── WebSocket 事件 ──────────────────────────────────────────────────────────

@socketio.on("connect")
def on_connect() -> None:
    logger.info(f"Web client connected: {request.sid}")
    join_room("web")
    emit("connected", {"sid": request.sid})


@socketio.on("disconnect")
def on_disconnect() -> None:
    logger.info(f"Web client disconnected: {request.sid}")
    leave_room("web")


@socketio.on("subscribe")
def on_subscribe(data: dict[str, Any]) -> None:
    room = data.get("room", "web")
    join_room(room)
    emit("subscribed", {"room": room})


# ── 主入口 ────────────────────────────────────────────────────────────────────

def run() -> None:
    logger.info(f"Starting web server on {config.FLASK_HOST}:{config.FLASK_PORT}")
    socketio.run(app, allow_unsafe_werkzeug=True, host=config.FLASK_HOST, port=config.FLASK_PORT, debug=config.FLASK_DEBUG)


if __name__ == "__main__":
    run()
