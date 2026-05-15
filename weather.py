"""赛博人类天气模块"""
import requests, random

class Weather:
    """获取无锡天气（小雪球在江南大学）"""
    
    def __init__(self):
        self.cache = None
        self.city = "无锡"
    
    def get_today(self):
        """获取今天天气，带缓存"""
        if self.cache:
            return self.cache
        try:
            # 使用 wttr.in - 无需API key
            resp = requests.get(
                f"https://wttr.in/{self.city}?format=%C|%t|%h|%w",
                headers={"User-Agent": "curl/8.0"},
                timeout=10
            )
            parts = resp.text.strip().split("|")
            if len(parts) >= 2:
                weather = {
                    "condition": parts[0].strip(),
                    "temp": parts[1].strip() if len(parts) > 1 else "?",
                    "humidity": parts[2].strip() if len(parts) > 2 else "?",
                    "wind": parts[3].strip() if len(parts) > 3 else "?",
                }
                self.cache = weather
                return weather
        except:
            pass
        # Fallback: random weather
        weather = random.choice(["晴天", "多云", "阴天", "小雨", "微风"])
        self.cache = {"condition": weather, "temp": "20°C", "humidity": "60%", "wind": "3级"}
        return self.cache
    
    def get_mood_modifier(self):
        """天气对心情的影响"""
        w = self.get_today()
        cond = w.get("condition", "")
        if any(x in cond for x in ["晴", "Sunny", "Clear"]):
            return 0.3  # 心情+30%
        elif any(x in cond for x in ["雨", "Rain", "阴", "Cloud"]):
            return -0.1
        return 0

if __name__ == "__main__":
    w = Weather()
    print(w.get_today())
