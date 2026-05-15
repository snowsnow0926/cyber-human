"""Fix memory.py - split multi-statement execute"""
with open('/home/ubuntu/cyber-human/memory.py') as f:
    c = f.read()

# Find the problematic multi-statement block
old = """            );
            CREATE TABLE IF NOT EXISTS daily_plan ("""

new = """            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS daily_plan ("""

c = c.replace(old, new)

with open('/home/ubuntu/cyber-human/memory.py', 'w') as f:
    f.write(c)
print("OK - split daily_schedule and daily_plan into separate executes")

# Verify
import re
matches = list(re.finditer(r"cursor\.execute", c))
print("Total cursor.execute calls: %d" % len(matches))
