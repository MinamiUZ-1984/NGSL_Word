import streamlit as st
import pandas as pd
import json
import streamlit.components.v1 as components

# --- ページ設定 ---
st.set_page_config(page_title="NGSL テスト＆管理", page_icon="📝", layout="centered")

# 上部の余白
st.markdown("<div style='padding-top: 20px;'><h3 style='text-align: center;'>📝 NGSL 単語テスト＆管理</h3></div>", unsafe_allow_html=True)

# --- データ読み込み＆シャッフル ---
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
        
        new_df['original_rank'] = df.iloc[:, 0] if cols_count > 0 else range(1, len(df) + 1)
        new_df['en'] = df.iloc[:, 1] if cols_count > 1 else ""
        new_df['jp'] = df.iloc[:, 2] if cols_count > 2 else ""      
        new_df['ex_en'] = df.iloc[:, 4] if cols_count > 4 else ""   
        new_df['ex_jp'] = df.iloc[:, 5] if cols_count > 5 else ""   
        
        new_df['original_rank'] = pd.to_numeric(new_df['original_rank'], errors='coerce').fillna(0).astype(int)
        # シード値「42」で固定シャッフル
        new_df = new_df.sample(frac=1, random_state=42).reset_index(drop=True)
        
        return new_df
    except Exception as e:
        st.error(f"CSVの読み込みに失敗しました: {e}")
        return pd.DataFrame()

df = load_data()

if df.empty:
    st.warning("単語データを読み込めません。vocab.csv を確認してください。")
    st.stop()

