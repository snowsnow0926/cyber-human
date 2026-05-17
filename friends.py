#!/usr/bin/env python3
"""
朋友圈系统模块
模拟小雪球的室友/朋友朋友圈动态，支持点赞、评论
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional

from logger import get_logger
from memory import get_db

logger = get_logger(__name__)


@dataclass
class Friend:
    name: str
    avatar: str
    mood: str


# 小雪球的预设好友列表
DEFAULT_FRIENDS = [
    Friend(name="小雨", avatar="&#x1F338;", mood="开心"),
    Friend(name="阿泽", avatar="&#x1F43E;", mood="犯困"),
    Friend(name="小美", avatar="&#x1F9D1;&#x200D;&#x1F3A8;", mood="期待"),
    Friend(name="班长林哥", avatar="&#x1F9D4;&#x200D;&#x2642;&#xFE0F;", mood="忙碌"),
    Friend(name="室友阿月", avatar="&#x1F970;", mood="悠闲"),
]


@dataclass
class Moment:
    id: Optional[int] = None
    friend_name: str = ""
    content: str = ""
    timestamp: str = ""
    likes: int = 0
    liked_by_xiaoqiu: bool = False


class FriendsSystem:
    """朋友圈系统：管理好友列表和动态"""

    def __init__(self, db=None) -> None:
        self.db = db or get_db()
        self.friends = DEFAULT_FRIENDS
        logger.info("FriendsSystem initialized")
        self._seed_initial_moments()

    def _ensure_tables(self) -> None:
        """确保朋友圈相关表存在。"""
        try:
            with self.db.get_conn() as conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS friend_moments (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        friend_name TEXT,
                        content TEXT,
                        timestamp TEXT,
                        likes INTEGER DEFAULT 0,
                        liked_by_xiaoqiu INTEGER DEFAULT 0
                    )
                """)
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS friend_comments (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        moment_id INTEGER,
                        commenter TEXT,
                        content TEXT,
                        timestamp TEXT
                    )
                """)
                conn.execute("CREATE INDEX IF NOT EXISTS idx_moments_friend ON friend_moments(friend_name)")
        except Exception as e:
            logger.error(f"Failed to create friends tables: {e}")

    def _seed_initial_moments(self) -> None:
        """首次启动时自动生成历史朋友圈动态，确保 UI 不空。"""
        self._ensure_tables()
        try:
            with self.db.get_cursor() as cursor:
                count = cursor.execute("SELECT COUNT(*) FROM friend_moments").fetchone()[0]
            if count > 0:
                return
        except Exception:
            return

        from datetime import timedelta
        now = datetime.now()
        seed_templates = [
            ("小雨", "今天在图书馆泡了一下午，看到一本超好看的推理小说！"),
            ("阿泽", "博美犬今天又拆家了！！我已经麻了......"),
            ("小美", "新买的眼影盘到了，这个颜色绝了！"),
            ("室友阿月", "食堂的红烧狮子头居然只要5块钱，太良心了"),
            ("班长林哥", "期末复习周真的好累，但一定要撑住！"),
            ("小雨", "在楼下发现一只超可爱的小橘猫，求收养~"),
            ("阿泽", "今天打了三个小时游戏，罪恶感满满"),
            ("小美", "烘焙课做的曲奇成功了！配方分享给大家"),
            ("室友阿月", "终于周末了！打算睡到自然醒"),
            ("班长林哥", "社团活动策划案终于写完了，累死"),
        ]

        for i, (friend_name, content) in enumerate(seed_templates):
            ts = (now - timedelta(days=i // 2 + 1, hours=i * 2)).strftime("%Y-%m-%dT%H:%M:%S")
            likes = random.randint(0, 12)
            try:
                with self.db.get_conn() as conn:
                    conn.execute(
                        """INSERT INTO friend_moments
                           (friend_name, content, timestamp, likes, liked_by_xiaoqiu)
                           VALUES (?, ?, ?, ?, 0)""",
                        (friend_name, content, ts, likes),
                    )
            except Exception as e:
                logger.debug(f"Seed moment failed: {e}")

        logger.info(f"Seeded {len(seed_templates)} initial friend moments")

    def generate_daily_moments(self, count: int = 3, sim_date: str = "") -> list[Moment]:
        """
        生成当日的随机朋友圈动态（供每日模拟调用）。
        返回生成的数量。
        """
        self._ensure_tables()
        date_str = sim_date or datetime.now().strftime("%Y-%m-%d")
        ts_prefix = f"{date_str}T{random.randint(10, 22):02d}:{random.randint(0, 59):02d}"

        templates = [
            "{friend}分享了一首歌：🎵 《{song}》",
            "{friend}晒了一张图，配文：今天{activity}，超开心的~",
            "{friend}说：{feeling}，有没有人懂啊！",
            "{friend}：刚发现一家超棒的{place}，下次一定要去！",
            "{friend}转发了一条动态，配上文字：笑死",
            "{friend}发了一条：今天天气{weather}，心情也跟着{weather}了~",
            "{friend}：终于完成了{achievement}，感动哭了呜呜呜",
            "{friend}晒出美食：今日份{meal}，自己做的，好有成就感！",
            "{friend}更新了状态：在{app}上看到了有趣的东西哈哈哈",
            "{friend}：好累啊但是好充实！今天{event}",
        ]

        activities = ["吃了顿好的", "逛街", "自习", "打游戏", "拍照", "追剧", "喝奶茶"]
        feelings = ["好开心", "太难了", "无语了", "绝绝子", "emo了", "太甜了", "超解压"]
        places = ["咖啡店", "书店", "甜品店", "奶茶店", "公园", "小众景点"]
        weathers = ["晴朗", "下雨", "凉爽", "闷热", "温暖"]
        achievements = ["论文初稿", "期末复习", "项目答辩", "社团任务", "社团策划"]
        meals = ["早餐", "午餐", "下午茶", "晚餐", "夜宵"]
        apps = ["小红书", "B站", "微博", "抖音", "豆瓣"]
        events = ["上课差点迟到", "抢到了想吃的饭", "室友送了小零食", "超市大采购", "意外收到了快递"]

        generated = []
        for i in range(count):
            tpl = random.choice(templates)
            friend = random.choice(self.friends)
            content = tpl.format(
                friend=friend.name,
                song=random.choice(["起风了", "合适", "晚安", "爱你", "晴天"]),
                activity=random.choice(activities),
                feeling=random.choice(feelings),
                place=random.choice(places),
                weather=random.choice(weathers),
                achievement=random.choice(achievements),
                meal=random.choice(meals),
                app=random.choice(apps),
                event=random.choice(events),
            )
            ts = f"{ts_prefix}:{random.randint(10, 59):02d}.000"
            likes_count = random.randint(0, 15)

            try:
                with self.db.get_conn() as conn:
                    cursor = conn.execute(
                        """INSERT INTO friend_moments
                           (friend_name, content, timestamp, likes, liked_by_xiaoqiu)
                           VALUES (?, ?, ?, ?, 0)""",
                        (friend.name, content, ts, likes_count),
                    )
                    moment_id = cursor.lastrowid
                    generated.append(Moment(
                        id=int(moment_id) if moment_id else None,
                        friend_name=friend.name,
                        content=content,
                        timestamp=ts,
                        likes=likes_count,
                        liked_by_xiaoqiu=False,
                    ))
            except Exception as e:
                logger.warning(f"Failed to save moment: {e}")

        logger.info(f"Generated {len(generated)} friend moments for {date_str}")
        return generated

    def get_all_moments(self, limit: int = 30) -> list[dict[str, Any]]:
        """获取所有朋友圈动态（供 Web UI 调用）。"""
        self._ensure_tables()
        try:
            with self.db.get_cursor() as cursor:
                cursor.execute(
                    """SELECT id, friend_name, content, timestamp, likes, liked_by_xiaoqiu
                       FROM friend_moments
                       ORDER BY timestamp DESC
                       LIMIT ?""",
                    (limit,),
                )
                rows = cursor.fetchall()
                return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Failed to get moments: {e}")
            return []

    def get_recent_moments(self, friend_name: str, limit: int = 5) -> list[dict[str, Any]]:
        """获取某好友最近的动态。"""
        self._ensure_tables()
        try:
            with self.db.get_cursor() as cursor:
                cursor.execute(
                    """SELECT id, friend_name, content, timestamp, likes, liked_by_xiaoqiu
                       FROM friend_moments
                       WHERE friend_name = ?
                       ORDER BY timestamp DESC
                       LIMIT ?""",
                    (friend_name, limit),
                )
                rows = cursor.fetchall()
                return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Failed to get moments for {friend_name}: {e}")
            return []

    def toggle_like(self, moment_id: int) -> bool:
        """切换小雪球对某条动态的点赞状态。"""
        self._ensure_tables()
        try:
            with self.db.get_conn() as conn:
                row = conn.execute(
                    "SELECT liked_by_xiaoqiu FROM friend_moments WHERE id = ?",
                    (moment_id,),
                ).fetchone()
                if not row:
                    return False
                new_state = 0 if row[0] else 1
                conn.execute(
                    "UPDATE friend_moments SET liked_by_xiaoqiu = ? WHERE id = ?",
                    (new_state, moment_id),
                )
                conn.execute(
                    "UPDATE friend_moments SET likes = likes + ? WHERE id = ?",
                    (1 if new_state else -1, moment_id),
                )
                logger.debug(f"Toggle like on moment {moment_id}: liked={bool(new_state)}")
                return bool(new_state)
        except Exception as e:
            logger.error(f"Failed to toggle like: {e}")
            return False

    def add_comment(self, moment_id: int, comment: str, commenter: str = "小雪球") -> bool:
        """小雪球对某条动态发表评论。"""
        self._ensure_tables()
        try:
            with self.db.get_conn() as conn:
                conn.execute(
                    """INSERT INTO friend_comments
                       (moment_id, commenter, content, timestamp)
                       VALUES (?, ?, ?, ?)""",
                    (moment_id, commenter, comment, datetime.now().isoformat()),
                )
                logger.debug(f"Added comment on moment {moment_id}: {comment[:30]}")
                return True
        except Exception as e:
            logger.error(f"Failed to add comment: {e}")
            return False

    def get_comments(self, moment_id: int) -> list[dict[str, Any]]:
        """获取某条动态的所有评论。"""
        self._ensure_tables()
        try:
            with self.db.get_cursor() as cursor:
                cursor.execute(
                    """SELECT id, moment_id, commenter, content, timestamp
                       FROM friend_comments
                       WHERE moment_id = ?
                       ORDER BY timestamp ASC""",
                    (moment_id,),
                )
                rows = cursor.fetchall()
                return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Failed to get comments: {e}")
            return []

    def ai_like_and_comment(self, moments: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """AI 自动对小雪球可能感兴趣的朋友圈动态点赞和评论。"""
        if not moments:
            return []

        ai = None
        try:
            from cyber_human import get_ai
            ai = get_ai()
        except Exception:
            return []

        interested_keywords = ["美食", "烘焙", "甜品", "游戏", "可爱", "奶茶",
                              "咖啡", "蛋糕", "穿搭", "美妆", "周末", "放松"]
        results = []

        for moment in moments:
            content = moment.get("content", "")
            if any(kw in content for kw in interested_keywords):
                liked = self.toggle_like(moment["id"])

                prompt = (
                    f"你是「小雪球」，看到室友/朋友发了这样一条朋友圈：\n"
                    f"「{content}」\n\n"
                    f"请用她的口吻写一条简短的评论（10-30字），可以点赞、调侃、羡慕或表达共鸣。"
                    f"例如：「绝了绝了！」「哈哈哈太真实了」「好羡慕啊啊啊！」"
                    f"只输出评论文字，不要其他内容。"
                )
                try:
                    resp = ai._call_llm(prompt, system=None)
                    comment = resp.content.strip()
                    if comment:
                        self.add_comment(moment["id"], comment)
                        results.append({
                            "moment_id": moment["id"],
                            "liked": liked,
                            "comment": comment,
                            "tokens": getattr(resp, "total_tokens", 0),
                        })
                    # 记录 token 消耗
                    tokens = getattr(resp, "total_tokens", 0)
                    if tokens > 0:
                        try:
                            from datetime import datetime as _dt
                            with self.db.get_conn() as conn:
                                conn.execute(
                                    "INSERT INTO token_usage (timestamp, prompt_tokens, completion_tokens, total_tokens) VALUES (?, 0, 0, ?)",
                                    (_dt.now().isoformat(), tokens),
                                )
                        except Exception:
                            pass
                except Exception as e:
                    logger.warning(f"AI comment failed: {e}")

        return results


# 单例
_friends_system: Optional[FriendsSystem] = None


def get_friends_system() -> FriendsSystem:
    global _friends_system
    if _friends_system is None:
        _friends_system = FriendsSystem()
    return _friends_system
