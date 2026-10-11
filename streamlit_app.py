import streamlit as st
from google import genai
from google.genai import types
import time

# タイトルと説明文を表示
st.title("💬 Gemini Chatbot")
st.write(
    "このアプリは Google の Gemini モデルを使用したシンプルなチャットボットです。"
    "利用するには Google AI Studio で取得した Gemini API キーを入力してください。"
)

# ユーザーにGemini APIキー入力を求める
gemini_api_key = st.text_input("Gemini API Key", type="password")

if not gemini_api_key:
    st.info("続けるには Gemini API キーを入力してください。", icon="🗝️")
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

        # ユーザーの入力を保存・表示
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        # Gemini APIへ送るための過去のチャット履歴を変換
        history_contents = []
        for m in st.session_state.messages:
            role = "user" if m["role"] == "user" else "model"
            history_contents.append(
                types.Content(
                    role=role,
                    parts=[types.Part.from_text(text=m["content"])]
                )
            )

        # アシスタントの返答をストリーミング形式で生成・表示（リトライ処理付き）
        with st.chat_message("assistant"):
            response_stream = None
            max_retries = 3
            wait_seconds = 2

            for attempt in range(max_retries):
                try:
                    response_stream = client.models.generate_content_stream(
                        model="gemini-3.8-flash",
                        contents=history_contents,
                    )
                    break # 成功したらループを抜ける
                except Exception as e:
                    if "503" in str(e) and attempt < max_retries - 1:
                        time.sleep(wait_seconds)
                        wait_seconds *= 2 # 待機時間を増やす（指数バックオフ）
                    else:
                        st.error(f"エラーが発生しました: {e}")
                        break

            if response_stream:
                try:
                    def stream_generator():
                        for chunk in response_stream:
                            if chunk.text:
                                yield chunk.text

                    response = st.write_stream(stream_generator())
                    # アシスタントの応答をセッションに保存
                    st.session_state.messages.append({"role": "assistant", "content": response})
                except Exception as e:
                    st.error(f"ストリーミング処理中にエラーが発生しました: {e}")
