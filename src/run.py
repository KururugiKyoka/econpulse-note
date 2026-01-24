import os
import yaml
import datetime
import json
import re
import time  # 待機のために追加
import pandas as pd
from fredapi import Fred
from google import genai
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
# 3. AI分析ロジック (リトライ機能付き)
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

    # リソース不足(429)対策：最大3回までリトライする
    for attempt in range(3):
        try:
            # ログで接続が確認できている 2.0-flash を使用
            response = client.models.generate_content(
                model='gemini-2.0-flash', 
                contents=prompt
            )
            
            text = response.text
            json_match = re.search(r'\{.*\}', text, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
            else:
                raise ValueError("JSONが見つかりませんでした")
                
        except Exception as e:
            if "RESOURCE_EXHAUSTED" in str(e) or "429" in str(e):
                print(f"⚠️ クォータ制限に達しました。30秒待機して再試行します ({attempt+1}/3)...")
                time.sleep(30)
                continue
            raise e
    
    raise Exception("リトライ上限に達しました。APIの制限を確認してください。")

# ==========================================
# 4. レポート & 画像生成
# ==========================================
def generate_professional_markdown(analysis, latest_values):
    today = datetime.date.today().strftime("%Y/%m/%d")
    return f"""# 【Weekly Macro Insight】経済 Macro NOTE (KURURUGI)
📅 *作成日: {today}*

---
## 📈 エグゼクティブ・サマリー
> {analysis.get('summary')}

## 🔍 指標別分析
### 1. 雇用統計 (NFP)
* **最新値:** {latest_values.get('非農業部門雇用者数 (NFP)')}
* **洞察:** {analysis.get('nfp_insight')}

### 2. ドル指数 (DXY)
| 指標 | 現在値 | トレンド |
| :--- | :--- | :--- |
| **DXY** | {latest_values.get('ドルインデックス')} | {analysis.get('dxy_trend')} |

### 3. 消費者物価 (CPI)
* **注目点:** {analysis.get('cpi_insight')}

## 💡 総括
{analysis.get('overall_outlook')}
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
    print("🚀 Running KURURUGI Macro System (2026.01)...")
    config = load_config()
    data, latest = get_fred_data(config['indicators'])
    
    print("🧠 Analyzing with Gemini (with Retry logic)...")
    try:
        analysis_json = analyze_with_gemini(latest)
        final_md = generate_professional_markdown(analysis_json, latest)
        with open(OUTPUT_MD, "w", encoding="utf-8") as f:
            f.write(final_md)
        create_sns_image(data, config)
        print("✅ All processes completed successfully!")
    except Exception as e:
        print(f"❌ Error: {e}")
        exit(1)

if __name__ == "__main__":
    main()