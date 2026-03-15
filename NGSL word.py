import streamlit as st
import pandas as pd
import json
import streamlit.components.v1 as components

st.set_page_config(page_title="NGSL 聞き流しアプリ", layout="centered")

# --- 1. ダミーデータの準備（実際はここでExcel/CSVを読み込みます） ---
@st.cache_data
def load_data():
    # 実際は: return pd.read_csv("ngsl_words.csv")
    data = [
        {"en": "abandon", "jp": "見捨てる、放棄する", "ex_en": "Do not abandon your dreams.", "ex_jp": "夢をあきらめないで。"},
        {"en": "ability", "jp": "能力、才能", "ex_en": "She has the ability to do the job.", "ex_jp": "彼女にはその仕事をする能力がある。"},
        {"en": "aboard", "jp": "（船・飛行機・列車などに）乗って", "ex_en": "Welcome aboard this flight.", "ex_jp": "本日のフライトへようこそ。"}
    ]
    return pd.DataFrame(data)

df = load_data()

# --- 2. メイン画面のUI ---
st.title("🎧 NGSL 聞き流し学習")
st.write("再生ボタンを押すと、自動的に単語が連続再生されます。")

# DataFrameをJSON文字列に変換（JavaScriptに渡すため）
words_json = json.dumps(df.to_dict(orient="records"))

# --- 3. 音声再生＆UI同期用のHTML/JavaScript ---
# Streamlitの中に、音声制御を行うための独自のWebパーツを埋め込みます
html_code = f"""
<!DOCTYPE html>
<html>
<head>
    <style>
        body {{ font-family: sans-serif; text-align: center; margin-top: 20px; color: #333; }}
        .word-container {{ padding: 20px; border: 2px solid #1E90FF; border-radius: 10px; background-color: #f0f8ff; max-width: 400px; margin: auto; }}
        .en-word {{ font-size: 36px; font-weight: bold; color: #1E90FF; margin-bottom: 10px; }}
        .jp-word {{ font-size: 24px; color: #e74c3c; margin-bottom: 20px; min-height: 30px; display: none; }}
        .ex-en {{ font-size: 18px; color: #555; margin-bottom: 10px; min-height: 25px; }}
        .ex-jp {{ font-size: 16px; color: #888; display: none; }}
        button {{ padding: 15px 30px; font-size: 18px; background-color: #1E90FF; color: white; border: none; border-radius: 5px; cursor: pointer; font-weight: bold; }}
        button:hover {{ background-color: #0066cc; }}
        button:disabled {{ background-color: #ccc; cursor: not-allowed; }}
    </style>
</head>
<body>

    <button id="startBtn" onclick="startLearning()">▶️ 聞き流しスタート</button>
    <button id="stopBtn" onclick="stopLearning()" style="background-color: #e74c3c; display: none;">⏹ 停止</button>

    <div id="displayArea" class="word-container" style="display: none; margin-top: 20px;">
        <div id="enWord" class="en-word"></div>
        <div id="jpWord" class="jp-word"></div>
        <hr>
        <div id="exEn" class="ex-en"></div>
        <div id="exJp" class="ex-jp"></div>
    </div>

    <script>
        const words = {words_json}; // Pythonから渡されたデータ
        let currentIndex = 0;
        let isPlaying = false;

        // ブラウザの音声合成APIを準備
        const synth = window.speechSynthesis;

        function getVoice(lang) {{
            const voices = synth.getVoices();
            // アメリカ英語か、指定言語の音声を探す
            return voices.find(v => v.lang.includes(lang) && v.lang.includes('US')) || voices.find(v => v.lang.includes(lang));
        }}

        function speak(text, lang, rate=0.9) {{
            return new Promise((resolve) => {{
                if (!isPlaying) return resolve(); // 停止されたら即終了
                const utterance = new SpeechSynthesisUtterance(text);
                utterance.voice = getVoice(lang);
                utterance.lang = lang;
                utterance.rate = rate; // 再生スピード（0.9は少しゆっくり）
                utterance.onend = () => {{ setTimeout(resolve, 600); }}; // 読み終わった後0.6秒の「間」を空ける
                synth.speak(utterance);
            }});
        }}

        async function playWordSequence(wordObj) {{
            // 画面リセット（英語だけ表示）
            document.getElementById('enWord').innerText = wordObj.en;
            document.getElementById('jpWord').style.display = 'none';
            document.getElementById('jpWord').innerText = wordObj.jp;
            document.getElementById('exEn').style.display = 'none';
            document.getElementById('exEn').innerText = wordObj.ex_en;
            document.getElementById('exJp').style.display = 'none';
            document.getElementById('exJp').innerText = wordObj.ex_jp;

            // 1. 英語
            await speak(wordObj.en, 'en-US');
            // 2. 英語
            await speak(wordObj.en, 'en-US');
            
            // 3. 日本語（表示して発音）
            if (!isPlaying) return;
            document.getElementById('jpWord').style.display = 'block';
            await speak(wordObj.jp, 'ja-JP', 1.1); // 日本語は少し速め

            // 4. 英語
            await speak(wordObj.en, 'en-US');

            // 5. 例文英語（表示して発音）
            if (!isPlaying) return;
            document.getElementById('exEn').style.display = 'block';
            await speak(wordObj.ex_en, 'en-US');

            // 6. 例文日本語（表示して発音）
            if (!isPlaying) return;
            document.getElementById('exJp').style.display = 'block';
            await speak(wordObj.ex_jp, 'ja-JP', 1.1);
        }}

        async function startLearning() {{
            isPlaying = true;
            document.getElementById('startBtn').style.display = 'none';
            document.getElementById('stopBtn').style.display = 'inline-block';
            document.getElementById('displayArea').style.display = 'block';

            // リストが終わるか、停止ボタンが押されるまでループ
            while (currentIndex < words.length && isPlaying) {{
                await playWordSequence(words[currentIndex]);
                currentIndex++;
            }}

            if (currentIndex >= words.length) {{
                alert("すべての単語が終了しました！");
                stopLearning();
                currentIndex = 0; // リセット
            }}
        }}

        function stopLearning() {{
            isPlaying = false;
            synth.cancel(); // 再生中の音声を強制停止
            document.getElementById('startBtn').style.display = 'inline-block';
            document.getElementById('stopBtn').style.display = 'none';
            document.getElementById('startBtn').innerText = '▶️ 続きから再生';
        }}
    </script>
</body>
</html>
"""

# HTMLをStreamlitアプリ内にレンダリング (高さはスマホでも見やすいように設定)
components.html(html_code, height=500, scrolling=True)

st.divider()
st.caption("※ 初回再生時は音声エンジン読み込みのため、数秒かかる場合があります。スマートフォンの場合はマナーモードを解除してください。")