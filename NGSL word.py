import streamlit as st
import pandas as pd
import json
import streamlit.components.v1 as components

# --- ページ設定 ---
st.set_page_config(page_title="NGSL 聞き流しアプリ", layout="centered")

st.markdown("""
    <style>
        .block-container { padding-top: 1.5rem; padding-bottom: 1rem; }
        div.stButton > button { margin-bottom: -10px; }
    </style>
""", unsafe_allow_html=True)


# --- データ読み込み ---
@st.cache_data
def load_data():
    try:
        try:
            df = pd.read_csv("vocab.csv", encoding="utf-8")
        except UnicodeDecodeError:
            df = pd.read_csv("vocab.csv", encoding="shift_jis")
        
        df = df.fillna("")
        
        # ★修正ポイント1：見出しの文字に依存せず、「列の場所（A列、B列…）」で強制的にデータを取得します。
        # A列(0): 番号, B列(1): 英単語, C列(2): 意味, D列(3): 品詞(無視), E列(4): 例文, F列(5): 例文訳
        new_df = pd.DataFrame()
        cols_count = df.shape[1]
        
        new_df['rank'] = df.iloc[:, 0] if cols_count > 0 else range(1, len(df) + 1)
        new_df['en'] = df.iloc[:, 1] if cols_count > 1 else ""
        new_df['jp'] = df.iloc[:, 2] if cols_count > 2 else ""      # C列を強制的に日本語訳に
        new_df['ex_en'] = df.iloc[:, 4] if cols_count > 4 else ""   # E列を強制的に例文に
        new_df['ex_jp'] = df.iloc[:, 5] if cols_count > 5 else ""   # F列を強制的に例文訳に
        
        # 番号列を数値に変換（エラー行は除外）
        new_df['rank'] = pd.to_numeric(new_df['rank'], errors='coerce').fillna(0).astype(int)
        
        return new_df
    except Exception as e:
        st.error(f"CSVの読み込みに失敗しました: {e}")
        return pd.DataFrame()

df = load_data()


# --- メイン画面UI ---
st.markdown("<h3 style='text-align: center; margin-bottom: 0;'>🎧 NGSL 聞き流し学習</h3>", unsafe_allow_html=True)

if df.empty:
    st.warning("単語データを読み込めません。vocab.csv がアップロードされているか確認してください。")
    st.stop()

# --- 🎯 範囲指定とランダム化の設定 ---
st.divider()
min_rank = int(df['rank'].min()) if not df.empty and int(df['rank'].min()) > 0 else 1
max_rank = int(df['rank'].max()) if not df.empty else 3000

st.write("▼ 出題範囲を設定（頻度順位）")
selected_range = st.slider(
    "出題する番号の範囲を選んでください",
    min_value=min_rank, 
    max_value=max_rank, 
    value=(min_rank, min(min_rank + 99, max_rank)), 
    label_visibility="collapsed"
)

filtered_df = df[(df['rank'] >= selected_range[0]) & (df['rank'] <= selected_range[1])]
filtered_df = filtered_df.sample(frac=1).reset_index(drop=True)

st.info(f"📚 **{selected_range[0]} 〜 {selected_range[1]}** 番の単語から、**{len(filtered_df)}語** をランダムに出題します。")

words_json = json.dumps(filtered_df.to_dict(orient="records"))

