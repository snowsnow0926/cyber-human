#!/usr/bin/env python3
"""
Web 服务模块 v2.0
Flask + Flask-SocketIO，极简路由 + 投喂功能
"""

from __future__ import annotations

import os
from datetime import datetime, date
from functools import wraps
from threading import Thread
from typing import Any, Callable, Optional

import flask_socketio as _fso
import inspect as _ins
_sfp = _ins.getsourcefile(_fso)
_patch_marker = _sfp + ".session_patch_done"
import os as _os
if not _os.path.exists(_patch_marker):
    try:
        with open(_sfp, encoding="utf-8") as _f:
            _sl = _f.readlines()
        _mod = False
        for _i, _l in enumerate(_sl):
            if "ctx.session = session_obj" in _l:
                if not _l.strip().startswith("#"):
                    _sl[_i] = "                # ctx.session is read-only in Flask 3.1+\n"
                    _mod = True
                    break
        if _mod:
            with open(_sfp, "w", encoding="utf-8") as _f:
                _f.writelines(_sl)
            with open(_patch_marker, "w") as _f:
                _f.write("1")
    except Exception:
        pass

from flask import Flask, jsonify, render_template, request
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


@app.route("/api/today")
@make_response
def api_today() -> Any:
    """今天所有想法 + 浏览记录"""
    from memory import get_db
    db = get_db()
    thoughts = db.get_today_thoughts()
    browses = db.get_today_browses()
    return jsonify({
        "date": date.today().isoformat(),
        "thoughts": thoughts,
        "browses": browses,
    })


@app.route("/api/thoughts")
@make_response
def api_all_thoughts() -> Any:
    """全部想法，支持 tag 筛选"""
    from memory import get_db
    db = get_db()
    tag = request.args.get("tag", "").strip()
    try:
        limit = int(request.args.get("limit", "100"))
    except (ValueError, TypeError):
        limit = 100

    if tag:
        items = db.get_thoughts_by_tag(tag, limit)
    else:
        items = db.get_all_thoughts(limit)
    return jsonify({"data": items, "total": len(items)})


@app.route("/api/status")
@make_response
def api_status() -> Any:
    """模拟状态"""
    from memory import get_db
    db = get_db()
    stats = db.get_stats()
    return jsonify({
        "running": False,
        "date": date.today().isoformat(),
        "stats": stats,
    })


@app.route("/api/control/simulate", methods=["POST"])
@make_response
def api_simulate() -> Any:
    """触发一次完整模拟"""
    from daily_life import get_engine
    data = request.get_json(silent=True) or {}
    sim_date = data.get("date", "").strip()

    def run_sim():
        try:
            engine = get_engine()
            results = engine.run_full_day(sim_date)
            socketio.emit("sim_complete", {
                "slots": len(results),
                "date": sim_date or date.today().isoformat()
            }, room="web")
        except Exception as e:
            logger.error(f"Simulate day error: {e}")
            socketio.emit("sim_error", {"error": str(e)}, room="web")

    Thread(target=run_sim, daemon=True).start()
    return jsonify({"status": "started", "date": sim_date or "today"})


@app.route("/api/control/clear", methods=["POST"])
@make_response
def api_clear() -> Any:
    """清空今日数据"""
    from memory import get_db
    db = get_db()
    results = db.clear_today_data()
    return jsonify({"success": True, "cleared": results})


@app.route("/api/timeline")
@make_response
def api_timeline() -> Any:
    """时间线视图数据"""
    from memory import get_db
    db = get_db()
    req_date = request.args.get("date", "").strip()
    target_date = req_date or date.today().isoformat()

    schedule = db.get_schedule_by_date(target_date)
    thoughts = db.get_thoughts_by_date(target_date)
    browses = db.get_browses_by_date(target_date)

    if not schedule and not thoughts and not browses and req_date:
        try:
            with db.get_cursor() as cursor:
                rows = cursor.execute("""
                    SELECT date FROM (
                        SELECT DISTINCT substr(timestamp, 1, 10) as date FROM thoughts
                        UNION
                        SELECT date FROM daily_schedule
                    ) ORDER BY date DESC LIMIT 1
                """).fetchall()
                if rows:
                    target_date = rows[0][0]
                    schedule = db.get_schedule_by_date(target_date)
                    thoughts = db.get_thoughts_by_date(target_date)
                    browses = db.get_browses_by_date(target_date)
        except Exception:
            pass

    slot_order = ["08:00", "09:00", "11:00", "12:00", "14:00", "16:00", "18:00", "20:00", "22:00", "23:00", "00:00"]

    def assign_slot(ts: str) -> str:
        h = ts[11:13] if len(ts) >= 13 else ""
        if not h.isdigit():
            return "00:00"
        hour = int(h)
        if hour == 0:
            return "00:00"
        best = "00:00"
        for s in slot_order[:-1]:
            if int(s[:2]) <= hour:
                best = s
        return best

    slot_map: dict[str, dict[str, Any]] = {}
    for s in schedule:
        ts = s.get("time_slot", "00:00")
        slot_map[ts] = {
            "time_slot": ts,
            "label": s.get("label", ""),
            "activity_type": s.get("activity_type", ""),
            "content": s.get("content", ""),
            "is_event": s.get("is_event", 0),
            "token_cost": s.get("token_cost", 0),
            "browses": [],
            "thoughts": [],
        }

    for b in browses:
        ts = b.get("timestamp", "")
        assigned = assign_slot(ts)
        if assigned not in slot_map:
            slot_map[assigned] = {
                "time_slot": assigned, "label": "", "activity_type": "browse",
                "content": "", "is_event": 0, "token_cost": 0, "browses": [], "thoughts": [],
            }
        slot_map[assigned]["browses"].append(b)

    for t in thoughts:
        ts = t.get("timestamp", "")
        assigned = assign_slot(ts)
        if assigned not in slot_map:
            slot_map[assigned] = {
                "time_slot": assigned, "label": "", "activity_type": "",
                "content": "", "is_event": 0, "token_cost": 0, "browses": [], "thoughts": [],
            }
        slot_map[assigned]["thoughts"].append(t)

    groups = []
    for s in slot_order:
        if s in slot_map:
            groups.append(slot_map[s])
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


