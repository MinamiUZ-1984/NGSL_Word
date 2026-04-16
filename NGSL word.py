import streamlit as st
import pandas as pd
import json
import streamlit.components.v1 as components

# --- ページ設定 ---
st.set_page_config(page_title="NGSL 統合マスター", page_icon="🚀", layout="centered")

@st.cache_data
def load_data():
    try:
        try:
            df = pd.read_csv("vocab.csv", encoding="utf-8")
        except UnicodeDecodeError:
            df = pd.read_csv("vocab.csv", encoding="shift_jis")
        df = df.fillna("")
        df['rank'] = pd.to_numeric(df.iloc[:, 0], errors='coerce').fillna(9999).astype(int)
        
        # 【重要】どちらも同じSeed(42)でシャッフルし、MP3と連動させる
        # 作戦A：全単語用（3000語）
        df_all = df.sample(frac=1, random_state=42).reset_index(drop=True)
        
        # 作戦B：700語限定用
        df_700_base = df[df['rank'] <= 700].copy()
        df_700 = df_700_base.sample(frac=1, random_state=42).reset_index(drop=True)
        
        return df_all, df_700
    except Exception as e:
        st.error(f"データ読み込みエラー: {e}")
        return pd.DataFrame(), pd.DataFrame()

df_all, df_700 = load_data()

st.markdown("<h3 style='text-align: center; color: #2c3e50;'>🚀 NGSL 統合マスター</h3>", unsafe_allow_html=True)

# --- メインメニュー ---
course = st.radio(
    "コースを選択してください",
    ["📁 作戦A：全3000語マスター (インプット重視)", "🔥 作戦B：最重要700語特訓 (アウトプット重視)"],
    horizontal=True
)

st.divider()

# --- 各コースの設定 ---
if "作戦A" in course:
    st.subheader("📁 全3000語フラッシュカード")
    target_df = df_all
    chunk_size = 100
    total_tracks = 30
    sub_mode = "単語カード" # Aはカード固定
    st.info("MP3のTrack 01〜30と連動しています。全単語を効率よくインプットしましょう。")
else:
    st.subheader("🔥 最重要700語・徹底特訓")
    target_df = df_700
    chunk_size = 70
    total_tracks = 10
    sub_mode = st.radio("特訓メニュー", ["単語カード", "瞬間英作文"], horizontal=True)
    st.info("日常会話の7割を占める700語を、10トラックで完璧に使いこなせるようにします。")

# トラック選択
selected_track = st.selectbox(f"トラックを選択 (全{total_tracks}回)", range(1, total_tracks + 1), format_func=lambda x: f"Track {x:02d}")

# 表示データの抽出
track_data = target_df.iloc[(selected_track-1)*chunk_size : selected_track*chunk_size]
if sub_mode == "瞬間英作文":
    track_data = track_data[track_data['ex_jp'] != ""]

words_json = json.dumps(track_data.to_dict(orient="records"), ensure_ascii=False).replace("</", "<\\/")