# --- 音声再生＆UI同期用のHTML/JavaScript ---
html_code = f"""
<!DOCTYPE html>
<html>
<head>
    <style>
        body {{ font-family: sans-serif; text-align: center; margin: 0; padding: 0; color: #333; }}
        .word-container {{ padding: 10px; border: 2px solid #1E90FF; border-radius: 8px; background-color: #f0f8ff; max-width: 100%; margin: 5px auto; }}
        .en-word {{ font-size: 32px; font-weight: bold; color: #1E90FF; margin-bottom: 5px; }}
        .jp-word {{ font-size: 22px; color: #e74c3c; margin-bottom: 10px; min-height: 28px; display: none; }}
        hr {{ margin: 10px 0; border: none; border-top: 1px solid #ccc; }}
        .ex-en {{ font-size: 16px; color: #555; margin-bottom: 5px; min-height: 22px; }}
        .ex-jp {{ font-size: 14px; color: #888; display: none; }}
        button {{ padding: 12px 24px; font-size: 16px; background-color: #1E90FF; color: white; border: none; border-radius: 5px; cursor: pointer; font-weight: bold; width: 80%; max-width: 300px; margin-top: 10px; }}
        button:hover {{ background-color: #0066cc; }}
        #stopBtn {{ background-color: #e74c3c; }}
        #stopBtn:hover {{ background-color: #c0392b; }}
    </style>
</head>
<body>

    <button id="startBtn" onclick="startLearning()">▶️ ランダム再生スタート</button>
    <button id="stopBtn" onclick="stopLearning()" style="display: none;">⏹ 停止</button>

    <div id="displayArea" class="word-container" style="display: none;">
        <div id="enWord" class="en-word"></div>
        <div id="jpWord" class="jp-word"></div>
        <hr>
        <div id="exEn" class="ex-en"></div>
        <div id="exJp" class="ex-jp"></div>
    </div>

    <script>
        const words = {words_json}; 
        let currentIndex = 0;
        let isPlaying = false;
        const synth = window.speechSynthesis;

        // ★修正ポイント2：OSやブラウザごとに異なる「日本語音声」の内部名をあらゆるパターンで網羅してキャッチします。
        function getVoice(lang) {{
            const voices = synth.getVoices();
            if (lang === 'ja-JP') {{
                return voices.find(v => v.lang === 'ja-JP' || v.lang === 'ja_JP' || v.lang === 'ja') 
                    || voices.find(v => v.name.includes('日本語') || v.name.includes('Japanese'));
            }} else {{
                return voices.find(v => v.lang.includes('en') && v.lang.includes('US')) 
                    || voices.find(v => v.lang.includes('en'));
            }}
        }}

        function speak(text, lang, rate=0.9) {{
            return new Promise((resolve) => {{
                if (!isPlaying || !text || text.trim() === "") return resolve(); 
                
                const utterance = new SpeechSynthesisUtterance(text);
                utterance.lang = lang; // 言語を強制
                
                const voice = getVoice(lang);
                if (voice) {{
                    utterance.voice = voice;
                }}
                
                utterance.rate = rate; 
                utterance.onend = () => {{ setTimeout(resolve, 400); }}; 
                utterance.onerror = () => {{ setTimeout(resolve, 400); }}; // エラーでも止まらないように
                
                synth.speak(utterance);
            }});
        }}

        async function playWordSequence(wordObj) {{
            document.getElementById('enWord').innerText = wordObj.en || "";
            document.getElementById('jpWord').style.display = 'none';
            document.getElementById('jpWord').innerText = wordObj.jp || "";
            document.getElementById('exEn').style.display = 'none';
            document.getElementById('exEn').innerText = wordObj.ex_en || "";
            document.getElementById('exJp').style.display = 'none';
            document.getElementById('exJp').innerText = wordObj.ex_jp || "";

            // 1. 英 (B列)
            await speak(wordObj.en, 'en-US');
            
            // 2. 英 (B列)
            await speak(wordObj.en, 'en-US');
            
            // 3. 日 (C列)
            if (!isPlaying) return;
            if (wordObj.jp && wordObj.jp.trim() !== "") {{
                document.getElementById('jpWord').style.display = 'block';
                await speak(wordObj.jp, 'ja-JP', 1.1);
            }}

            // 4. 英 (B列)
            if (!isPlaying) return;
            await speak(wordObj.en, 'en-US');

            // 5. 例文英 (E列)
            if (!isPlaying) return;
            if (wordObj.ex_en && wordObj.ex_en.trim() !== "") {{
                document.getElementById('exEn').style.display = 'block';
                await speak(wordObj.ex_en, 'en-US');
            }}

            // 6. 例文日 (F列)
            if (!isPlaying) return;
            if (wordObj.ex_jp && wordObj.ex_jp.trim() !== "") {{
                document.getElementById('exJp').style.display = 'block';
                await speak(wordObj.ex_jp, 'ja-JP', 1.1);
            }}
            
            // 7. 英 (B列)
            if (!isPlaying) return;
            await speak(wordObj.en, 'en-US');
        }}

        async function startLearning() {{
            if (words.length === 0) return;
            isPlaying = true;
            document.getElementById('startBtn').style.display = 'none';
            document.getElementById('stopBtn').style.display = 'inline-block';
            document.getElementById('displayArea').style.display = 'block';

            // 隠しコマンド：再生開始時にOSの音声リストを強制ロード
            synth.getVoices();

            while (currentIndex < words.length && isPlaying) {{
                await playWordSequence(words[currentIndex]);
                currentIndex++;
            }}

            if (currentIndex >= words.length) {{
                alert("指定範囲の学習がすべて終了しました！");
                stopLearning();
                currentIndex = 0; 
            }}
        }}

        function stopLearning() {{
            isPlaying = false;
            synth.cancel(); 
            document.getElementById('startBtn').style.display = 'inline-block';
            document.getElementById('stopBtn').style.display = 'none';
            document.getElementById('startBtn').innerText = '▶️ 続きから再生';
        }}
    </script>
</body>
</html>
"""

components.html(html_code, height=400, scrolling=True)

st.caption("※マナーモードを解除してご利用ください。")
