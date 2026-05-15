"""
和赛博人类聊一句话。
用法: python3 chat_once.py "你的话"
"""

import sys
from cyber_human import CyberHuman
from memory import Memory

def chat_once(message: str):
    human = CyberHuman(name="小雪球")
    memory = Memory()
    
    recent = memory.get_recent_thoughts(5)
    context = ""
    for r in recent:
        context += f"你之前看到了: {r[3][:80]}...\n"
    
    if context:
        msg = f"{message}\n\n(你之前看到的:\n{context})"
    else:
        msg = message
    
    reply = human.chat(msg)
    memory.close()
    return reply

if __name__ == "__main__":
    if len(sys.argv) > 1:
        msg = " ".join(sys.argv[1:])
        print(chat_once(msg))
    else:
        print("用法: python3 chat_once.py '你想说的话'")