# --- 学習UI (JavaScript) ---
html_code = f"""
<!DOCTYPE html><html><head><style>
    body {{ font-family: sans-serif; text-align: center; padding: 10px; color: #333; }}
    .card-container {{ padding: 25px 15px; border-radius: 15px; background: #fff; box-shadow: 0 4px 10px rgba(0,0,0,0.1); margin-bottom: 20px; }}
    /* コースによって枠の色を変える */
    .border-a {{ border: 3px solid #2ecc71; }}
    .border-b {{ border: 3px solid #e74c3c; }}
    
    .progress {{ font-size: 13px; font-weight: bold; color: #666; margin-bottom: 15px; }}
    .front-text {{ font-size: 28px; font-weight: bold; color: #2c3e50; min-height: 80px; display: flex; align-items: center; justify-content: center; line-height: 1.3; }}
    
    #answerArea {{ display: none; }}
    .back-main {{ font-size: 22px; font-weight: bold; color: #e74c3c; margin: 15px 0; cursor: pointer; }}
    .back-sub {{ font-size: 15px; background: #f8f9fa; padding: 12px; border-radius: 8px; text-align: left; font-style: italic; cursor: pointer; }}
    
    .btn {{ padding: 16px; font-size: 18px; color: white; border: none; border-radius: 10px; width: 100%; max-width: 300px; margin: 10px auto; display: block; font-weight: bold; cursor: pointer; }}
    #showBtn {{ background: #3498db; }}
    
    .judge-box {{ display: flex; gap: 10px; margin-top: 20px; }}
    .judge-btn {{ flex: 1; padding: 15px; border-radius: 10px; color: white; font-weight: bold; border: none; cursor: pointer; }}
</style></head><body>
    <div class="card-container {"border-a" if "作戦A" in course else "border-b"}">
        <div id="progress" class="progress"></div>
        <div id="front" class="front-text"></div>
        
        <button id="showBtn" class="btn" onclick="show()">答えを見る</button>
        
        <div id="answerArea">
            <div id="backMain" class="back-main" onclick="playMain()"></div>
            <div id="backSub" class="back-sub" onclick="playSub()"></div>
            
            <div class="judge-box">
                <button class="judge-btn" style="background:#e67e22" onclick="next(false)">❌ まだ</button>
                <button class="judge-btn" style="background:#2ecc71" onclick="next(true)">✅ 完璧</button>
            </div>
        </div>
    </div>

    <script>
        const words = {words_json};
        const subMode = "{sub_mode}";
        const course = "{course}";
        let idx = 0; let curr = null; const synth = window.speechSynthesis;
        
        // 保存キーをコース・モード別に分ける
        const storageKey = course.includes("作戦A") ? "ngsl_a_full" : (subMode === "単語カード" ? "ngsl_b_card" : "ngsl_b_speak");
        let prog = JSON.parse(localStorage.getItem(storageKey) || "{{}}");

        function speak(t) {{ if(!t)return; synth.cancel(); const u = new SpeechSynthesisUtterance(t); u.lang='en-US'; u.rate=0.9; synth.speak(u); }}
        
        function loadCard() {{
            while(idx < words.length && prog[words[idx].rank]) idx++;
            if(idx >= words.length) {{ alert("このトラックは完了です！"); location.reload(); return; }}
            
            curr = words[idx];
            document.getElementById('progress').innerText = (idx+1) + " / " + words.length + " (Rank: " + curr.rank + ")";
            
            if(subMode === "単語カード") {{
                document.getElementById('front').innerText = curr.en;
                document.getElementById('backMain').innerText = curr.jp;
                document.getElementById('backSub').innerHTML = "例文: " + curr.ex_en + "<br><small>" + curr.ex_jp + "</small>";
                speak(curr.en);
            }} else {{
                document.getElementById('front').innerText = curr.ex_jp;
                document.getElementById('backMain').innerText = curr.ex_en;
                document.getElementById('backSub').innerText = "単語: " + curr.en + " (" + curr.jp + ")";
            }}
            document.getElementById('answerArea').style.display = 'none';
            document.getElementById('showBtn').style.display = 'block';
        }}

        function show() {{
            document.getElementById('showBtn').style.display = 'none';
            document.getElementById('answerArea').style.display = 'block';
            if(subMode === "瞬間英作文") speak(curr.ex_en);
        }}

        function playMain() {{ speak(subMode === "単語カード" ? curr.en : curr.ex_en); }}
        function playSub() {{ speak(curr.ex_en); }}

        function next(learned) {{
            if(learned) {{ prog[curr.rank] = true; localStorage.setItem(storageKey, JSON.stringify(prog)); }}
            idx++; loadCard();
        }}
        loadCard();
    </script>
</body></html>
"""
components.html(html_code, height=650, scrolling=True)

st.caption("💡 **ヒント**")
st.caption("・作戦A：全3000語をMP3で聞き流し、アプリで意味を素早くチェック。")
st.caption("・作戦B：700語に集中。単語が分かったら『瞬間英作文』で口を鍛える。")
