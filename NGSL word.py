import streamlit as st
import pandas as pd
import json
import streamlit.components.v1 as components

# --- ページ設定 ---
st.set_page_config(page_title="NGSL テスト＆管理", page_icon="📝", layout="centered")

st.markdown("""
    <style>
        .block-container { padding-top: 1.5rem; padding-bottom: 1rem; }
    </style>
""", unsafe_allow_html=True)


# --- データ読み込み＆Colabと完全に同じシャッフル ---
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
        
        # 本来のランク（ID）を保持
        new_df['original_rank'] = df.iloc[:, 0] if cols_count > 0 else range(1, len(df) + 1)
        new_df['en'] = df.iloc[:, 1] if cols_count > 1 else ""
        new_df['jp'] = df.iloc[:, 2] if cols_count > 2 else ""      
        new_df['ex_en'] = df.iloc[:, 4] if cols_count > 4 else ""   
        new_df['ex_jp'] = df.iloc[:, 5] if cols_count > 5 else ""   
        
        new_df['original_rank'] = pd.to_numeric(new_df['original_rank'], errors='coerce').fillna(0).astype(int)
        
        # ★超重要：ColabのMP3作成時と全く同じ「42」というシード値でシャッフルする
        new_df = new_df.sample(frac=1, random_state=42).reset_index(drop=True)
        
        return new_df
    except Exception as e:
        st.error(f"CSVの読み込みに失敗しました: {e}")
        return pd.DataFrame()

df = load_data()


# --- メイン画面UI ---
st.markdown("<h3 style='text-align: center; margin-bottom: 0;'>📝 NGSL 単語テスト＆管理</h3>", unsafe_allow_html=True)

if df.empty:
    st.warning("単語データを読み込めません。vocab.csv がアップロードされているか確認してください。")
    st.stop()

