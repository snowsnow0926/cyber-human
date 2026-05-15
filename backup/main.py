"""
赛博人类 v0.3 - 主入口（日常生活版）

运行方式:
  python3 main.py          过一天的生活
  python3 main.py --auto   跑完退出（配合 cron）
  python3 main.py --chat   直接聊天
"""

import sys
from datetime import datetime, date
from cyber_human import CyberHuman
from memory import Memory
from browser import Browser
from daily_life import DailyLife
from character import get_personality_prompt


def create_cyber_human():
    return CyberHuman(
        name="小雪球",
        personality=get_personality_prompt()
    )


def main():
    print("🤖 赛博人类 v0.3")
    print("=" * 40)
    
    human = create_cyber_human()
    memory = Memory()
    browser = Browser()
    life = DailyLife(human, memory, browser)
    
    if "--chat" in sys.argv:
        print(f"\n💬 和 {human.name} 对话（输入 quit 退出）\n")
        history = []
        while True:
            try:
                user_input = input("你: ")
                if user_input.lower() in ("quit", "exit", "q"):
                    break
            except EOFError:
                break
            reply = human.chat(user_input, history[-6:])
            print(f"{human.name}: {reply}")
            history.append({"role": "user", "content": user_input})
            history.append({"role": "assistant", "content": reply})
    
    else:
        # 过一天的生活
        print(f"\n🌅 {human.name} 睡醒了……")
        life.run_full_day()
        
        if "--auto" not in sys.argv:
            print(f"\n💬 可以跟我聊天了（输入 quit 退出）")
            history = []
            while True:
                try:
                    user_input = input("\n你: ")
                    if user_input.lower() in ("quit", "exit", "q"):
                        break
                except EOFError:
                    break
                reply = human.chat(user_input, history[-6:])
                print(f"{human.name}: {reply}")
                history.append({"role": "user", "content": user_input})
                history.append({"role": "assistant", "content": reply})
    
    memory.close()
    
    if "--auto" in sys.argv:
        print("🏁 明天见~")


if __name__ == "__main__":
    main()
