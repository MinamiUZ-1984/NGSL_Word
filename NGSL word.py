import streamlit as st
import pandas as pd
import json
import streamlit.components.v1 as components

# --- ページ設定（アイコン追加） ---
st.set_page_config(page_title="NGSL 聞き流し", page_icon="🎧", layout="centered")

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
        
        new_df = pd.DataFrame()
        cols_count = df.shape[1]
        
        new_df['rank'] = df.iloc[:, 0] if cols_count > 0 else range(1, len(df) + 1)
        new_df['en'] = df.iloc[:, 1] if cols_count > 1 else ""
        new_df['jp'] = df.iloc[:, 2] if cols_count > 2 else ""      
        new_df['ex_en'] = df.iloc[:, 4] if cols_count > 4 else ""   
        new_df['ex_jp'] = df.iloc[:, 5] if cols_count > 5 else ""   
        
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

# --- 🎯 範囲指定の設定 ---
st.divider()
min_rank = int(df['rank'].min()) if not df.empty and int(df['rank'].min()) > 0 else 1
max_rank = int(df['rank'].max()) if not df.empty else 3000

st.write("▼ 出題範囲を手入力で設定")

col1, col2 = st.columns(2)
with col1:
    start_rank = st.number_input("スタート番号", min_value=min_rank, max_value=max_rank, value=min_rank, step=1)
with col2:
    end_rank = st.number_input("エンド番号", min_value=min_rank, max_value=max_rank, value=min(min_rank + 99, max_rank), step=1)

if start_rank > end_rank:
    st.error("⚠️ スタート番号はエンド番号以下の数字にしてください。")
    st.stop()

selected_range = (start_rank, end_rank)
filtered_df = df[(df['rank'] >= selected_range[0]) & (df['rank'] <= selected_range[1])]

st.info(f"📚 **{selected_range[0]} 〜 {selected_range[1]}** 番から出題（出題回数が少ない順・ランダム）")

words_json = json.dumps(filtered_df.to_dict(orient="records"))