# --- 🎯 トラック選択 ---
st.divider()
chunk_size = 100
total_tracks = (len(df) // chunk_size) + (1 if len(df) % chunk_size != 0 else 0)

st.write("▼ 学習するトラック（MP3の番号）を選択")
selected_track = st.selectbox("トラック番号", range(1, total_tracks + 1), format_func=lambda x: f"Track {x:02d}")

# 選択したトラックの100語を抽出
start_idx = (selected_track - 1) * chunk_size
end_idx = start_idx + chunk_size
track_df = df.iloc[start_idx:end_idx]

st.info(f"🎧 **Track {selected_track:02d}** のプレテスト / 復習を行います。\n\n※すでに「覚えた」にチェックした単語は自動でスキップされます。")

words_json = json.dumps(track_df.to_dict(orient="records"))

# --- フラッシュカードUI用のHTML/JavaScript ---
html_code = f"""
<!DOCTYPE html>
<html>
<head>
    <style>
        body {{ font-family: sans-serif; text-align: center; margin: 0; padding: 0; color: #333; }}
        .card-container {{ padding: 20px; border: 2px solid #2ecc71; border-radius: 12px; background-color: #f9fff9; max-width: 100%; margin: 15px auto; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }}
        
        .progress-text {{ font-size: 16px; font-weight: bold; color: #666; background-color: #e0f2fe; display: inline-block; padding: 6px 16px; border-radius: 16px; margin-bottom: 15px; }}
        
        .en-word {{ font-size: 36px; font-weight: bold; color: #2c3e50; margin-bottom: 15px; }}
        
        /* 答えエリア（初期は非表示） */
        #answerArea {{ display: none; }}
        .jp-word {{ font-size: 24px; font-weight: bold; color: #e74c3c; margin-bottom: 15px; }}
        hr {{ margin: 15px 0; border: none; border-top: 1px dashed #ccc; }}
        .ex-en {{ font-size: 16px; color: #555; margin-bottom: 5px; font-style: italic; }}
        .ex-jp {{ font-size: 14px; color: #888; }}
        
        .btn {{ padding: 14px 20px; font-size: 18px; color: white; border: none; border-radius: 8px; cursor: pointer; font-weight: bold; width: 90%; max-width: 320px; margin: 8px auto; display: block; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }}
        
        #showAnswerBtn {{ background-color: #3498db; }}
        #showAnswerBtn:hover {{ background-color: #2980b9; }}
        
        #speakBtn {{ background-color: #9b59b6; padding: 10px 15px; font-size: 14px; width: auto; display: inline-block; margin-bottom: 15px; }}
        
        .judge-container {{ display: flex; justify-content: center; gap: 10px; margin-top: 20px; }}
        .judge-btn {{ padding: 14px 10px; font-size: 16px; color: white; border: none; border-radius: 8px; cursor: pointer; font-weight: bold; flex: 1; max-width: 150px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }}
        #learnedBtn {{ background-color: #2ecc71; }}
        #learnedBtn:hover {{ background-color: #27ae60; }}
        #learningBtn {{ background-color: #e67e22; }}
        #learningBtn:hover {{ background-color: #d35400; }}
        
        #resetBtn {{ background-color: #95a5a6; font-size: 14px; padding: 10px 20px; width: auto; margin-top: 40px; }}
    </style>
</head>
<body>

    <button id="startBtn" class="btn" style="background-color: #1E90FF;" onclick="startTest()">▶️ テストを開始する</button>

    <div id="displayArea" class="card-container" style="display: none;">
        <div id="progressDisplay" class="progress-text"></div>
        
        <div id="enWord" class="en-word"></div>
        <button id="speakBtn" class="btn" onclick="speakWord()">🔊 発音を聞く</button>
        
        <button id="showAnswerBtn" class="btn" onclick="showAnswer()">👀 答えを見る</button>

        <div id="answerArea">
            <div id="jpWord" class="jp-word"></div>
            <hr>
            <div id="exEn" class="ex-en"></div>
            <div id="exJp" class="ex-jp"></div>
            
            <div class="judge-container">
                <button id="learningBtn" class="judge-btn" onclick="nextWord(false)">❌ まだ</button>
                <button id="learnedBtn" class="judge-btn" onclick="nextWord(true)">✅ 覚えた</button>
            </div>
        </div>
    </div>

    <button id="resetBtn" class="btn" onclick="resetProgress()">🔄 全記録をリセット</button>

    <script>
        const allWords = {words_json}; 
        let playlist = [];
        let currentIndex = 0;
        let currentWordObj = null;
        const synth = window.speechSynthesis;

        // V01の記録を引き継ぎます
        let progress = JSON.parse(localStorage.getItem('ngsl_progress')) || {{}};

        function getProgress(rank) {{
            if (!progress[rank]) {{ progress[rank] = {{ playCount: 0, skipped: false }}; }}
            return progress[rank];
        }}

        function saveProgress() {{
            localStorage.setItem('ngsl_progress', JSON.stringify(progress));
        }}

        function resetProgress() {{
            if (confirm("すべての学習記録（覚えた単語）をリセットしますか？")) {{
                localStorage.removeItem('ngsl_progress');
                progress = {{}};
                alert("リセットしました！");
            }}
        }}

        function speakWord() {{
            if (!currentWordObj || !currentWordObj.en) return;
            synth.cancel();
            const utterance = new SpeechSynthesisUtterance(currentWordObj.en);
            utterance.lang = 'en-US';
            synth.speak(utterance);
        }}

        function startTest() {{
            // まだ覚えていない単語だけを抽出
            playlist = allWords.filter(w => !getProgress(w.original_rank).skipped);
            
            if (playlist.length === 0) {{
                alert("🎉 このトラックの単語はすべて「覚えた」になっています！完璧です！");
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
            
            document.getElementById('progressDisplay').innerText = `残り ${{playlist.length - currentIndex}} 語 / 全 ${{playlist.length}} 語`;
            document.getElementById('enWord').innerText = currentWordObj.en;
            
            // 答えを隠す
            document.getElementById('answerArea').style.display = 'none';
            document.getElementById('showAnswerBtn').style.display = 'block';
            
            // 答えのテキストをセットしておく
            document.getElementById('jpWord').innerText = currentWordObj.jp || "";
            document.getElementById('exEn').innerText = currentWordObj.ex_en || "";
            document.getElementById('exJp').innerText = currentWordObj.ex_jp || "";
        }}

        function showAnswer() {{
            document.getElementById('showAnswerBtn').style.display = 'none';
            document.getElementById('answerArea').style.display = 'block';
        }}

        function nextWord(isLearned) {{
            if (isLearned) {{
                progress[currentWordObj.original_rank].skipped = true;
                saveProgress();
            }}
            
            currentIndex++;
            
            if (currentIndex < playlist.length) {{
                showCurrentCard();
            }} else {{
                alert("🏁 このトラックの今回のテストが終了しました！\nお疲れ様でした！");
                document.getElementById('displayArea').style.display = 'none';
                document.getElementById('startBtn').style.display = 'block';
                document.getElementById('startBtn').innerText = '🔄 もう一度テストする';
                document.getElementById('resetBtn').style.display = 'block';
            }}
        }}
    </script>
</body>
</html>
"""

components.html(html_code, height=650, scrolling=True)

st.caption("💡 **使い方**")
st.caption("1. MP3を聞き流す前（または後）に、同じTrackのテストを行います。")
st.caption("2. 英語を見て意味を思い浮かべ、「答えを見る」を押します。")
st.caption("3. 完璧にわかったら「✅ 覚えた」、怪しければ「❌ まだ」を押します。")
st.caption("※「覚えた」単語は次回から出題されなくなります！")
