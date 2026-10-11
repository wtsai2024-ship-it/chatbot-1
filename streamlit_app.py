import streamlit as st
from google import genai
from google.genai import types
import time

st.title("💬 Gemini Chatbot (自動認証版)")
st.write(
    "このアプリは Google の Gemini モデルを使用したチャットボットです。"
    "APIキーは設定ファイル（Secrets）から自動で読み込まれます。"
)

# st.secrets からAPIキーを自動取得
try:
    gemini_api_key = st.secrets["GEMINI_API_KEY"]
except Exception:
    gemini_api_key = None

if not gemini_api_key:
    st.error(
        "APIキーが設定されていません。.streamlit/secrets.toml または "
        "Streamlit CloudのSecrets設定に `GEMINI_API_KEY` を登録してください。",
        icon="🚨"
    )
else:
    # Geminiクライアントの初期化
    client = genai.Client(api_key=gemini_api_key)

    # チャット履歴を保持するセッションステートの初期化
    if "messages" not in st.session_state:
        st.session_state.messages = []

    # 既存のチャットメッセージを表示
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # ユーザーからの入力を受け取る
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

            # 503エラー対策のリトライロジック
            for attempt in range(max_retries):
                try:
                    response_stream = client.models.generate_content_stream(
                        model="gemini-3.8-flash",
                        contents=history_contents,
                    )
                    break
                except Exception as e:
                    if ("503" in str(e) or "UNAVAILABLE" in str(e)) and attempt < max_retries - 1:
                        time.sleep(wait_seconds)
                        wait_seconds *= 2
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