# --- 音声再生＆学習記録UI用のHTML/JavaScript ---
html_code = f"""
<!DOCTYPE html>
<html>
<head>
    <style>
        body {{ font-family: sans-serif; text-align: center; margin: 0; padding: 0; color: #333; }}
        .word-container {{ padding: 10px; border: 2px solid #1E90FF; border-radius: 8px; background-color: #f0f8ff; max-width: 100%; margin: 15px auto; position: relative; }}
        
        /* 進捗表示のデザイン */
        .progress-text {{ font-size: 14px; font-weight: bold; color: #666; background-color: #e0f2fe; display: inline-block; padding: 4px 12px; border-radius: 12px; margin-bottom: 10px; }}
        
        .en-word {{ font-size: 32px; font-weight: bold; color: #1E90FF; margin-bottom: 5px; }}
        .jp-word {{ font-size: 22px; color: #e74c3c; margin-bottom: 10px; min-height: 28px; display: none; }}
        hr {{ margin: 10px 0; border: none; border-top: 1px solid #ccc; }}
        .ex-en {{ font-size: 16px; color: #555; margin-bottom: 5px; min-height: 22px; }}
        .ex-jp {{ font-size: 14px; color: #888; display: none; }}
        
        .action-btn {{ padding: 14px 20px; font-size: 16px; color: white; border: none; border-radius: 8px; cursor: pointer; font-weight: bold; width: 90%; max-width: 320px; margin: 5px auto; display: block; }}
        #startBtn {{ background-color: #1E90FF; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }}
        #startBtn:hover {{ background-color: #0066cc; }}
        #stopBtn {{ background-color: #e74c3c; }}
        #stopBtn:hover {{ background-color: #c0392b; }}
        #skipBtn {{ background-color: #2ecc71; margin-top: 15px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }}
        #skipBtn:hover {{ background-color: #27ae60; }}
        #resetBtn {{ background-color: #95a5a6; font-size: 14px; padding: 10px 20px; width: auto; margin-top: 30px; }}
        #resetBtn:hover {{ background-color: #7f8c8d; }}
    </style>
</head>
<body>

    <button id="startBtn" class="action-btn" onclick="startLearning()">▶️ 学習スタート</button>
    <button id="stopBtn" class="action-btn" onclick="stopLearning()" style="display: none;">⏹ 停止</button>

    <div id="displayArea" class="word-container" style="display: none;">
        <div id="progressDisplay" class="progress-text"></div>
        
        <div id="enWord" class="en-word"></div>
        <div id="jpWord" class="jp-word"></div>
        <hr>
        <div id="exEn" class="ex-en"></div>
        <div id="exJp" class="ex-jp"></div>
    </div>

    <button id="skipBtn" class="action-btn" onclick="markAsLearned()" style="display: none;">✅ 覚えた！(次回から出題しない)</button>
    <button id="resetBtn" class="action-btn" onclick="resetProgress()">🔄 学習記録をリセット</button>

    <script>
        const words = {words_json}; 
        let playlist = [];
        let currentIndex = 0;
        let isPlaying = false;
        let isSkipping = false; 
        const synth = window.speechSynthesis;
        let wakeLock = null; // ★スリープ防止用の変数

        let progress = JSON.parse(localStorage.getItem('ngsl_progress')) || {{}};

        function getProgress(rank) {{
            if (!progress[rank]) {{ progress[rank] = {{ playCount: 0, skipped: false }}; }}
            return progress[rank];
        }}

        function saveProgress() {{
            localStorage.setItem('ngsl_progress', JSON.stringify(progress));
        }}

        function resetProgress() {{
            if (confirm("『出題回数』と『覚えた単語』の記録をすべてリセットしますか？")) {{
                localStorage.removeItem('ngsl_progress');
                progress = {{}};
                alert("リセットが完了しました！");
            }}
        }}

        // ★画面のスリープ（自動ロック）を防ぐ関数
        async function requestWakeLock() {{
            try {{
                if ('wakeLock' in navigator) {{
                    wakeLock = await navigator.wakeLock.request('screen');
                    console.log('スリープ防止がオンになりました');
                }}
            }} catch (err) {{
                console.log('スリープ防止エラー:', err);
            }}
        }}

        // ★スリープ防止を解除する関数
        function releaseWakeLock() {{
            if (wakeLock !== null) {{
                wakeLock.release().then(() => {{ wakeLock = null; }});
            }}
        }}

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

        function speak(text, lang, rate=0.9, pause=400) {{
            return new Promise((resolve) => {{
                if (!isPlaying || isSkipping || !text || text.trim() === "") return resolve(); 
                
                const utterance = new SpeechSynthesisUtterance(text);
                utterance.lang = lang;
                const voice = getVoice(lang);
                if (voice) utterance.voice = voice;
                
                utterance.rate = rate; 
                utterance.onend = () => {{ setTimeout(resolve, pause); }}; 
                utterance.onerror = () => {{ setTimeout(resolve, 100); }}; 
                
                synth.speak(utterance);
            }});
        }}

        async function playWordSequence(wordObj) {{
            isSkipping = false;
            
            // ★進捗テキストの更新 (例: 15 / 100 問目)
            document.getElementById('progressDisplay').innerText = (currentIndex + 1) + " / " + playlist.length + " 問目";

            document.getElementById('enWord').innerText = wordObj.en || "";
            document.getElementById('jpWord').style.display = 'none';
            document.getElementById('jpWord').innerText = wordObj.jp || "";
            document.getElementById('exEn').style.display = 'none';
            document.getElementById('exEn').innerText = wordObj.ex_en || "";
            document.getElementById('exJp').style.display = 'none';
            document.getElementById('exJp').innerText = wordObj.ex_jp || "";

            if (!isPlaying || isSkipping) return; await speak(wordObj.en, 'en-US');
            if (!isPlaying || isSkipping) return; await speak(wordObj.en, 'en-US');
            
            if (!isPlaying || isSkipping) return;
            if (wordObj.jp && wordObj.jp.trim() !== "") {{
                document.getElementById('jpWord').style.display = 'block';
                await speak(wordObj.jp, 'ja-JP', 1.1);
            }}

            if (!isPlaying || isSkipping) return; await speak(wordObj.en, 'en-US');

            if (!isPlaying || isSkipping) return;
            if (wordObj.ex_en && wordObj.ex_en.trim() !== "") {{
                document.getElementById('exEn').style.display = 'block';
                await speak(wordObj.ex_en, 'en-US');
            }}

            if (!isPlaying || isSkipping) return;
            if (wordObj.ex_jp && wordObj.ex_jp.trim() !== "") {{
                document.getElementById('exJp').style.display = 'block';
                await speak(wordObj.ex_jp, 'ja-JP', 1.1);
            }}
            
            if (!isPlaying || isSkipping) return; await speak(wordObj.en, 'en-US', 0.9, 800);
        }}

        async function startLearning() {{
            if (words.length === 0) return;
            
            playlist = words.filter(w => !getProgress(w.rank).skipped);
            if (playlist.length === 0) {{
                alert("この範囲の単語はすべて「覚えた（スキップ）」に設定されています！必要に応じてリセットしてください。");
                return;
            }}

            playlist.sort(() => Math.random() - 0.5); 
            playlist.sort((a, b) => getProgress(a.rank).playCount - getProgress(b.rank).playCount); 

            isPlaying = true;
            currentIndex = 0;
            
            // ★再生開始時にスリープ防止をリクエスト
            requestWakeLock();

            document.getElementById('startBtn').style.display = 'none';
            document.getElementById('resetBtn').style.display = 'none';
            document.getElementById('stopBtn').style.display = 'block';
            document.getElementById('skipBtn').style.display = 'block';
            document.getElementById('displayArea').style.display = 'block';

            synth.getVoices();

            while (currentIndex < playlist.length && isPlaying) {{
                let currentWord = playlist[currentIndex];
                progress[currentWord.rank].playCount += 1;
                saveProgress();

                await playWordSequence(currentWord);
                currentIndex++;
            }}

            if (currentIndex >= playlist.length && isPlaying) {{
                alert("今回の出題リストがすべて終了しました！");
                stopLearning();
            }}
        }}

        function stopLearning() {{
            isPlaying = false;
            isSkipping = false;
            synth.cancel(); 
            
            // ★停止時にスリープ防止を解除
            releaseWakeLock();

            document.getElementById('startBtn').style.display = 'block';
            document.getElementById('resetBtn').style.display = 'block';
            document.getElementById('stopBtn').style.display = 'none';
            document.getElementById('skipBtn').style.display = 'none';
            document.getElementById('startBtn').innerText = '▶️ 再開する';
        }}

        function markAsLearned() {{
            if (!isPlaying || !playlist[currentIndex]) return;
            
            let currentWord = playlist[currentIndex];
            progress[currentWord.rank].skipped = true;
            saveProgress();
            
            isSkipping = true;
            synth.cancel(); 
        }}
        
        // ★タブを閉じたり隠したりした時も念のためスリープ防止を解除
        document.addEventListener('visibilitychange', () => {{
            if (document.visibilityState !== 'visible') {{
                releaseWakeLock();
            }} else if (isPlaying) {{
                // 戻ってきたときに再生中なら再度ロックをかける
                requestWakeLock();
            }}
        }});

    </script>
</body>
</html>
"""

# 高さを少し増やして進捗テキストが収まるようにしました
components.html(html_code, height=600, scrolling=True)

st.caption("※マナーモードを解除してご利用ください。")
st.caption("※学習記録はブラウザに保存されるため、明日も続きから効率よく学習できます。")
