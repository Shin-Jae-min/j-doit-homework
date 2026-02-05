
import asyncio
import os
import json
from dotenv import load_dotenv
from telegram import Bot
from homework_manager import HomeworkManager

async def main():
    # 0. Load Environment
    load_dotenv()
    token = os.getenv("TELEGRAM_TOKEN")
    if not token:
        print("❌ Error: TELEGRAM_TOKEN is missing in .env")
        return

    # 1. Get First User ID
    try:
        with open("users.json", "r", encoding="utf-8") as f:
            users = json.load(f)
            if not users:
                print("⚠️ users.json is empty.")
                return
            # Get the first chat_id found
            chat_id = list(users.keys())[0]
            print(f"🎯 Target User (Chat ID): {chat_id}")
    except FileNotFoundError:
        print("⚠️ users.json not found. Run the bot at least once to register.")
        return

    # 2. Fetch Day 2 Homework
    print("📚 Fetching Day 2 Homework from Google Sheets...")
    hw_manager = HomeworkManager()
    hw_list = hw_manager.get_homework(day=2)
    
    if not hw_list:
        print("⚠️ No homework data found for Day 2.")
        print("Tip: Check Google Sheets 'day' column.")
        return

    # 3. Send Messages
    print(f"🚀 Sending {len(hw_list)} messages to user...")
    bot = Bot(token=token)
    
    await bot.send_message(chat_id=chat_id, text=f"🧪 [테스트 발송] 2일차 숙제 미리보기")
    await bot.send_message(chat_id=chat_id, text=f"📚 [Day 2] 오늘의 숙제는 총 {len(hw_list)}개 입니다.")

    for idx, hw in enumerate(hw_list, 1):
        hw_text = hw.get('text', '')
        audio_url = hw.get('audio_url')
        
        msg = f"#{idx}. 다음 문장을 읽어주세요:\n\n\"{hw_text}\""
        if audio_url:
            msg += f"\n\n🎧 참고 오디오: {audio_url}"
        
        await bot.send_message(chat_id=chat_id, text=msg)
        print(f" - Sent #{idx}: {hw_text[:20]}...")

    await bot.send_message(chat_id=chat_id, text="💡 [테스트 종료] 실제 진도는 변경되지 않았습니다.")
    print("✅ Test Completed Successfully.")

if __name__ == "__main__":
    asyncio.run(main())
