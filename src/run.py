import os
import yaml
import datetime
import json
import re
import pandas as pd
from fredapi import Fred
from google import genai  # 最新の google-genai SDK
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm

# ==========================================
# 1. 環境設定
# ==========================================
FRED_API_KEY = os.getenv("FRED_API_KEY")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
CONFIG_PATH = "config/indicators.yml"
FONT_PATH = "ipaexg.ttf"
OUTPUT_IMAGE = "output_sns.png"
OUTPUT_MD = "analysis.md"

# クライアントの初期化（google-genai 方式）
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

# ==========================================
# 3. AI分析ロジック
# ==========================================
def analyze_with_gemini(latest_values):
    prompt = f"""
    マクロ経済アナリストとして、以下の最新指標を分析し、JSONで回答してください。
    【データ】
    - NFP: {latest_values.get('非農業部門雇用者数 (NFP)', 'N/A')}
    - DXY: {latest_values.get('ドルインデックス', 'N/A')}
    - CPI: {latest_values.get('消費者物価指数 (CPI)', 'N/A')}

    【形式】
    以下のキーを持つJSONのみを返してください。
    {{ "summary": "...", "nfp_insight": "...", "dxy_trend": "...", "dxy_insight": "...", "cpi_insight": "...", "overall_outlook": "..." }}
    """
    
    # 2026年最新SDKでの最も安定した呼び出し方
    response = client.models.generate_content(
        model='gemini-1.5-flash', 
        contents=prompt
    )
    
    text = response.text
    # JSON抽出（Geminiがお喋りしても大丈夫なように正規表現でガード）
    json_match = re.search(r'\{.*\}', text, re.DOTALL)
    if json_match:
        return json.loads(json_match.group())
    else:
        raise ValueError(f"JSONパースエラー: {text}")

# ==========================================
# 4. Markdown & 画像生成
# ==========================================
def generate_professional_markdown(analysis, latest_values):
    today = datetime.date.today().strftime("%Y/%m/%d")
    return f"""# 【Weekly Macro Insight】経済 Macro NOTE (KURURUGI)
📅 *作成日: {today}*

---
## 📈 エグゼクティブ・サマリー
> {analysis.get('summary')}

## 🔍 指標別分析
### 1. 非農業部門雇用者数 (NFP)
* **Fact:** {latest_values.get('非農業部門雇用者数 (NFP)')}
* **Insight:** {analysis.get('nfp_insight')}

### 2. ドルインデックス (DXY)
| 指標 | 現在値 | トレンド |
| :--- | :--- | :--- |
| **DXY** | {latest_values.get('ドルインデックス')} | {analysis.get('dxy_trend')} |
* **分析の視点:** {analysis.get('dxy_insight')}

### 3. 消費者物価指数 (CPI)
* **注目ポイント:** {analysis.get('cpi_insight')}

## 💡 総括と戦略的展望
{analysis.get('overall_outlook')}

---
**Powered by KURURUGI Macro System**
"""

def create_sns_image(data_results, config):
    plt.style.use('dark_background')
    fig, axes = plt.subplots(1, 3, figsize=(18, 6))
    prop = fm.FontProperties(fname=FONT_PATH)
    target_labels = config.get('target_labels', list(data_results.keys()))
    for i, label in enumerate(target_labels[:3]):
        ax = axes[i]
        df = data_results[label]
        ax.plot(df.index, df.values, color='#00ffcc', linewidth=2)
        ax.set_title(label, fontproperties=prop)
    plt.tight_layout()
    plt.savefig(OUTPUT_IMAGE)

def main():
    print("🚀 Starting Economic Macro Insight (v2026.01)...")
    config = load_config()
    data, latest = get_fred_data(config['indicators'])
    
    print("🧠 Analyzing with Gemini 1.5 Flash...")
    try:
        analysis_json = analyze_with_gemini(latest)
        final_md = generate_professional_markdown(analysis_json, latest)
        with open(OUTPUT_MD, "w", encoding="utf-8") as f:
            f.write(final_md)
        print("🎨 Generating dashboard image...")
        create_sns_image(data, config)
        print("✅ All processes completed successfully!")
    except Exception as e:
        print(f"❌ Critical Error: {e}")
        exit(1)

if __name__ == "__main__":
    main()