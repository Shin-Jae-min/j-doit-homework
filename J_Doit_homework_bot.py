
import os
import logging
import asyncio
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters
from pydub import AudioSegment
from azure_stt import AzureGrader
import tempfile

# Configure Logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    chat_id = update.effective_chat.id
    
    # Save user if not exists
    user_file = "users.txt"
    if not os.path.exists(user_file):
        with open(user_file, "w") as f: pass
        
    with open(user_file, "r+") as f:
        existing_users = f.read().splitlines()
        if str(chat_id) not in existing_users:
            f.write(f"{chat_id}\n")
    
    await update.message.reply_text(
        f"안녕하세요 {user.first_name}님! J_Doit_homework_bot입니다. 🇰🇷\n"
        f"등록되었습니다! 매일 오후 8시에 숙제가 배달됩니다.\n\n"
        "사용법:\n"
        "1. 📝 읽고 싶은 문장을 텍스트로 보내세요.\n"
        "2. 🎤 그 메시지에대고 '답장(Reply)'으로 음성 메시지를 녹음해서 보내세요.\n\n"
        "또는, 음성 메시지를 보낼 때 'Caption(설명)'에 문장을 적어서 보내셔도 됩니다.\n\n"
        "🚀 테스트: /homework 를 입력하면 즉시 예제 숙제를 받아볼 수 있습니다."
    )

async def send_homework_now(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """즉시 테스트용 숙제 발송"""
    hw_text = "안녕하세요. 만나서 반갑습니다. 오늘 날씨가 참 좋네요."
    
    # Store in context for implicit reply
    context.user_data['last_homework'] = hw_text
    
    await update.message.reply_text(f"[오늘의 숙제] 다음 문장을 읽어서 보내주세요:\n\n{hw_text}")

async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # 1. Determine Reference Text
    ref_text = None
    if update.message.caption:
        ref_text = update.message.caption
    elif update.message.reply_to_message and update.message.reply_to_message.text:
        ref_text = update.message.reply_to_message.text
    else:
        # Fallback to last homework
        ref_text = context.user_data.get('last_homework')
        if ref_text:
             await update.message.reply_text(f"💡 최근 숙제 문장으로 평가합니다.")
    
    if not ref_text:
        await update.message.reply_text(
            "⚠️ 평가할 대본을 찾을 수 없습니다.\n"
            "1. '/homework'로 숙제를 받거나\n"
            "2. 텍스트 메시지에 답장으로 녹음하거나\n"
            "3. 캡션에 텍스트를 적어주세요."
        )
        return

    status_msg = await update.message.reply_text(f"🎧 분석 중... \n문장: \"{ref_text}\"")

    # 2. Download Voice File
    try:
        voice_file = await update.message.voice.get_file()
        
        # Use temp files to avoid clutter/conflicts
        with tempfile.NamedTemporaryFile(suffix=".ogg", delete=False) as ogg_temp:
            ogg_path = ogg_temp.name
        
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as wav_temp:
            wav_path = wav_temp.name
            
        await voice_file.download_to_drive(ogg_path)
        
        # 3. Convert OGG to WAV (16kHz, Mono) using pydub
        try:
            sound = AudioSegment.from_ogg(ogg_path)
            sound = sound.set_frame_rate(16000).set_channels(1)
            sound.export(wav_path, format="wav")
            
        except Exception as e:
            logging.error(f"Conversion Error: {e}")
            await status_msg.edit_text("⚠️ 오디오 변환 실패. 서버에 ffmpeg가 설치되어 있는지 확인해주세요.")
            return
            
        # 4. Grade using Azure
        key = os.getenv("AZURE_SPEECH_KEY")
        region = os.getenv("AZURE_SPEECH_REGION")
        
        if not key or not region:
             await status_msg.edit_text("⚠️ 서버 설정 오류: Azure Key/Region이 설정되지 않았습니다.")
             return

        grader = AzureGrader(key, region)
        # Note: grade() is synchronous/blocking. In a production bot, run in loop.run_in_executor
        res = grader.grade(wav_path, ref_text)
        
        # 5. Send Result
        if res['status'] == 'success':
            s = res['scores']
            
            # Format Score Message
            score_emoji = "🏆" if s['pronunciation'] >= 90 else ("🙂" if s['pronunciation'] >= 70 else "💪")
            
            msg = (f"{score_emoji} **평가 결과**\n"
                   f"📊 종합 점수: **{s['pronunciation']:.0f}점**\n\n"
                   f"🎯 정확도: {s['accuracy']:.0f} | 🌊 유창성: {s['fluency']:.0f}\n"
                   f"🧩 완결성: {s['completeness']:.0f}\n\n"
                   f"📝 인식된 발음:\n\"{res['recognized_text']}\"")
            
            # Error Highlights
            errors = [w for w in res['word_details'] if w['error_type'] != 'None']
            if errors:
                msg += "\n\n⚠️ **피드백**:"
                for e in errors:
                    etype = e['error_type']
                    if etype == "Mispronunciation": etype = "❌ 발음"
                    elif etype == "Omission": etype = "🗑 누락"
                    elif etype == "Insertion": etype = "➕ 추임새"
                    msg += f"\n- {e['word']}: {etype}"
            
            await status_msg.edit_text(msg, parse_mode='Markdown')
            
        else:
             await status_msg.edit_text(f"😥 평가 실패: {res.get('message', 'Unknown Error')}")

    except Exception as e:
        logging.error(f"Bot Error: {e}")
        await status_msg.edit_text("⚠️ 처리 중 오류가 발생했습니다.")
        
    finally:
        # Cleanup
        if 'ogg_path' in locals() and os.path.exists(ogg_path):
            os.remove(ogg_path)
        if 'wav_path' in locals() and os.path.exists(wav_path):
            os.remove(wav_path)

if __name__ == '__main__':
    load_dotenv()
    
    token = os.getenv("TELEGRAM_TOKEN")
    if not token:
        print("❌ Error: TELEGRAM_TOKEN is missing in .env")
        exit(1)
        
    app = ApplicationBuilder().token(token).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("homework", send_homework_now))
    app.add_handler(MessageHandler(filters.VOICE, handle_voice))
    
    print("🤖 Telegram Bot Started...")
    app.run_polling()
