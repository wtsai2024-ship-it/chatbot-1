import streamlit as st
from google import genai
from google.genai import types
import time

st.title("💬 Gemini Chatbot (安定性強化版)")
st.write(
    "このアプリは Google の Gemini モデルを使用したチャットボットです。"
    "混雑時の 503 エラーに対する自動リトライ機能を備えています。"
)

gemini_api_key = st.text_input("Gemini API Key", type="password")

if not gemini_api_key:
    st.info("続けるには Gemini API キーを入力してください。", icon="🗝️")
else:
    client = genai.Client(api_key=gemini_api_key)

    if "messages" not in st.session_state:
        st.session_state.messages = []

    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    if prompt := st.chat_input("何か質問してください..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        history_contents = []
        for m in st.session_state.messages:
            role = "user" if m["role"] == "user" else "model"
            history_contents.append(
                types.Content(
                    role=role,
                    parts=[types.Part.from_text(text=m["content"])]
                )
            )

        with st.chat_message("assistant"):
            response_stream = None
            max_retries = 3
            wait_seconds = 2

            # 503エラー対策としての自動リトライロジック
            for attempt in range(max_retries):
                try:
                    response_stream = client.models.generate_content_stream(
                        model="gemini-3.8-flash",
                        contents=history_contents,
                    )
                    break
                except Exception as e:
                    # 503エラーや一時的な過負荷エラーの場合のみリトライ
                    if ("503" in str(e) or "UNAVAILABLE" in str(e)) and attempt < max_retries - 1:
                        time.sleep(wait_seconds)
                        wait_seconds *= 2  # 待機時間を倍々に増やす
                    else:
                        st.error(f"APIサーバーが混雑しています。しばらく時間を置いてから再度お試しください。\n(エラー詳細: {e})")
                        break

            if response_stream:
                try:
                    def stream_generator():
                        for chunk in response_stream:
                            if chunk.text:
                                yield chunk.text

                    response = st.write_stream(stream_generator())
                    st.session_state.messages.append({"role": "assistant", "content": response})
                except Exception as e:
                    st.error(f"ストリーミング処理中にエラーが発生しました: {e}")
