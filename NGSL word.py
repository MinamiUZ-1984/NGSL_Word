import streamlit as st
import pandas as pd
import json
import streamlit.components.v1 as components

# --- ページ設定 ---
st.set_page_config(page_title="NGSL 究極の二刀流", page_icon="⚔️", layout="centered")

# --- タイトル表示 ---
st.markdown("<div style='padding-top: 10px;'><h3 style='text-align: center;'>⚔️ NGSL ハイブリッド学習アプリ</h3></div>", unsafe_allow_html=True)

# --- データ読み込み（Colabと共通のシャッフル設定） ---
@st.cache_data
def load_data():
    try:
        try:
            df = pd.read_csv("vocab.csv", encoding="utf-8")
        except UnicodeDecodeError:
            df = pd.read_csv("vocab.csv", encoding="shift_jis")
        
        df = df.fillna("")
        new_df = pd.DataFrame()
        cols_count = df.shape[1]
        
        # 基本データの抽出
        new_df['original_rank'] = pd.to_numeric(df.iloc[:, 0], errors='coerce').fillna(0).astype(int)
        new_df['en'] = df.iloc[:, 1]
        new_df['jp'] = df.iloc[:, 2]
        new_df['ex_en'] = df.iloc[:, 4] if cols_count > 4 else ""
        new_df['ex_jp'] = df.iloc[:, 5] if cols_count > 5 else ""
        
        # Colabと完全に一致させるためのシャッフル（Seed=42）
        new_df = new_df.sample(frac=1, random_state=42).reset_index(drop=True)
        return new_df
    except Exception as e:
        st.error(f"CSV読み込み失敗: {e}")
        return pd.DataFrame()

df = load_data()

if df.empty:
    st.stop()

# --- ⚙️ 学習設定サイドバー/上部 ---
st.divider()

col1, col2 = st.columns(2)
with col1:
    # 🌟 モード切り替え機能
    mode = st.radio("学習モードを選択", ["単語カード (英→日)", "瞬間英作文 (日→英)"], horizontal=True)

