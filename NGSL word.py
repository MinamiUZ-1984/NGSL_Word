import streamlit as st
import pandas as pd
import json
import streamlit.components.v1 as components

st.set_page_config(page_title="NGSL 黄金の700語", page_icon="🔰", layout="centered")

st.markdown("<div style='padding-top: 20px;'><h3 style='text-align: center;'>🔰 超基礎：黄金の700語マスター</h3></div>", unsafe_allow_html=True)

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
        
        # ランク、英語、日本語のみ抽出
        new_df['original_rank'] = pd.to_numeric(df.iloc[:, 0], errors='coerce').fillna(0).astype(int)
        new_df['en'] = df.iloc[:, 1]
        new_df['jp'] = df.iloc[:, 2]
        
        # ★【重要】上位700語だけに絞り込む！
        new_df = new_df[new_df['original_rank'] <= 700]
        
        # ランク順に並べる（まずは順番に覚えるため）
        new_df = new_df.sort_values('original_rank')
        return new_df
    except Exception as e:
        st.error(f"データの読み込み失敗: {e}")
        return pd.DataFrame()

df = load_data()

st.divider()

if df.empty:
    st.warning("データが見つかりません。")
else:
    # 100語ずつのブロック選択
    block_option = st.selectbox("学習範囲を選択", ["1-100位", "101-200位", "201-300位", "301-400位", "401-500位", "501-600位", "601-700位"])
    start_r = int(block_option.split('-')[0])
    end_r = int(block_option.split('-')[1].replace('位',''))
    
    current_df = df[(df['original_rank'] >= start_r) & (df['original_rank'] <= end_r)]
    
    st.info(f"✨ **最重要単語 {block_option}** の学習です。\n\n「英語を見て日本語を言う」→「日本語を見て英語を言う」の順で、まずは単語を反射的に言えるようにしましょう。")

    words_json = json.dumps(current_df.to_dict(orient="records"), ensure_ascii=False)

    html_code = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {{ font-family: sans-serif; text-align: center; padding: 10px; color: #333; }}
            .card {{ padding: 30px 20px; border: 3px solid #3498db; border-radius: 15px; background-color: #fff; margin-bottom: 20px; box-shadow: 0 4px 10px rgba(0,0,0,0.1); }}
            .rank {{ font-size: 14px; color: #3498db; font-weight: bold; }}
            .word-en {{ font-size: 40px; font-weight: bold; margin: 15px 0; color: #2c3e50; }}
            .word-jp {{ font-size: 26px; font-weight: bold; color: #e67e22; display: none; margin-top: 20px; }}
            .btn {{ padding: 15px; width: 100%; max-width: 300px; font-size: 18px; border-radius: 10px; border: none; color: white; cursor: pointer; margin: 10px 0; font-weight: bold; }}
            #showBtn {{ background-color: #3498db; }}
            .judge-btn {{ background-color: #2ecc71; }}
            .next-btn {{ background-color: #95a5a6; }}
        </style>
    </head>
    <body>
        <div id="card" class="card">
            <div id="rank" class="rank"></div>
            <div id="en" class="word-en"></div>
            <div id="jp" class="word-jp"></div>
        </div>
        <button id="showBtn" class="btn" onclick="showAnswer()">答えを見る</button>
        <div id="nextArea" style="display:none;">
            <button class="btn judge-btn" onclick="nextWord()">次へ進む</button>
        </div>

        <script>
            const words = {words_json};
            let idx = 0;
            const synth = window.speechSynthesis;

            function showWord() {{
                const item = words[idx];
                document.getElementById('rank').innerText = "NGSL Rank: " + item.original_rank;
                document.getElementById('en').innerText = item.en;
                document.getElementById('jp').innerText = item.jp;
                document.getElementById('jp').style.display = 'none';
                document.getElementById('showBtn').style.display = 'block';
                document.getElementById('nextArea').style.display = 'none';
                
                // 音声を再生
                const u = new SpeechSynthesisUtterance(item.en);
                u.lang = 'en-US';
                synth.speak(u);
            }}

            function showAnswer() {{
                document.getElementById('jp').style.display = 'block';
                document.getElementById('showBtn').style.display = 'none';
                document.getElementById('nextArea').style.display = 'block';
            }}

            function nextWord() {{
                idx++;
                if (idx < words.length) {{
                    showWord();
                }} else {{
                    alert("このブロックは完了です！");
                    location.reload();
                }}
            }}
            showWord();
        </script>
    </body>
    </html>
    """
    components.html(html_code, height=500)