@app.route("/api/stats")
@make_response
def api_stats() -> Any:
    """统计数据"""
    from memory import get_db
    db = get_db()
    return jsonify(db.get_stats())


# ── 日记 ────────────────────────────────────────────────────────────────────

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
    from cyber_human import get_ai
    from memory import get_db, DiaryEntry
    from datetime import datetime

    db = get_db()
    ai = get_ai()
    today = datetime.now().strftime("%Y-%m-%d")
    thoughts = db.get_today_thoughts()
    browses = db.get_today_browses()
    context = f"今天共浏览了 {len(browses)} 条内容，产生了 {len(thoughts)} 条想法。"
    prompt = f"""你是「小雪球」，今日情绪平静。

今日发生的事：
{context}

请根据以上信息写今日日记。要求：自然真实，200-300字，情感丰富。
"""
    try:
        response = ai._call_llm(prompt, system=None)
        diary_text = response.content
        db.add_diary(DiaryEntry(date=today, summary=diary_text, mood="平静"))
        socketio.emit("diary_update", {"date": today, "summary": diary_text}, room="web")
        return jsonify({"success": True, "diary": diary_text})
    except Exception as e:
        logger.error(f"Write diary failed: {e}")
        return jsonify({"error": str(e)}), 500


# ── 情绪（简化版）──────────────────────────────────────────────────────────

@app.route("/api/emotion")
@make_response
def api_emotion() -> Any:
    return jsonify({
        "current": {"state": "平静", "emoji": "&#x1F610;"},
        "history_count": 0,
        "time_slot": "afternoon",
    })


# ── 聊天 ────────────────────────────────────────────────────────────────────

@app.route("/api/chat", methods=["POST"])
@make_response
def api_chat() -> Any:
    from cyber_human import get_ai
    ai = get_ai()
    data = request.get_json(silent=True) or {}
    user_input = data.get("message", "")
    history = data.get("history", [])
    if not user_input:
        return jsonify({"error": "empty message"}), 400
    try:
        reply = ai.chat(user_input, history)
        return jsonify({"reply": reply})
    except Exception as e:
        logger.error(f"Chat error: {e}")
        return jsonify({"error": str(e)}), 500


# ── 投喂功能 ───────────────────────────────────────────────────────────────

@app.route("/api/feed", methods=["POST"])
@make_response
def api_feed() -> Any:
    """
    用户投喂信息给 AI。
    请求体: { "content": "...", "keywords": ["美食", "烘焙"] }
    """
    from cyber_human import get_ai
    from memory import FeedRecord

    data = request.get_json(silent=True) or {}
    content = data.get("content", "").strip()
    keywords = data.get("keywords", [])

    if not content:
        return jsonify({"error": "内容不能为空"}), 400

    if len(content) > 5000:
        return jsonify({"error": "内容过长，请控制在5000字以内"}), 400

    try:
        ai = get_ai()
        thought, importance, tags = ai.analyze_feed(content, keywords)
        feed_record = FeedRecord(
            timestamp=datetime.now().isoformat(),
            user_content=content[:500],
            ai_thought=thought,
            tags=tags,
            emotion="好奇",
            importance=importance,
        )
        from memory import get_db
        db = get_db()
        db.add_feed(feed_record)
        socketio.emit("thought_update", {
            "thought": thought,
            "tags": tags,
            "importance": importance,
            "source": "投喂",
        }, room="web")
        return jsonify({
            "success": True,
            "thought": thought,
            "tags": tags,
            "importance": importance,
        })
    except Exception as e:
        logger.error(f"Feed analysis failed: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/feed/history")
@make_response
def api_feed_history() -> Any:
    """获取投喂历史"""
    from memory import get_db
    db = get_db()
    try:
        limit = int(request.args.get("limit", "50"))
    except (ValueError, TypeError):
        limit = 50
    feeds = db.get_all_feeds(limit)
    return jsonify({"data": feeds, "total": len(feeds)})


# ── WebSocket ───────────────────────────────────────────────────────────────

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
    socketio.run(
        app,
        allow_unsafe_werkzeug=True,
        host=config.FLASK_HOST,
        port=config.FLASK_PORT,
        debug=config.FLASK_DEBUG,
    )


if __name__ == "__main__":
    run()
