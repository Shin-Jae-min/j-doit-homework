
import re

try:
    with open('cf.log', 'r', encoding='utf-8') as f:
        content = f.read()
except UnicodeDecodeError:
    with open('cf.log', 'r', encoding='utf-16') as f:
        content = f.read()
except Exception:
    with open('cf.log', 'r', errors='ignore') as f:
        content = f.read()

matches = re.findall(r'https://[a-zA-Z0-9-]+\.trycloudflare\.com', content)
if matches:
    print("FOUND_URL: " + matches[0])
else:
    print("NO_URL_FOUND")
    # print snippet
    print(content[:500])