# --- 🎯 トラック選択 ---
st.divider()
chunk_size = 100
total_tracks = (len(df) // chunk_size) + (1 if len(df) % chunk_size != 0 else 0)

st.write("▼ 学習するトラックを選択")
selected_track = st.selectbox("トラック番号", range(1, total_tracks + 1), format_func=lambda x: f"Track {x:02d}")

start_idx = (selected_track - 1) * chunk_size
end_idx = start_idx + chunk_size
track_df = df.iloc[start_idx:end_idx]

st.info(f"🎧 **Track {selected_track:02d}** のテスト\n\n※「答えを見る」を押した後、英文をタップすると読み上げます。")

# JSONデータ作成
words_json = json.dumps(track_df.to_dict(orient="records"), ensure_ascii=False).replace("</", "<\\/")

# --- フラッシュカードUI (例文タップ対応) ---
html_code = f"""
<!DOCTYPE html>
<html>
<head>
    <style>
        body {{ font-family: sans-serif; text-align: center; margin: 0; padding: 20px 10px; color: #333; }}
        .card-container {{ padding: 20px 15px; border: 2px solid #2ecc71; border-radius: 12px; background-color: #f9fff9; max-width: 100%; margin: 0 auto; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }}
        
        .progress-text {{ font-size: 15px; font-weight: bold; color: #666; background-color: #e0f2fe; display: inline-block; padding: 8px 16px; border-radius: 16px; margin-bottom: 20px; }}
        
        .en-word {{ font-size: 32px; font-weight: bold; color: #2c3e50; margin-bottom: 15px; cursor: pointer; }}
        
        #answerArea {{ display: none; }}
        .jp-word {{ font-size: 22px; font-weight: bold; color: #e74c3c; margin-bottom: 10px; }}
        hr {{ margin: 15px 0; border: none; border-top: 1px dashed #ccc; }}
        
        /* 例文エリアのデザイン：タップ可能であることを示す */
        .ex-container {{ background-color: #f0f4f8; padding: 10px; border-radius: 8px; cursor: pointer; transition: background 0.2s; text-align: left; position: relative; }}
        .ex-container:active {{ background-color: #d1e3f0; }}
        .ex-label {{ font-size: 10px; color: #3498db; font-weight: bold; display: block; margin-bottom: 3px; }}
        .ex-en {{ font-size: 16px; color: #2c3e50; margin-bottom: 5px; font-style: italic; line-height: 1.4; }}
        .ex-jp {{ font-size: 13px; color: #777; line-height: 1.3; }}
        
        .btn {{ padding: 16px 20px; font-size: 18px; color: white; border: none; border-radius: 8px; cursor: pointer; font-weight: bold; width: 100%; max-width: 320px; margin: 10px auto; display: block; }}
        
        #showAnswerBtn {{ background-color: #3498db; margin-top: 25px; }}
        
        .judge-container {{ display: flex; justify-content: center; gap: 15px; margin-top: 25px; }}
        .judge-btn {{ padding: 16px 10px; font-size: 18px; color: white; border: none; border-radius: 8px; cursor: pointer; font-weight: bold; flex: 1; max-width: 150px; }}
        #learnedBtn {{ background-color: #2ecc71; }}
        #learningBtn {{ background-color: #e67e22; }}
        
        #resetBtn {{ background-color: #95a5a6; font-size: 14px; padding: 10px 20px; width: auto; margin-top: 40px; display: inline-block; }}
    </style>
</head>
<body>

    <script type="application/json" id="wordsData">{words_json}</script>

    <button id="startBtn" class="btn" style="background-color: #1E90FF;" onclick="startTest()">▶️ テストを開始する</button>

    <div id="displayArea" class="card-container" style="display: none;">
        <div id="progressDisplay" class="progress-text"></div>
        
        <div id="enWord" class="en-word" onclick="speakText(currentWordObj.en)"></div>
        
        <button id="showAnswerBtn" class="btn" onclick="showAnswer()">👀 答えを見る</button>

        <div id="answerArea">
            <div id="jpWord" class="jp-word"></div>
            <hr>
            <div class="ex-container" onclick="speakText(currentWordObj.ex_en)">
                <span class="ex-label">🔊 Tap to Listen</span>
                <div id="exEn" class="ex-en"></div>
                <div id="exJp" class="ex-jp"></div>
            </div>
            
            <div class="judge-container">
                <button id="learningBtn" class="judge-btn" onclick="nextWord(false)">❌ まだ</button>
                <button id="learnedBtn" class="judge-btn" onclick="nextWord(true)">✅ 覚えた</button>
            </div>
        </div>
    </div>

    <button id="resetBtn" class="btn" onclick="resetProgress()">🔄 全記録をリセット</button>

    <script>
        let allWords = [];
        let playlist = [];
        let currentIndex = 0;
        let currentWordObj = null;
        const synth = window.speechSynthesis;

        try {{
            allWords = JSON.parse(document.getElementById('wordsData').textContent);
        }} catch(e) {{ console.error("Data error", e); }}

        let progress = JSON.parse(localStorage.getItem('ngsl_progress') || "{{}}");

        function saveProgress() {{
            localStorage.setItem('ngsl_progress', JSON.stringify(progress));
        }}

        function resetProgress() {{
            if (confirm("記録をリセットしますか？")) {{
                localStorage.removeItem('ngsl_progress');
                progress = {{}};
                location.reload();
            }}
        }}

        // 指定されたテキストを読み上げる汎用関数
        function speakText(text) {{
            if (!text) return;
            synth.cancel();
            const utterance = new SpeechSynthesisUtterance(text);
            utterance.lang = 'en-US';
            utterance.rate = 0.9;
            synth.speak(utterance);
        }}

        function startTest() {{
            playlist = allWords.filter(w => !progress[w.original_rank]?.skipped);
            if (playlist.length === 0) {{
                alert("このトラックは完了しています！");
                return;
            }}
            currentIndex = 0;
            document.getElementById('startBtn').style.display = 'none';
            document.getElementById('resetBtn').style.display = 'none';
            document.getElementById('displayArea').style.display = 'block';
            showCurrentCard();
        }}

        function showCurrentCard() {{
            currentWordObj = playlist[currentIndex];
            document.getElementById('progressDisplay').innerText = `残り ${{playlist.length - currentIndex}} 語 / ${{playlist.length}}`;
            document.getElementById('enWord').innerText = currentWordObj.en;
            document.getElementById('answerArea').style.display = 'none';
            document.getElementById('showAnswerBtn').style.display = 'block';
            
            document.getElementById('jpWord').innerText = currentWordObj.jp;
            document.getElementById('exEn').innerText = currentWordObj.ex_en;
            document.getElementById('exJp').innerText = currentWordObj.ex_jp;
            
            // 出現時に単語を自動再生
            setTimeout(() => speakText(currentWordObj.en), 300);
        }}

        function showAnswer() {{
            document.getElementById('showAnswerBtn').style.display = 'none';
            document.getElementById('answerArea').style.display = 'block';
        }}

        function nextWord(isLearned) {{
            if (isLearned) {{
                if (!progress[currentWordObj.original_rank]) progress[currentWordObj.original_rank] = {{}};
                progress[currentWordObj.original_rank].skipped = true;
                saveProgress();
            }}
            currentIndex++;
            if (currentIndex < playlist.length) {{
                showCurrentCard();
            }} else {{
                alert("終了！");
                location.reload();
            }}
        }}
    </script>
</body>
</html>
"""

components.html(html_code, height=900, scrolling=True)
