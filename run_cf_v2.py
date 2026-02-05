
import subprocess
import time
import sys
import os

def run():
    print("🚀 Starting Cloudflared...")
    # Run cloudflared and capture output
    # process = subprocess.Popen(['.\\cloudflared.exe', 'tunnel', '--url', 'http://127.0.0.1:8501'], 
    #                            stdout=subprocess.PIPE, 
    #                            stderr=subprocess.STDOUT,
    #                            text=True,
    #                            encoding='utf-8',
    #                            bufsize=1)
    
    # Simple shell execution to avoid buffering issues sometimes seen with Popen in this environment
    os.system("powershell -c \".\\cloudflared.exe tunnel --url http://127.0.0.1:8501 | Select-String -Pattern 'trycloudflare.com'\"")

if __name__ == "__main__":
    run()
