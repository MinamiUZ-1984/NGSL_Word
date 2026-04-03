import streamlit as st
import pandas as pd
import json
import streamlit.components.v1 as components

# --- ページ設定 ---
st.set_page_config(page_title="NGSL マスターアプリ", page_icon="🚀", layout="centered")

st.markdown("<div style='padding-top: 10px;'><h3 style='text-align: center;'>🚀 NGSL マスターアプリ</h3></div>", unsafe_allow_html=True)

# --- データ読み込み ---
@st.cache_data
def load_base_data():
    try:
        try:
            df = pd.read_csv("vocab.csv", encoding="utf-8")
        except UnicodeDecodeError:
            df = pd.read_csv("vocab.csv", encoding="shift_jis")
        
        df = df.fillna("")
        new_df = pd.DataFrame()
        cols_count = df.shape[1]
        
        new_df['original_rank'] = pd.to_numeric(df.iloc[:, 0], errors='coerce').fillna(0).astype(int)
        new_df['en'] = df.iloc[:, 1] if cols_count > 1 else ""
        new_df['jp'] = df.iloc[:, 2] if cols_count > 2 else ""      
        new_df['ex_en'] = df.iloc[:, 4] if cols_count > 4 else ""   
        new_df['ex_jp'] = df.iloc[:, 5] if cols_count > 5 else ""   
        
        return new_df
    except Exception as e:
        st.error(f"CSVの読み込みに失敗しました: {e}")
        return pd.DataFrame()

base_df = load_base_data()

if base_df.empty:
    st.warning("単語データを読み込めません。vocab.csv を確認してください。")
    st.stop()

# ==========================================
# 🏠 ホーム画面（モード選択）
# ==========================================
st.markdown("##### 🎯 学習メニューを選択")
app_mode = st.radio(
    "",
    ["🔤 作戦A：フラッシュカード (全単語・MP3連動)", "🗣️ 作戦B：瞬間英作文 (上位700語・基礎固め)"],
    label_visibility="collapsed"
)
st.divider()

