"""赛博人类节假日模块"""
from datetime import date, timedelta

class Holiday:
    """识别节假日和纪念日"""
    
    # 简单节假日表（公历）
    FIXED = {
        (1, 1): "元旦",
        (2, 14): "情人节",
        (3, 8): "妇女节",
        (3, 12): "植树节",
        (4, 1): "愚人节",
        (5, 1): "劳动节",
        (5, 4): "青年节",
        (6, 1): "儿童节",
        (7, 1): "建党节",
        (8, 1): "建军节",
        (9, 10): "教师节",
        (10, 1): "国庆节",
        (10, 31): "万圣节",
        (12, 24): "平安夜",
        (12, 25): "圣诞节",
        (12, 31): "跨年夜",
    }
    
    def __init__(self, birth="2026-05-15"):
        """birth: 小雪球的"生日"（出生日期）"""
        self.birth = date.fromisoformat(birth) if isinstance(birth, str) else birth
    
    def get_today_events(self, dt=None):
        """获取今天是什么日子"""
        if dt is None:
            dt = date.today()
        elif isinstance(dt, str):
            dt = date.fromisoformat(dt)
        
        events = []
        
        # 固定节日
        key = (dt.month, dt.day)
        if key in self.FIXED:
            events.append({"type": "holiday", "name": self.FIXED[key]})
        
        # 周末
        if dt.weekday() >= 5:
            events.append({"type": "weekend", "name": "周末"})
        
        # 生日
        if dt.month == self.birth.month and dt.day == self.birth.day:
            age = dt.year - self.birth.year
            events.append({"type": "birthday", "name": f"小雪球{age}岁生日"})
        
        # 季节
        if (dt.month == 3 and dt.day >= 20) or (4 <= dt.month <= 5):
            events.append({"type": "season", "name": "春天"})
        elif (6 <= dt.month <= 8):
            events.append({"type": "season", "name": "夏天"})
        elif (9 <= dt.month <= 11):
            events.append({"type": "season", "name": "秋天"})
        else:
            events.append({"type": "season", "name": "冬天"})
        
        return events

if __name__ == "__main__":
    h = Holiday()
    print(h.get_today_events())
