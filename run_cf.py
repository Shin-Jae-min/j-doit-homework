
import subprocess
import time
import re
import sys

def run_cloudflared():
    print("🚀 Starting Cloudflare Tunnel...")
    # Using the 'trycloudflare' quick tunnel which requires no auth
    # We use the 'cloudflared' command which pycloudflared should have installed or made available, 
    # but sometimes it's just a wrapper. Let's try running the module directly or checking usage.
    # Actually pycloudflared just provides the binary.
    
    from pycloudflared import try_cloudflare
    
    print("🔗 Requesting tunnel URL...")
    tunnel_url = try_cloudflare(port=8501)
    
    print(f"✅ Tunnel Active!")
    print(f"🌍 Public URL: {tunnel_url}")
    print("--------------------------------------------------")
    print("👉 위 URL을 모바일(Safari/Chrome)에서 열어주세요!")
    print("   (마이크 권한 100% 지원되는 공식 HTTPS입니다)")
    print("--------------------------------------------------")
    
    # Keep alive
    while True:
        time.sleep(1)

if __name__ == "__main__":
    try:
        run_cloudflared()
    except KeyboardInterrupt:
        print("Stopping...")
    except Exception as e:
        print(f"Error: {e}")
