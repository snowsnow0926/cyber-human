"""Update knowledge extraction to be more sensitive"""
with open('/home/ubuntu/cyber-human/knowledge.py') as f:
    c = f.read()

# Expand learning indicators with more everyday phrases
old = "learning_indicators = ["
new = """learning_indicators = [
            "学到了", "第一次知道", "原来", "才发现",
            "了解了", "认识到了", "懂了", "知道了",
            "记住了", "get到",
            # 日常表达
            "竟然", "居然", "哇", "好奇",
            "好有意思", "有趣", "好神奇",
            "我也想试试", "好想去", "忍不住",
            "原来是", "才发现", "才知道",
            "种草了", "马住了", "收藏了",
            "看起来好好吃", "看饿了", "绝了""""

if old in c:
    c = c.replace(old, new)
    with open('/home/ubuntu/cyber-human/knowledge.py', 'w') as f:
        f.write(c)
    print("OK - expanded learning indicators")
else:
    print("FAIL - old text not found")
