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
    
    def think_about(self, content: str) -> tuple:
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": "我刚刚看到了这个内容，说说你的想法：\n\n--- 内容 ---\n" + content[:3000] + "\n--- 内容结束 ---\n\n看完这个，你有什么想说的？用第一人称表达。\n最后用一行 [IMPORTANCE:X] 评价这件事对你的影响程度（1=没什么感觉，5=印象深刻）"}
        ]
        
        reply = self.client.chat.completions.create(
            model="deepseek-v4-flash",
            messages=messages,
            temperature=0.8,
            max_tokens=500
        )
        
        text = reply.choices[0].message.content
        
        importance = 3
        if "[IMPORTANCE:" in text:
            try:
                parts = text.split("[IMPORTANCE:")
                text = parts[0].strip()
                imp_str = parts[1].split("]")[0]
                importance = max(1, min(5, int(imp_str)))
            except:
                pass
        
        return text, importance

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

    def chat_with_tokens(self, user_input: str) -> tuple:
        """
        聊天并返回 token 消耗信息。
        返回: (回复文本, {prompt_tokens, completion_tokens, total_tokens})
        """
        messages = [{"role": "system", "content": self.system_prompt}]
        messages.append({"role": "user", "content": user_input})
        
        reply = self.client.chat.completions.create(
            model="deepseek-v4-flash",
            messages=messages,
            temperature=0.9,
            max_tokens=800
        )
        
        usage = reply.usage
        if usage:
            token_info = {
                "prompt_tokens": usage.prompt_tokens or 0,
                "completion_tokens": usage.completion_tokens or 0,
                "total_tokens": usage.total_tokens or 0
            }
        else:
            token_info = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
        
        return reply.choices[0].message.content, token_info
