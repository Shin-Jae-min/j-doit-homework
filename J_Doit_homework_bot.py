
import os
import logging
import asyncio
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters
from pydub import AudioSegment
from azure_stt import AzureGrader
from homework_manager import HomeworkManager
from user_manager import UserManager
import tempfile
import difflib
import pytz
import datetime

# KST Timezone
KST = pytz.timezone('Asia/Seoul')

# Configure Logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    chat_id = update.effective_chat.id
    
    # Register user via UserManager
    user_manager = UserManager()
    is_new = user_manager.register_user(chat_id)
    
    msg = f"안녕하세요 {user.first_name}님! J_Doit_homework_bot입니다. 🇰🇷\n"
    if is_new:
        msg += f"등록되었습니다! 오늘부터 1일차 숙제가 시작됩니다.\n\n"
    else:
        progress = user_manager.get_user_progress(chat_id)
        day = progress.get('current_day', 1)
        msg += f"돌아오셨군요! 현재 진도는 {day}일차 입니다.\n\n"

    msg += ("사용법:\n"
            "1. 🚀 /homework 를 입력하면 오늘의 숙제가 도착합니다.\n"
            "2. 🎤 도착한 문장을 읽고 음성 메시지를 보내주세요.\n"
            "   (답장하지 않고 그냥 보내셔도 됩니다.)")
            
    await update.message.reply_text(msg)

