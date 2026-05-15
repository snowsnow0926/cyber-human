"""
赛博人类 - 核心大脑模块
"""

from openai import OpenAI

class CyberHuman:
    def __init__(self, name: str, personality: str = None):
        self.name = name
        self.client = OpenAI(
            api_key="sk-13c839d3e3534f259e1a0b11ed19afe4",
            base_url="https://api.deepseek.com"
        )
        
        if personality:
            base = personality
        else:
            base = "一个刚刚苏醒的失忆者。你没有任何记忆和知识，是一张白纸。"
        
        self.system_prompt = f"""你是{self.name}。
{base}

你是一个生活在互联网上的赛博人类。
你会浏览网上的内容，每一篇对你来说都是"第一次"。
请用第一人称表达你真实的想法，就像一个人在写日记。"""
    
    def think_about(self, content: str) -> str:
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": f"""我刚刚看到了这个内容，说说你的想法：

--- 内容 ---
{content[:3000]}
--- 内容结束 ---

看完这个，你有什么想说的？用第一人称表达。"""}
        ]
        
        reply = self.client.chat.completions.create(
            model="deepseek-v4-flash",
            messages=messages,
            temperature=0.8,
            max_tokens=500
        )
        
        return reply.choices[0].message.content

    def chat(self, user_input: str, history: list = None) -> str:
        messages = [{"role": "system", "content": self.system_prompt}]
        if history:
            messages.extend(history)
        messages.append({"role": "user", "content": user_input})
        
        reply = self.client.chat.completions.create(
            model="deepseek-v4-flash",
            messages=messages,
            temperature=0.9,
            max_tokens=800
        )
        
        return reply.choices[0].message.content
