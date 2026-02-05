
from pyngrok import ngrok
import time

# Open a HTTP tunnel on the default port 8501
public_url = ngrok.connect(8501).public_url

print("🚀 Ngrok Tunnel Started!")
print(f"🔗 Public URL: {public_url}")
print("이제 모바일에서 위 주소로 접속하세요! (HTTPS 지원)")
print("Tunne is active. Press Ctrl+C to stop.")

# Keep the script running
try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    print("Stopping tunnel...")
    ngrok.kill()