# ==========================================
# モードA：全単語フラッシュカード (V02ベース)
# ==========================================
if "作戦A" in app_mode:
    # MP3と完全に順番を合わせるため「42」でシャッフル
    df_a = base_df.sample(frac=1, random_state=42).reset_index(drop=True)
    
    chunk_size = 100
    total_tracks = (len(df_a) // chunk_size) + (1 if len(df_a) % chunk_size != 0 else 0)

    st.write("▼ MP3のトラック番号に合わせて選択")
    selected_track = st.selectbox("トラック番号", range(1, total_tracks + 1), format_func=lambda x: f"Track {x:02d}")

    start_idx = (selected_track - 1) * chunk_size
    end_idx = start_idx + chunk_size
    track_df = df_a.iloc[start_idx:end_idx]

    st.info(f"🎧 **Track {selected_track:02d}** の単語カードです。\n\n英語を見て、日本語の意味がフワッと分かれば「✅覚えた」でOK！")

    words_json = json.dumps(track_df.to_dict(orient="records"), ensure_ascii=False).replace("</", "<\\/")

    html_code_a = f"""
    <!DOCTYPE html><html><head><style>
        body {{ font-family: sans-serif; text-align: center; margin: 0; padding: 10px; color: #333; }}
        .card-container {{ padding: 20px 15px; border: 2px solid #2ecc71; border-radius: 12px; background-color: #f9fff9; margin: 0 auto; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }}
        .progress-text {{ font-size: 14px; font-weight: bold; color: #666; background-color: #e0f2fe; display: inline-block; padding: 8px 16px; border-radius: 16px; margin-bottom: 20px; }}
        .en-word {{ font-size: 32px; font-weight: bold; color: #2c3e50; margin-bottom: 15px; cursor: pointer; }}
        #answerArea {{ display: none; }}
        .jp-word {{ font-size: 22px; font-weight: bold; color: #e74c3c; margin-bottom: 10px; }}
        hr {{ margin: 15px 0; border: none; border-top: 1px dashed #ccc; }}
        .ex-container {{ background-color: #f0f4f8; padding: 10px; border-radius: 8px; cursor: pointer; text-align: left; }}
        .ex-en {{ font-size: 16px; color: #2c3e50; margin-bottom: 5px; font-style: italic; line-height: 1.4; }}
        .ex-jp {{ font-size: 13px; color: #777; line-height: 1.3; }}
        .btn {{ padding: 16px; font-size: 18px; color: white; border: none; border-radius: 8px; cursor: pointer; font-weight: bold; width: 100%; max-width: 320px; margin: 10px auto; display: block; }}
        #showAnswerBtn {{ background-color: #3498db; margin-top: 25px; }}
        .judge-container {{ display: flex; justify-content: center; gap: 15px; margin-top: 25px; }}
        .judge-btn {{ padding: 16px 10px; font-size: 18px; color: white; border: none; border-radius: 8px; cursor: pointer; font-weight: bold; flex: 1; max-width: 150px; }}
        #learnedBtn {{ background-color: #2ecc71; }}
        #learningBtn {{ background-color: #e67e22; }}
    </style></head><body>
        <script type="application/json" id="wordsData">{words_json}</script>
        <button id="startBtn" class="btn" style="background-color: #1E90FF;" onclick="startTest()">▶️ 単語テストを開始</button>
        <div id="displayArea" class="card-container" style="display: none;">
            <div id="progressDisplay" class="progress-text"></div>
            <div id="enWord" class="en-word" onclick="speakText(currentWordObj.en)"></div>
            <button id="showAnswerBtn" class="btn" onclick="showAnswer()">👀 答えを見る</button>
            <div id="answerArea">
                <div id="jpWord" class="jp-word"></div><hr>
                <div class="ex-container" onclick="speakText(currentWordObj.ex_en)">
                    <div id="exEn" class="ex-en"></div><div id="exJp" class="ex-jp"></div>
                </div>
                <div class="judge-container">
                    <button id="learningBtn" class="judge-btn" onclick="nextWord(false)">❌ まだ</button>
                    <button id="learnedBtn" class="judge-btn" onclick="nextWord(true)">✅ 覚えた</button>
                </div>
            </div>
        </div>
        <script>
            let playlist = []; let currentIndex = 0; let currentWordObj = null; const synth = window.speechSynthesis;
            const allWords = JSON.parse(document.getElementById('wordsData').textContent);
            let progress = JSON.parse(localStorage.getItem('ngsl_flashcard') || "{{}}");
            function saveProgress() {{ localStorage.setItem('ngsl_flashcard', JSON.stringify(progress)); }}
            function speakText(text) {{ if(!text) return; synth.cancel(); const u = new SpeechSynthesisUtterance(text); u.lang = 'en-US'; synth.speak(u); }}
            function startTest() {{
                playlist = allWords.filter(w => !progress[w.original_rank]?.skipped);
                if (playlist.length === 0) {{ alert("完璧です！すべて覚えています！"); return; }}
                currentIndex = 0; document.getElementById('startBtn').style.display = 'none'; document.getElementById('displayArea').style.display = 'block'; showCard();
            }}
            function showCard() {{
                currentWordObj = playlist[currentIndex];
                document.getElementById('progressDisplay').innerText = `残り ${{playlist.length - currentIndex}} 語 / ${{playlist.length}}`;
                document.getElementById('enWord').innerText = currentWordObj.en;
                document.getElementById('answerArea').style.display = 'none'; document.getElementById('showAnswerBtn').style.display = 'block';
                document.getElementById('jpWord').innerText = currentWordObj.jp;
                document.getElementById('exEn').innerText = currentWordObj.ex_en; document.getElementById('exJp').innerText = currentWordObj.ex_jp;
                setTimeout(() => speakText(currentWordObj.en), 300);
            }}
            function showAnswer() {{ document.getElementById('showAnswerBtn').style.display = 'none'; document.getElementById('answerArea').style.display = 'block'; }}
            function nextWord(isLearned) {{
                if (isLearned) {{ if (!progress[currentWordObj.original_rank]) progress[currentWordObj.original_rank] = {{}}; progress[currentWordObj.original_rank].skipped = true; saveProgress(); }}
                currentIndex++; if (currentIndex < playlist.length) {{ showCard(); }} else {{ alert("終了！"); location.reload(); }}
            }}
        </script>
    </body></html>
    """
    components.html(html_code_a, height=800, scrolling=True)


# ==========================================
# モードB：瞬間英作文 (上位700語)
# ==========================================
elif "作戦B" in app_mode:
    # ランク1〜700位に絞り、ランク順に並べる
    df_b = base_df[(base_df['original_rank'] > 0) & (base_df['original_rank'] <= 700)]
    df_b = df_b.sort_values('original_rank').reset_index(drop=True)
    
    # 例文がないものは除外
    df_b = df_b[df_b['ex_jp'] != ""]

    st.write("▼ 学習するランク帯を選択")
    blocks = ["1-100位", "101-200位", "201-300位", "301-400位", "401-500位", "501-600位", "601-700位"]
    selected_block = st.selectbox("学習範囲", blocks)

    start_r = int(selected_block.split('-')[0])
    end_r = int(selected_block.split('-')[1].replace('位',''))

    block_df = df_b[(df_b['original_rank'] >= start_r) & (df_b['original_rank'] <= end_r)]

    st.info("🗣️ **瞬間英作文トレーニング**\n\n日本語を見たら、とにかく3秒以内に英語を口に出してみましょう。（間違えてもOK！）")

    words_json_b = json.dumps(block_df.to_dict(orient="records"), ensure_ascii=False).replace("</", "<\\/")

    html_code_b = f"""
    <!DOCTYPE html><html><head><style>
        body {{ font-family: sans-serif; text-align: center; margin: 0; padding: 10px; color: #333; }}
        .card-container {{ padding: 20px 15px; border: 2px solid #e74c3c; border-radius: 12px; background-color: #fff9f9; margin: 0 auto; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }}
        .progress-text {{ font-size: 14px; font-weight: bold; color: #fff; background-color: #e74c3c; display: inline-block; padding: 8px 16px; border-radius: 16px; margin-bottom: 20px; }}
        .ex-jp-front {{ font-size: 24px; font-weight: bold; color: #2c3e50; margin-bottom: 20px; line-height: 1.4; text-align: left; padding: 10px; }}
        #answerArea {{ display: none; }}
        hr {{ margin: 15px 0; border: none; border-top: 1px dashed #ccc; }}
        .ex-en-back {{ font-size: 22px; font-weight: bold; color: #1E90FF; margin-bottom: 15px; line-height: 1.4; text-align: left; padding: 10px; cursor: pointer; background-color: #f0f8ff; border-radius: 8px; }}
        .hint-word {{ font-size: 16px; color: #7f8c8d; text-align: left; padding-left: 10px; font-style: italic; }}
        .btn {{ padding: 16px; font-size: 18px; color: white; border: none; border-radius: 8px; cursor: pointer; font-weight: bold; width: 100%; max-width: 320px; margin: 10px auto; display: block; }}
        #showAnswerBtn {{ background-color: #e74c3c; margin-top: 25px; }}
        .judge-container {{ display: flex; justify-content: center; gap: 15px; margin-top: 25px; }}
        .judge-btn {{ padding: 16px 10px; font-size: 18px; color: white; border: none; border-radius: 8px; cursor: pointer; font-weight: bold; flex: 1; max-width: 150px; }}
        #learnedBtn {{ background-color: #2ecc71; }}
        #learningBtn {{ background-color: #e67e22; }}
    </style></head><body>
        <script type="application/json" id="wordsData">{words_json_b}</script>
        <button id="startBtn" class="btn" style="background-color: #e74c3c;" onclick="startTest()">▶️ 英作文を開始</button>
        <div id="displayArea" class="card-container" style="display: none;">
            <div id="progressDisplay" class="progress-text"></div>
            <div id="exJpFront" class="ex-jp-front"></div>
            <button id="showAnswerBtn" class="btn" onclick="showAnswer()">👀 英語の正解を見る</button>
            <div id="answerArea">
                <hr>
                <div id="exEnBack" class="ex-en-back" onclick="speakText(currentWordObj.ex_en)"></div>
                <div id="hintWord" class="hint-word"></div>
                <div class="judge-container">
                    <button id="learningBtn" class="judge-btn" onclick="nextWord(false)">❌ 言えなかった</button>
                    <button id="learnedBtn" class="judge-btn" onclick="nextWord(true)">✅ 完璧に言えた</button>
                </div>
            </div>
        </div>
        <script>
            let playlist = []; let currentIndex = 0; let currentWordObj = null; const synth = window.speechSynthesis;
            const allWords = JSON.parse(document.getElementById('wordsData').textContent);
            
            // フラッシュカードとは別の保存領域を使用します
            let progress = JSON.parse(localStorage.getItem('ngsl_speaking700') || "{{}}");
            function saveProgress() {{ localStorage.setItem('ngsl_speaking700', JSON.stringify(progress)); }}
            function speakText(text) {{ if(!text) return; synth.cancel(); const u = new SpeechSynthesisUtterance(text); u.lang = 'en-US'; u.rate = 0.9; synth.speak(u); }}
            function startTest() {{
                playlist = allWords.filter(w => !progress[w.original_rank]?.skipped);
                if (playlist.length === 0) {{ alert("この範囲の英作文は完璧です！"); return; }}
                currentIndex = 0; document.getElementById('startBtn').style.display = 'none'; document.getElementById('displayArea').style.display = 'block'; showCard();
            }}
            function showCard() {{
                currentWordObj = playlist[currentIndex];
                document.getElementById('progressDisplay').innerText = `残り ${{playlist.length - currentIndex}} 文 / ${{playlist.length}} (Rank: ${{currentWordObj.original_rank}})`;
                document.getElementById('exJpFront').innerText = currentWordObj.ex_jp;
                document.getElementById('answerArea').style.display = 'none'; document.getElementById('showAnswerBtn').style.display = 'block';
                document.getElementById('exEnBack').innerText = currentWordObj.ex_en;
                document.getElementById('hintWord').innerText = "💡 Target: " + currentWordObj.en + " (" + currentWordObj.jp + ")";
            }}
            function showAnswer() {{ document.getElementById('showAnswerBtn').style.display = 'none'; document.getElementById('answerArea').style.display = 'block'; speakText(currentWordObj.ex_en); }}
            function nextWord(isLearned) {{
                if (isLearned) {{ if (!progress[currentWordObj.original_rank]) progress[currentWordObj.original_rank] = {{}}; progress[currentWordObj.original_rank].skipped = true; saveProgress(); }}
                currentIndex++; if (currentIndex < playlist.length) {{ showCard(); }} else {{ alert("終了！"); location.reload(); }}
            }}
        </script>
    </body></html>
    """
    components.html(html_code_b, height=800, scrolling=True)
