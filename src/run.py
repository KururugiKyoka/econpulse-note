import os
import yaml
import datetime
import json
import re
import time
import pandas as pd
from fredapi import Fred
from google import genai
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm

# 設定
FRED_API_KEY = os.getenv("FRED_API_KEY")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
CONFIG_PATH = "config/indicators.yml"
FONT_PATH = "ipaexg.ttf"
OUTPUT_IMAGE = "output_sns.png"
OUTPUT_MD = "analysis.md"

client = genai.Client(api_key=GOOGLE_API_KEY)

def load_config():
    with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)

def get_fred_data(indicators):
    fred = Fred(api_key=FRED_API_KEY)
    data_results = {}
    latest_values = {}
    for item in indicators:
        series_id = item['id']
        label = item['label']
        series = fred.get_series(series_id)
        data_results[label] = series.tail(12)
        latest_values[label] = series.iloc[-1]
    return data_results, latest_values

def analyze_with_gemini(latest_values):
    prompt = f"指標データを分析しJSONで回答してください。NFP:{latest_values.get('非農業部門雇用者数 (NFP)')}, DXY:{latest_values.get('ドルインデックス')}, CPI:{latest_values.get('消費者物価指数 (CPI)')}. JSONキー: summary, nfp_insight, dxy_trend, dxy_insight, cpi_insight, overall_outlook"
    
    # 試行するモデルの優先順位
    models_to_try = ['gemini-1.5-flash', 'gemini-1.5-flash-8b']
    last_error = None

    for model_name in models_to_try:
        print(f"🧠 Trying model: {model_name}...")
        for attempt in range(2):
            try:
                response = client.models.generate_content(
                    model=model_name, 
                    contents=prompt
                )
                json_match = re.search(r'\{.*\}', response.text, re.DOTALL)
                if json_match:
                    return json.loads(json_match.group())
            except Exception as e:
                last_error = e
                if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
                    # 制限にかかったら長めに待機（90秒）
                    wait_time = 90
                    print(f"⚠️ クォータ制限（429）。{wait_time}秒待機して再試行します...")
                    time.sleep(wait_time)
                    continue
                break # 他のエラーなら次のモデルへ
    
    raise last_error if last_error else Exception("分析に失敗しました。")

def main():
    print("🚀 Running KURURUGI Macro System (2026.01.25-Final)...")
    try:
        config = load_config()
        data, latest = get_fred_data(config['indicators'])
        
        print("🧠 Analyzing with Gemini 2.0 Flash...")
        analysis = analyze_with_gemini(latest)
        
        today = datetime.date.today().strftime("%Y/%m/%d")
        report = f"# 【Weekly Macro Insight】\\n📅 *{today}*\\n\\n## 📈 要約\\n> {analysis['summary']}\\n\\n## 🔍 指標分析\\n### NFP: {latest.get('非農業部門雇用者数 (NFP)')}\\n{analysis['nfp_insight']}\\n\\n### DXY: {latest.get('ドルインデックス')}\\nトレンド: {analysis['dxy_trend']}\\n\\n### CPI: {latest.get('消費者物価指数 (CPI)')}\\n{analysis['cpi_insight']}\\n\\n## 💡 総括\\n{analysis['overall_outlook']}"
        
        with open(OUTPUT_MD, "w", encoding="utf-8") as f:
            f.write(report)
        
        plt.style.use('dark_background')
        fig, axes = plt.subplots(1, 3, figsize=(18, 6))
        prop = fm.FontProperties(fname=FONT_PATH)
        for i, label in enumerate(list(data.keys())[:3]):
            axes[i].plot(data[label].index, data[label].values, color='#00ffcc')
            axes[i].set_title(label, fontproperties=prop)
        plt.tight_layout()
        plt.savefig(OUTPUT_IMAGE)
        print("✅ All processes completed! Check analysis.md and output_sns.png")
    except Exception as e:
        print(f"❌ Critical Error: {e}")
        exit(1)

if __name__ == "__main__":
    main()