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
        
        df = df.rename(columns={
            "単語": "en",
            "意味": "jp",
            "例文": "ex_en",
            "例文訳": "ex_jp"
        })
        
        for col in ["en", "jp", "ex_en", "ex_jp"]:
            if col not in df.columns:
                df[col] = ""
                
        return df
    except Exception as e:
        st.error(f"CSVの読み込みに失敗しました: {e}")
        return pd.DataFrame()

df = load_data()


# --- メイン画面UI ---
st.markdown("<h3 style='text-align: center; margin-bottom: 0;'>🎧 NGSL 聞き流し学習</h3>", unsafe_allow_html=True)

if df.empty:
    st.warning("単語データを読み込めません。vocab.csv がアップロードされているか確認してください。")
    st.stop()

words_json = json.dumps(df.to_dict(orient="records"))

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

    <button id="startBtn" onclick="startLearning()">▶️ 聞き流しスタート</button>
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

        function getVoice(lang) {{
            const voices = synth.getVoices();
            return voices.find(v => v.lang.includes(lang) && v.lang.includes('US')) || voices.find(v => v.lang.includes(lang));
        }}

        function speak(text, lang, rate=0.9) {{
            return new Promise((resolve) => {{
                if (!isPlaying || !text) return resolve(); 
                const utterance = new SpeechSynthesisUtterance(text);
                utterance.voice = getVoice(lang);
                utterance.lang = lang;
                utterance.rate = rate; 
                
                // ★ここが「間隔」の設定です（600 → 200 に変更しました）
                // もっと短くしたい場合は 100 や 0 に、長くしたい場合は 500 などに変更できます
                utterance.onend = () => {{ setTimeout(resolve, 200); }}; 
                
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

            // 1. 英語
            await speak(wordObj.en, 'en-US');
            // 2. 英語
            await speak(wordObj.en, 'en-US');
            
            // 3. 日本語
            if (!isPlaying) return;
            if (wordObj.jp) {{
                document.getElementById('jpWord').style.display = 'block';
                await speak(wordObj.jp, 'ja-JP', 1.1);
            }}

            // 4. 英語
            await speak(wordObj.en, 'en-US');

            // 5. 例文英語
            if (!isPlaying) return;
            if (wordObj.ex_en) {{
                document.getElementById('exEn').style.display = 'block';
                await speak(wordObj.ex_en, 'en-US');
            }}

            // 6. 例文日本語
            if (!isPlaying) return;
            if (wordObj.ex_jp) {{
                document.getElementById('exJp').style.display = 'block';
                await speak(wordObj.ex_jp, 'ja-JP', 1.1);
            }}
        }}

        async function startLearning() {{
            if (words.length === 0) return;
            isPlaying = true;
            document.getElementById('startBtn').style.display = 'none';
            document.getElementById('stopBtn').style.display = 'inline-block';
            document.getElementById('displayArea').style.display = 'block';

            while (currentIndex < words.length && isPlaying) {{
                await playWordSequence(words[currentIndex]);
                currentIndex++;
            }}

            if (currentIndex >= words.length) {{
                alert("すべての単語が終了しました！");
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