async def send_homework_now(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """현재 진도에 맞는 숙제 발송 및 진도 업데이트"""
    chat_id = update.effective_chat.id
    
    try:
        user_manager = UserManager()
        hw_manager = HomeworkManager()
        
        # Get user progress
        progress = user_manager.get_user_progress(chat_id)
        current_day = progress.get("current_day", 1)
        
        # Fetch homework for current day (returns a LIST now)
        hw_list = hw_manager.get_homework(day=current_day)
        
        if hw_list:
            # Store ALL candidate texts for implicit reply matching
            candidates = [entry['text'] for entry in hw_list if entry.get('text')]
            context.user_data['homework_candidates'] = candidates
            
            # Reset single last_homework (optional, but good for clarity)
            context.user_data['last_homework'] = None 
            
            await update.message.reply_text(f"📚 [Day {current_day}] 오늘의 숙제는 총 {len(hw_list)}개 입니다.")
            
            # Iterate and send each homework
            for idx, hw in enumerate(hw_list, 1):
                hw_text = hw.get('text', '')
                audio_url = hw.get('audio_url')
                
                msg = f"#{idx}. 다음 문장을 읽어주세요:\n\n\"{hw_text}\""
                if audio_url:
                    msg += f"\n\n🎧 참고 오디오: {audio_url}"
                
                await update.message.reply_text(msg)
            
            await update.message.reply_text("💡 팁: 위 문장 중 아무거나 골라서 읽어주시면, 자동으로 찾아서 채점해드립니다!")
            
            # Advance progress AFTER sending (assuming checking sent is enough)
            user_manager.advance_user_day(chat_id)
            
        else:
            # No homework found -> Course Completed
            await update.message.reply_text("🎉 축하합니다! 모든 과정을 수료하셨습니다! 더 이상 숙제가 없습니다.")
            
    except Exception as e:
        await update.message.reply_text(f"⚠️ 숙제 로딩 중 오류 발생: {str(e)}")
        logging.error(f"Homework Fetch Error: {e}")

async def run_daily_homework(context: ContextTypes.DEFAULT_TYPE):
    """매일 정해진 시간에 모든 유저에게 숙제 발송"""
    logging.info("Running daily homework job...")
    
    user_manager = UserManager()
    hw_manager = HomeworkManager()
    
    # Load all users (assuming we can iterate them, otherwise we need get_all_users() in user_manager)
    # Since user_manager.users is a dict loaded from json, we can access it directly or add a method.
    # Let's verify accessing .users directly is safe if instance is fresh.
    # UserManager loads on init.
    
    all_users = user_manager.users
    
    for chat_id_str, user_data in all_users.items():
        chat_id = int(chat_id_str)
        current_day = user_data.get("current_day", 1)
        
        try:
            hw_list = hw_manager.get_homework(day=current_day)
            
            if hw_list:
                # We can't update context.user_data for all users easily in a job unless we use job context or application.user_data?
                # Actually, context.user_data is available if we passed a specific user's context, but here we are in a global job.
                # However, application.persistence or user_data is accessible if persistance is set up.
                # Without persistence, context.user_data might be volatile or tricky to access by key.
                # BUT, we can just send the message. The fallback logic in handle_voice might fail if it relies ONLY on context.user_data.
                # CRITICAL: We need a way to store candidates for implicit reply.
                # 'context.application.user_data[chat_id]' is the standard way.
                
                # Fetch user_data for this user
                user_context_data = context.application.user_data[chat_id]
                
                candidates = [entry['text'] for entry in hw_list if entry.get('text')]
                user_context_data['homework_candidates'] = candidates
                user_context_data['last_homework'] = None
                
                await context.bot.send_message(chat_id=chat_id, text=f"🔔 [알림] 오늘의 숙제가 도착했습니다! (Day {current_day})")
                await context.bot.send_message(chat_id=chat_id, text=f"📚 총 {len(hw_list)}개의 문장이 준비되었습니다.")

                for idx, hw in enumerate(hw_list, 1):
                    hw_text = hw.get('text', '')
                    audio_url = hw.get('audio_url')
                    
                    msg = f"#{idx}. 다음 문장을 읽어주세요:\n\n\"{hw_text}\""
                    if audio_url:
                        msg += f"\n\n🎧 참고 오디오: {audio_url}"
                    
                    await context.bot.send_message(chat_id=chat_id, text=msg)
                
                await context.bot.send_message(chat_id=chat_id, text="💡 아무 문장이나 읽어서 음성 메시지로 보내주세요!")
                
                # Advance day
                user_manager.advance_user_day(chat_id)
                logging.info(f"Sent homework to {chat_id} (Day {current_day})")
            
            else:
                # No homework means done? Silent or notify? Let's stay silent to avoid spam, or verify intent.
                # User asked for "모든 과정을 수료하셨습니다" on exception, maybe send once?
                # For now, let's just log.
                logging.info(f"No homework for {chat_id} (Day {current_day})")
                
        except Exception as e:
            logging.error(f"Failed to send daily homework to {chat_id}: {e}")

async def test_scheduler_job(context: ContextTypes.DEFAULT_TYPE):
    """봇 실행 직후 작동 확인을 위한 1회성 테스트 Job"""
    logging.info("🧪 Testing Scheduler...")
    # Send a message to the first user found or log
    user_manager = UserManager()
    if user_manager.users:
        first_user = list(user_manager.users.keys())[0]
        await context.bot.send_message(chat_id=first_user, text="✅ [System] 봇이 재실행되었습니다. 스케줄러가 정상 작동 중입니다.")

async def set_day(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """(테스트용) 강제로 진도(Day)를 변경하는 명령어"""
    chat_id = update.effective_chat.id
    try:
        if not context.args:
            await update.message.reply_text("usage: /set <숫자>")
            return
            
        new_day = int(context.args[0])
        user_manager = UserManager()
        
        # Update logic
        str_id = str(chat_id)
        if str_id in user_manager.users:
            # Update local DB
            user_manager.users[str_id]["current_day"] = new_day
            user_manager.save_users()
            
            # Sync to Google Sheet (Important!)
            # We reuse the last_homework_date or just today's date if None
            last_date = user_manager.users[str_id].get("last_homework_date")
            if not last_date:
                last_date = datetime.date.today().isoformat()
            
            user_manager.sync_to_sheet(str_id, new_day, last_date)
            
            await update.message.reply_text(f"🔄 진도가 {new_day}일차로 변경되었습니다!\n'/homework'를 입력하면 해당 진도의 숙제가 나옵니다.")
        else:
            await update.message.reply_text("먼저 /start를 눌러 등록해주세요.")
            
    except ValueError:
        await update.message.reply_text("⚠️ 숫자를 입력해주세요.")
    except Exception as e:
        await update.message.reply_text(f"Error: {e}")

async def my_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """내 진도 확인"""
    chat_id = update.effective_chat.id
    user_manager = UserManager()
    progress = user_manager.get_user_progress(chat_id)
    day = progress.get('current_day', 1)
    await update.message.reply_text(f"ℹ️ 현재 회원님의 진도는 [Day {day}] 입니다.")


async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # 1. Determine Reference Text
    ref_text = None
    if update.message.caption:
        ref_text = update.message.caption
    elif update.message.reply_to_message and update.message.reply_to_message.text:
        ref_text = update.message.reply_to_message.text
    elif update.message.reply_to_message and update.message.reply_to_message.text:
        ref_text = update.message.reply_to_message.text
    else:
        # Fallback: Check candidates list first
        candidates = context.user_data.get('homework_candidates', [])
        if candidates:
             # We have candidates, but we don't know WHICH one the user read.
             # We'll determine this AFTER downloading and recognizing the audio.
             pass 
        else:
            # Legacy fallback
            ref_text = context.user_data.get('last_homework')
            if ref_text:
                 await update.message.reply_text(f"💡 최근 숙제 문장으로 평가합니다.")
    
    if not ref_text and not context.user_data.get('homework_candidates'):
        await update.message.reply_text(
            "⚠️ 평가할 대본을 찾을 수 없습니다.\n"
            "'/homework'로 숙제를 먼저 받아주세요."
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
        
        # 4-1. Match Candidate if ref_text is missing
        if not ref_text:
            status_msg = await status_msg.edit_text("🎧 문장 확인 중...")
            
            # Recognize simple text first
            spoken_text = grader.recognize_simple(wav_path)
            
            if spoken_text:
                candidates = context.user_data.get('homework_candidates', [])
                if candidates:
                    # Find best match
                    matches = difflib.get_close_matches(spoken_text, candidates, n=1, cutoff=0.1) # cutoff 0.1 is very loose, we want 'best'
                    if matches:
                        ref_text = matches[0]
                        await status_msg.edit_text(f"💡 인식된 문장: \"{ref_text}\" 로 평가합니다.")
                    else:
                        # If no match found, maybe just pick the first one? Or fail?
                        # Let's pick the first one as fallback to give SOME feedack
                        ref_text = candidates[0]
                        await status_msg.edit_text(f"❓ 문장을 찾지 못해 첫 번째 숙제로 평가합니다: \"{ref_text}\"")
                else:
                     await status_msg.edit_text("⚠️ 비교할 숙제 목록이 없습니다.")
                     return
            else:
                 await status_msg.edit_text("⚠️ 음성을 명확히 인식하지 못했습니다.")
                 return

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
            
            # 6. Save Score to Google Sheet
            try:
                user_manager = UserManager()
                chat_id = update.effective_chat.id
                pronunciation_score = s['pronunciation']
                user_manager.update_user_score(chat_id, pronunciation_score)
                logging.info(f"Updated score for {chat_id}: {pronunciation_score}")
            except Exception as e:
                logging.error(f"Failed to save score: {e}")
            
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
    app.add_handler(CommandHandler("setday", set_day))
    app.add_handler(CommandHandler("set", set_day))
    app.add_handler(CommandHandler("myinfo", my_info))
    app.add_handler(MessageHandler(filters.VOICE, handle_voice))
    
    # Scheduler Setup
    job_queue = app.job_queue
    
    # 1. Daily Homework at 20:00 KST
    target_time = datetime.time(hour=20, minute=0, second=0, tzinfo=KST)
    job_queue.run_repeating(run_daily_homework, interval=86400, first=target_time)
    
    # 2. Startup Test (10 seconds after start)
    job_queue.run_once(test_scheduler_job, when=10)
    
    print(f"🤖 Telegram Bot Started... (Daily Job at {target_time})")
    app.run_polling()