with col2:
    # トラック選択
    chunk_size = 100
    total_tracks = (len(df) // chunk_size) + (1 if len(df) % chunk_size != 0 else 0)
    selected_track = st.selectbox("トラック番号", range(1, total_tracks + 1), format_func=lambda x: f"Track {x:02d}")

# --- データの準備 ---
start_idx = (selected_track - 1) * chunk_size
end_idx = start_idx + chunk_size
current_df = df.iloc[start_idx:end_idx]

# 瞬間英作文モードの場合は例文があるものだけに絞る
if "瞬間英作文" in mode:
    current_df = current_df[current_df['ex_jp'] != ""]

words_json = json.dumps(current_df.to_dict(orient="records"), ensure_ascii=False).replace("</", "<\\/")

# --- フラッシュカードUI (JavaScript) ---
html_code = f"""
<!DOCTYPE html>
<html>
<head>
    <style>
        body {{ font-family: sans-serif; text-align: center; margin: 0; padding: 10px; color: #333; }}
        .card-container {{ padding: 25px 15px; border: 3px solid #3498db; border-radius: 15px; background-color: #fff; box-shadow: 0 4px 10px rgba(0,0,0,0.1); margin-bottom: 20px; }}
        
        .progress-text {{ font-size: 14px; font-weight: bold; color: #666; background-color: #f0f4f8; display: inline-block; padding: 6px 16px; border-radius: 16px; margin-bottom: 15px; }}
        
        /* 表面のテキスト */
        .front-text {{ font-size: 32px; font-weight: bold; color: #2c3e50; margin-bottom: 20px; line-height: 1.3; }}
        
        #answerArea {{ display: none; }}
        
        /* 裏面のテキスト */
        .back-main {{ font-size: 24px; font-weight: bold; color: #e74c3c; margin-bottom: 15px; cursor: pointer; }}
        .back-sub {{ font-size: 16px; color: #555; text-align: left; background: #f8f9fa; padding: 10px; border-radius: 8px; font-style: italic; margin-top: 10px; cursor: pointer; }}
        
        .btn {{ padding: 16px; font-size: 18px; color: white; border: none; border-radius: 10px; cursor: pointer; font-weight: bold; width: 100%; max-width: 300px; margin: 10px auto; display: block; }}
        #showBtn {{ background-color: #3498db; }}
        
        .judge-container {{ display: flex; justify-content: center; gap: 10px; margin-top: 20px; }}
        .judge-btn {{ padding: 15px 10px; font-size: 16px; color: white; border: none; border-radius: 8px; cursor: pointer; font-weight: bold; flex: 1; }}
        .learned-btn {{ background-color: #2ecc71; }}
        .learning-btn {{ background-color: #e67e22; }}
    </style>
</head>
<body>
    <div id="displayArea" class="card-container">
        <div id="progressDisplay" class="progress-text"></div>
        <div id="frontDisplay" class="front-text"></div>
        
        <button id="showBtn" class="btn" onclick="showAnswer()">答えを見る</button>

        <div id="answerArea">
            <div id="backMain" class="back-main" onclick="playVoiceMain()"></div>
            <div id="backSub" class="back-sub" onclick="playVoiceSub()"></div>
            
            <div class="judge-container">
                <button class="judge-btn learning-btn" onclick="nextWord(false)">❌ まだ</button>
                <button class="judge-btn learned-btn" onclick="nextWord(true)">✅ 覚えた</button>
            </div>
        </div>
    </div>

    <script>
        const allWords = {words_json};
        const mode = "{mode}";
        let currentIndex = 0;
        let currentItem = null;
        const synth = window.speechSynthesis;

        // モードごとに別の記録を保存
        const storageKey = mode.includes("単語") ? "ngsl_word_v05" : "ngsl_speak_v05";
        let progress = JSON.parse(localStorage.getItem(storageKey) || "{{}}");

        function speak(text) {{
            if (!text) return;
            synth.cancel();
            const u = new SpeechSynthesisUtterance(text);
            u.lang = 'en-US';
            u.rate = 0.9;
            synth.speak(u);
        }}

        function showCard() {{
            currentItem = allWords[currentIndex];
            document.getElementById('progressDisplay').innerText = (currentIndex + 1) + " / " + allWords.length;
            
            if (mode.includes("単語")) {{
                // 単語カードモード：表＝英単語、裏＝日単語
                document.getElementById('frontDisplay').innerText = currentItem.en;
                document.getElementById('backMain').innerText = currentItem.jp;
                document.getElementById('backSub').innerHTML = "例文: " + currentItem.ex_en + "<br><small>" + currentItem.ex_jp + "</small>";
                speak(currentItem.en);
            }} else {{
                // 瞬間英作文モード：表＝日例文、裏＝英例文
                document.getElementById('frontDisplay').innerText = currentItem.ex_jp;
                document.getElementById('backMain').innerText = currentItem.ex_en;
                document.getElementById('backSub').innerText = "Target Word: " + currentItem.en + " (" + currentItem.jp + ")";
            }}
            
            document.getElementById('answerArea').style.display = 'none';
            document.getElementById('showBtn').style.display = 'block';
        }}

        function showAnswer() {{
            document.getElementById('showBtn').style.display = 'none';
            document.getElementById('answerArea').style.display = 'block';
            if (mode.includes("瞬間英作文")) speak(currentItem.ex_en);
        }}

        function playVoiceMain() {{
            speak(mode.includes("単語") ? currentItem.en : currentItem.ex_en);
        }}
        
        function playVoiceSub() {{
            speak(currentItem.ex_en);
        }}

        function nextWord(isLearned) {{
            if (isLearned) {{
                progress[currentItem.original_rank] = true;
                localStorage.setItem(storageKey, JSON.stringify(progress));
            }}
            currentIndex++;
            if (currentIndex < allWords.length) {{
                showCard();
            }} else {{
                alert("全単語終了です！お疲れ様でした！");
                location.reload();
            }}
        }}

        showCard();
    </script>
</body>
</html>
"""

components.html(html_code, height=600, scrolling=True)

st.caption("※「単語カード」と「瞬間英作文」の学習進捗は別々に保存されます。")
