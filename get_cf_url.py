
import re
import time
import os

log_file = 'cf_new.log'

def clean_ansi(text):
    ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
    return ansi_escape.sub('', text)

print("Searching for URL in log...")
found = False
for i in range(10): # Try for 10 seconds
    if not os.path.exists(log_file):
        time.sleep(1)
        continue
        
    try:
        with open(log_file, 'r', encoding='utf-8') as f:
            content = f.read()
    except:
        time.sleep(1)
        continue

    content = clean_ansi(content)
    # Regex to capture the URL. The URL is usually like https://<subdomain>.trycloudflare.com
    # Make sure to strictly capture the domain.
    match = re.search(r'(https://[a-zA-Z0-9-]+\.trycloudflare\.com)', content)
    
    if match:
        url = match.group(1)
        print(f"\nSUCCESS! URL Found: {url}")
        print("--------------------------------------------------")
        print("Open this URL in your mobile browser:")
        print(f"👉 {url}")
        print("--------------------------------------------------")
        found = True
        break
    else:
        time.sleep(1)

if not found:
    print("URL not found yet. Dumping last 500 chars of log:")
    print(content[-500:] if 'content' in locals() else "No log content")
