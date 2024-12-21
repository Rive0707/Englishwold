import pandas as pd
import random
import os
import io
from datetime import datetime
import streamlit as st
from gtts import gTTS
import tempfile
import logging
import platform

# ロギングの設定
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# 一時ファイルディレクトリの設定
TEMP_DIR = os.environ.get("STREAMLIT_TEMP_AUDIO_DIR") #環境変数で設定する場合
if not TEMP_DIR:
    if platform.system() == "Windows":
        TEMP_DIR = os.path.join(os.path.expanduser("~"), "streamlit_temp_audio")
    else:
        TEMP_DIR = tempfile.gettempdir()
try:
    os.makedirs(TEMP_DIR, exist_ok=True)
    logging.info(f"一時ファイルディレクトリを作成/確認: {TEMP_DIR}")
except OSError as e:
    logging.error(f"一時ファイルディレクトリの作成/確認に失敗: {e}")
    st.error(f"一時ファイルディレクトリの作成に失敗しました: {e}。ディレクトリ {TEMP_DIR} へのアクセス権限を確認してください。管理者権限での実行も試してください。")
    st.stop()  # Streamlitアプリを停止


# 単語学習アプリ
class WordLearningApp:
    def __init__(self):
        self.original_word_data = []
        self.word_data = []
        self.record = []
        self.incorrect_words = []
        self.reviewing_incorrect = False
        self.current_word_index = 0

    def load_csv(self, uploaded_file):
        try:
            logging.info(f"CSVファイルを読み込み中: {uploaded_file.name}")
            df = pd.read_csv(uploaded_file, encoding="utf-8")
            logging.info("CSVファイルの読み込みに成功しました。")
            return df.to_dict(orient="records")
        except Exception as e:
            st.error(f"CSV読み込みエラー: {e}")
            logging.exception("CSV読み込みエラー")
            return []

    def get_next_word(self):
        if not self.word_data:
            return None

        if self.current_word_index >= len(self.word_data):
            if self.reviewing_incorrect:
                self.word_data = self.original_word_data.copy()
                self.reviewing_incorrect = False
            self.current_word_index = 0
            return None

        current_word = self.word_data[self.current_word_index]
        return current_word

    def play_audio(self, text, lang="en"):
        try:
            logging.info(f"音声再生開始: {text}")
            tts = gTTS(text=text, lang=lang)

            with tempfile.NamedTemporaryFile(delete=True, suffix=".mp3", dir=TEMP_DIR) as temp_file: #dirを指定
                temp_file_path = temp_file.name
                tts.save(temp_file_path)

                st.audio(temp_file_path, format="audio/mp3")
                logging.info(f"音声ファイルを保存・再生: {temp_file_path}")

        except Exception as e:
            st.error(f"音声の生成中にエラーが発生しました: {e}")
            logging.exception("音声生成エラー")
        logging.info(f"音声再生終了: {text}")

    def check_answer(self, option, current_word):
        is_correct = option == current_word["日本語訳"]
        self.record.append({
            "英単語": current_word["英単語"],
            "あなたの回答": option,
            "正解": current_word["日本語訳"],
            "正誤": "正解" if is_correct else "不正解"
        })
        if not is_correct:
            self.incorrect_words.append(current_word)
        return is_correct

    def show_history(self):
        history_df = pd.DataFrame(self.record)
        st.dataframe(history_df)

    def review_incorrect_words(self):
        if not self.incorrect_words:
            st.info("不正解単語はありません。")
            return False
        else:
            self.original_word_data = self.word_data.copy()
            self.word_data = self.incorrect_words
            self.incorrect_words = []
            self.reviewing_incorrect = True
            return True

# Streamlit アプリの実行
def main():
    app = WordLearningApp()
    uploaded_file = st.file_uploader("CSVファイルをアップロードしてください", type="csv")

    if uploaded_file is not None:
        st.write(f"アップロードされたファイル: {uploaded_file.name}")

        app.word_data = app.load_csv(uploaded_file)
        if not app.word_data:
            return

        app.original_word_data = app.word_data.copy()

        st.title("英単語学習アプリ")
        st.subheader("英単語を学習しましょう")

        if "current_word_index" not in st.session_state:
            st.session_state["current_word_index"] = 0

        current_word = app.get_next_word()

        if current_word:
            st.subheader(f"英単語: {current_word['英単語']}")
            st.write(f"例文: {current_word['例文']}")

            options = [current_word["日本語訳"]]
            while len(options) < 4:
                option = random.choice(app.word_data)["日本語訳"]
                if option not in options:
                    options.append(option)
            random.shuffle(options)

            for i, option in enumerate(options):
                if st.button(option, key=f"{current_word['英単語']}-{i}"):
                    if app.check_answer(option, current_word):
                        st.session_state["current_word_index"] += 1
                        st.experimental_rerun()
                    else:
                        st.experimental_rerun()

            if st.button("音声を再生"):
                app.play_audio(current_word["英単語"])

        col1, col2 = st.columns(2)
        with col1:
            if st.button("学習履歴"):
                app.show_history()
        with col2:
            if st.button("不正解単語復習"):
                if app.review_incorrect_words():
                    st.session_state["current_word_index"] = 0
                    st.experimental_rerun()

    else:
        st.write("CSVファイルをアップロードしてください。")

if __name__ == "__main__":
    main()