
import streamlit as st
import os
import tempfile
import time
from dotenv import load_dotenv
import subprocess
from homework_manager import HomeworkManager
from user_manager import UserManager
from azure_stt import AzureGrader
import difflib

# 1. Init & Config
st.set_page_config(page_title="J-DoIt Speaking Practice", page_icon="🎤")
load_dotenv()

# Initialize Managers
if 'user_manager' not in st.session_state:
    st.session_state.user_manager = UserManager()
if 'hw_manager' not in st.session_state:
    st.session_state.hw_manager = HomeworkManager()

# Azure Config
# Azure Config
AZURE_KEY = os.getenv("AZURE_SPEECH_KEY")
AZURE_REGION = os.getenv("AZURE_SPEECH_REGION")

# Fallback to Streamlit Secrets if env vars are missing
if not AZURE_KEY and "AZURE_SPEECH_KEY" in st.secrets:
    AZURE_KEY = st.secrets["AZURE_SPEECH_KEY"]
if not AZURE_REGION and "AZURE_SPEECH_REGION" in st.secrets:
    AZURE_REGION = st.secrets["AZURE_SPEECH_REGION"]

# 2. Sidebar - User Login
st.sidebar.title("🔐 로그인")
user_id = st.sidebar.text_input("전화번호 뒷자리 (또는 ID)", placeholder="예: 1234")

if user_id:
    # Login Logic
    st.session_state.user_id = user_id
    
    # Get User Progress
    progress = st.session_state.user_manager.get_user_progress(user_id)
    current_day = progress.get('current_day', 1)
    
    st.sidebar.success(f"환영합니다! \n현재 진도: **Day {current_day}**")
    
    # Reset Day Button (For Testing)
    # if st.sidebar.button("진도 초기화 (Test)"):
    #     st.session_state.user_manager.users[str(user_id)]['current_day'] = 1
    #     st.session_state.user_manager.save_users()
    #     st.experimental_rerun()

else:
    st.title("🎤 J-DoIt 스피킹 연습장")
    st.info("👈 왼쪽 사이드바에 ID를 입력하여 로그인해주세요.")
    st.stop()

# 3. Main Interface
st.title(f"📅 Day {current_day} 연습하기")

# Fetch Homework
hw_list = st.session_state.hw_manager.get_homework(day=current_day)

if not hw_list:
    st.success("🎉 모든 과정을 수료하셨습니다! 더 이상 숙제가 없습니다.")
    st.stop()

# Display Homeworks
st.subheader("📚 오늘의 문장")
candidates = []
for idx, hw in enumerate(hw_list, 1):
    text = hw.get('text', '')
    candidates.append(text)
    st.markdown(f"**{idx}.** {text}")
    audio_url = hw.get('audio_url')
    if audio_url:
        st.audio(audio_url)

st.divider()

# 4. Audio Recorder
st.subheader("🎙️ 녹음 및 평가")
st.write("위 문장 중 하나를 골라 읽어주세요.")

audio_value = st.audio_input("녹음하기 (마이크 아이콘 클릭)")

if audio_value:
    # Save raw audio to temp file
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp_audio:
        tmp_audio.write(audio_value.read())
        raw_path = tmp_audio.name

    # Convert to 16k Mono WAV using ffmpeg (Azure requirement)
    # We use a second temp file for the converted output
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as converted_audio:
        tmp_filename = converted_audio.name
    
    # Run ffmpeg
    # -i input -ac 1 (mono) -ar 16000 (16k sample rate) output -y (overwrite)
    try:
        subprocess.run(["ffmpeg", "-i", raw_path, "-ac", "1", "-ar", "16000", tmp_filename, "-y"], check=True)
    except Exception as e:
        st.error(f"Audio conversion failed: {e}")
        tmp_filename = raw_path # Fallback to raw (might fail grading but better than crash)
    finally:
        # Clean up raw file
        if os.path.exists(raw_path):
            os.remove(raw_path)

    # Grade
    if not AZURE_KEY or not AZURE_REGION:
        st.error("Azure 설정이 되어있지 않습니다. .env 파일을 확인해주세요.")
    else:
        with st.spinner("🎧 채점 중입니다... 잠시만 기다려주세요."):
            grader = AzureGrader(AZURE_KEY, AZURE_REGION)
            
            # 1. Recognize Text first to match homework
            spoken_text = grader.recognize_simple(tmp_filename)
            
            target_text = None
            if spoken_text:
                matches = difflib.get_close_matches(spoken_text, candidates, n=1, cutoff=0.1)
                if matches:
                    target_text = matches[0]
                    st.info(f"💡 인식된 문장: **{target_text}**")
                else:
                    st.warning("⚠️ 문장을 찾지 못했습니다. 첫 번째 문장으로 평가합니다.")
                    target_text = candidates[0]
            else:
                st.error("목소리가 잘 들리지 않습니다. 다시 녹음해주세요.")
                target_text = candidates[0] # Fallback
            
            # 2. Detailed Grading
            res = grader.grade(tmp_filename, target_text)

            if res['status'] == 'success':
                scores = res['scores']
                final_score = scores['pronunciation']
                
                # Update User Score & Progress
                st.session_state.user_manager.update_user_score(user_id, final_score)
                # Auto-advance day if score is good enough? (Optional, let's keep it manual or simple for now)
                # let's advance anyway for homework completion
                st.session_state.user_manager.advance_user_day(user_id)
                
                # UI Result
                col1, col2, col3, col4 = st.columns(4)
                col1.metric("종합 점수", f"{final_score:.0f}", delta_color="normal")
                col2.metric("정확도", f"{scores['accuracy']:.0f}")
                col3.metric("유창성", f"{scores['fluency']:.0f}")
                col4.metric("완결성", f"{scores['completeness']:.0f}")
                
                # Feedback
                errors = [w for w in res['word_details'] if w['error_type'] != 'None']
                if errors:
                    st.warning("🧐 **피드백**")
                    for e in errors:
                        etype = e['error_type']
                        if etype == "Mispronunciation": etype = "❌ 발음"
                        elif etype == "Omission": etype = "🗑 누락"
                        elif etype == "Insertion": etype = "➕ 추임새"
                        st.write(f"- **{e['word']}**: {etype}")
                else:
                    st.success("완벽합니다! 👏")
                    
                st.toast("진도가 업데이트되었습니다! 내일 또 만나요 👋")
                time.sleep(2)
                st.rerun()
                
            else:
                st.error(f"평가 실패: {res.get('message')}")
            
    # Cleanup
    os.remove(tmp_filename)
