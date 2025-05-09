import streamlit as st
import openai
from streamlit_mic_recorder import mic_recorder
from PIL import Image
import os
import base64
import edge_tts
import asyncio
import nest_asyncio

# Apply nested asyncio loop
nest_asyncio.apply()

# Set OpenAI API key from secrets
openai.api_key = st.secrets["OPENAI_API_KEY"]

# Google Speech or Edge
GOOGLE_KEY = st.secrets["GOOGLE_API_KEY"]
AZURE_KEY = st.secrets["AZURE_SPEECH_KEY"]
AZURE_REGION = st.secrets["AZURE_REGION"]

# Page settings
st.set_page_config(
    page_title="공쌤 – 초개인화 학습 상담",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Custom CSS
st.markdown("""
<style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    /* Main container styling */
    .main {
        padding: 2rem;
        background-color: #f8f9fa;
    }
    
    /* Title styling */
    h1 {
        color: #2c3e50;
        font-size: 2.5rem !important;
        font-weight: 700 !important;
        margin-bottom: 1rem !important;
    }
    
    /* Subtitle styling */
    .subtitle {
        color: #7f8c8d;
        font-size: 1.2rem !important;
        margin-bottom: 2rem !important;
    }
    
    /* Card styling */
    .stButton>button {
        width: 100%;
        background-color: #3498db;
        color: white;
        border: none;
        padding: 0.5rem 1rem;
        border-radius: 5px;
        font-weight: 600;
        transition: all 0.3s ease;
    }
    
    .stButton>button:hover {
        background-color: #2980b9;
        transform: translateY(-2px);
    }
    
    /* Input styling */
    .stTextInput>div>div>input {
        border-radius: 5px;
        border: 2px solid #e0e0e0;
        padding: 0.5rem;
    }
    
    /* Radio button styling */
    .stRadio>div {
        background-color: white;
        padding: 1rem;
        border-radius: 5px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    
    /* Response container styling */
    .response-container {
        background-color: white;
        padding: 1.5rem;
        border-radius: 10px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        margin-top: 2rem;
    }
</style>
""", unsafe_allow_html=True)

# Header
st.title("👩‍🏫 공쌤과 함께하는 학습 상담")
st.markdown('<p class="subtitle">🧠 나에게 꼭 맞는 공부 방법을 AI 선생님 공쌤에게 물어보세요!</p>', unsafe_allow_html=True)

# 세션 상태에 음성 설정 저장
if "saved_voice" not in st.session_state:
    st.session_state["saved_voice"] = {
        "lang": "ko-KR",
        "gender": "여성",
        "speed": 0
    }

# Sidebar for user profile
with st.sidebar:
    st.header("👤 학습자 정보")
    name = st.text_input("이름")
    selected_level = st.radio(
        "학습자 수준을 선택해주세요",
        ["유치원", "초등학생", "중학생", "고등학생"],
        horizontal=True,
        label_visibility="collapsed"
    )
    subject = st.multiselect("관심 과목", ["수학", "과학", "국어", "영어"])
    mood = st.radio("오늘 기분은?", ["🙂 괜찮아요", "😐 보통이에요", "😣 좀 힘들어요"])
    st.markdown("---")
    st.subheader("🔈 음성 출력 설정")
    voice_lang = st.selectbox("음성 언어", ["ko-KR", "en-US", "ja-JP", "zh-CN"])
    voice_gender = st.selectbox("성별", ["여성", "남성"])
    voice_speed = st.slider("음성 속도 (기본: 0)", min_value=-50, max_value=50, step=10, value=0)

# 사용자가 바꾼 값 저장
st.session_state["saved_voice"]["lang"] = voice_lang
st.session_state["saved_voice"]["gender"] = voice_gender
st.session_state["saved_voice"]["speed"] = voice_speed

# Create two columns for input methods
col1, col2 = st.columns(2)

with col1:
    st.markdown("### 🎤 음성으로 질문하기")
    text_result = mic_recorder(
        start_prompt="🎙️ 녹음 시작",
        stop_prompt="⏹️ 녹음 중지",
        use_container_width=True,
        just_once=True,
        key="mic"
    )

with col2:
    st.markdown("### ✍️ 텍스트로 질문하기")
    text_input = st.text_input(
        "입력하고 싶은 내용이 있나요?",
        placeholder="예: 수학이 너무 어려워요 어떻게 해야 할까요?"
    )

# Image upload
st.markdown("---")
st.markdown("### 🖼️ 문제나 학습 자료가 있다면 이미지를 업로드해 주세요")
image_file = st.file_uploader("이미지 업로드", type=["png", "jpg", "jpeg"])
image_base64 = None
if image_file is not None:
    image = Image.open(image_file)
    st.image(image, caption="업로드된 이미지", use_column_width=True)
    image_base64 = base64.b64encode(image_file.getvalue()).decode("utf-8")

# edge-tts 동기 래퍼 함수
def speak_sync(text, filename="edge_output.mp3"):
    async def speak(text, filename):
        communicate = edge_tts.Communicate(text=text, voice="ko-KR-SunHiNeural")
        await communicate.save(filename)
    asyncio.run(speak(text, filename))

# 응답 저장용 세션 초기화
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

# Voice output functions
def get_voice_id(lang="ko-KR", gender="여성"):
    voices = {
        "ko-KR": {"여성": "ko-KR-SunHiNeural", "남성": "ko-KR-InJoonNeural"},
    }
    return voices[lang][gender]

async def generate_tts(text, lang="ko-KR", gender="여성", speed=0):
    voice_id = get_voice_id(lang, gender)
    rate = f"{speed:+d}%"
    communicate = edge_tts.Communicate(text=text, voice=voice_id, rate=rate)
    await communicate.save("tts_output.mp3")
    return "tts_output.mp3"

# GPT consultation with improved UI
if st.button("📩 공쌤에게 질문 보내기", use_container_width=True):
    user_question = text_result if text_result else text_input
    if not user_question:
        st.warning("⚠️ 먼저 질문을 말하거나 입력해주세요!")
    else:
        with st.spinner("🤔 공쌤이 열심히 생각하고 있어요..."):
            prompt = f"너는 이름이 '공쌤'인 AI 선생님이야. 학습자의 수준은 {selected_level}이고, 공부에 대한 고민을 친절하고 따뜻하게 상담해줘."
            messages = [
                {"role": "system", "content": prompt},
                {"role": "user", "content": user_question}
            ]
            response = openai.ChatCompletion.create(
                model="gpt-4",
                messages=messages
            )
            answer = response.choices[0].message.content
            
            # Response container with improved styling
            st.markdown('<div class="response-container">', unsafe_allow_html=True)
            st.markdown("### 📣 공쌤의 대답")
            st.markdown(answer)
            st.markdown('</div>', unsafe_allow_html=True)

            # Voice output with improved UI
            with st.spinner("🔊 음성 변환 중..."):
                loop = asyncio.get_event_loop()
                audio_path = loop.run_until_complete(generate_tts(answer))
                st.audio(audio_path, format="audio/mp3")

st.markdown("### 📂 오늘의 상담 기록 보기")
for i, chat in enumerate(st.session_state.chat_history):
    st.markdown(f"**{i+1}. 질문:** {chat['질문']}")
    st.markdown(f"👉 **AI 응답:** {chat['답변']}")
    st.markdown("---")

