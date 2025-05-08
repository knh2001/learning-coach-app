import streamlit as st
import openai
from streamlit_mic_recorder import mic_recorder
from PIL import Image
import os
import base64
import edge_tts
import asyncio

# Set OpenAI API key
openai.api_key = st.secrets["OPENAI_API_KEY"]  # Or use os.getenv("OPENAI_API_KEY")

# Google Speech or Edge
GOOGLE_KEY = st.secrets["GOOGLE_API_KEY"]
AZURE_KEY = st.secrets["AZURE_SPEECH_KEY"]
AZURE_REGION = st.secrets["AZURE_REGION"]

st.set_page_config(page_title="📚 초개인화 학습 상담", layout="wide")
st.title("🎓 AI 기반 초개인화 학습 상담")

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
    selected_level = st.selectbox("학습 수준", ["유치원", "초등학생", "중학생", "고등학생"])
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

# Input zone: multimodal options
st.markdown("### 🎤 질문을 말하거나 텍스트로 입력해보세요")

# Mic input
text_result = mic_recorder(start_prompt="음성으로 질문하기", stop_prompt="정지", just_once=True, use_container_width=True, key="voice")

# Text input fallback
text_input = st.text_area("또는 텍스트로 질문하기", placeholder="학습에 대해 궁금한 걸 자유롭게 적어보세요...", height=100)

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

# 음성 출력 함수
async def generate_tts(text, lang="ko-KR", gender="여성", speed=0):
    voices = {
        "ko-KR": {"여성": "ko-KR-SunHiNeural", "남성": "ko-KR-InJoonNeural"},
        "en-US": {"여성": "en-US-JennyNeural", "남성": "en-US-GuyNeural"},
        "ja-JP": {"여성": "ja-JP-NanamiNeural", "남성": "ja-JP-KeitaNeural"},
        "zh-CN": {"여성": "zh-CN-XiaoxiaoNeural", "남성": "zh-CN-YunxiNeural"},
    }
    voice_id = voices[lang][gender]
    rate = f"{speed:+d}%"
    communicate = edge_tts.Communicate(text=text, voice=voice_id, rate=rate)
    await communicate.save("tts_output.mp3")
    return "tts_output.mp3"

# Generate GPT response
if st.button("🧠 AI 상담 받기"):
    with st.spinner("AI가 생각 중이에요..."):
        user_content = text_result if text_result else text_input
        if not user_content:
            st.warning("질문을 입력하거나 말해주세요.")
        else:
            messages = [
                {"role": "system", "content": f"너는 {selected_level} 학습자의 질문에 맞는 학습 전략과 조언을 제공하는 초개인화 AI 멘토야. 관심 과목은 {', '.join(subject)}야."},
                {"role": "user", "content": user_content},
            ]
            if image_base64:
                messages.append({
                    "role": "user",
                    "content": [
                        {"type": "text", "text": user_content},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_base64}"}}
                    ]
                })
            response = openai.ChatCompletion.create(
                model="gpt-4o",
                messages=messages
            )
            reply = response.choices[0].message.content
            st.success("AI의 응답:")
            st.markdown(reply)

            # 상담 결과 저장
            if reply:
                st.session_state.chat_history.append({
                    "이름": name,
                    "학습 수준": selected_level,
                    "기분": mood,
                    "과목": subject,
                    "질문": user_content,
                    "답변": reply
                })

            # 음성 출력 (Edge TTS)
            audio_path = asyncio.run(generate_tts(reply, lang=voice_lang, gender=voice_gender, speed=voice_speed))
            st.audio(audio_path, format="audio/mp3")

st.markdown("### 📂 오늘의 상담 기록 보기")
for i, chat in enumerate(st.session_state.chat_history):
    st.markdown(f"**{i+1}. 질문:** {chat['질문']}")
    st.markdown(f"👉 **AI 응답:** {chat['답변']}")
    st.markdown("---")

