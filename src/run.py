import os
import yaml
import datetime
import pandas as pd
from fredapi import Fred
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm

# ==========================================
# 1. 環境設定
# ==========================================
FRED_API_KEY = os.getenv("FRED_API_KEY")
CONFIG_PATH = "config/indicators.yml"
FONT_PATH = "ipaexg.ttf"
OUTPUT_IMAGE = "output/note_table.png"
OUTPUT_MD = "output/analysis.md"

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
# 2. レポート生成ロジック (AIなし)
# ==========================================
def generate_simple_markdown(latest_values):
    today = datetime.date.today().strftime("%Y/%m/%d")
    
    # 取得した値をリストアップ
    nfp = latest_values.get('非農業部門雇用者数 (NFP)', 'N/A')
    dxy = latest_values.get('ドルインデックス', 'N/A')
    cpi = latest_values.get('消費者物価指数 (CPI)', 'N/A')

    return f"""# 【Weekly Macro Data】経済 Macro NOTE (KURURUGI)
📅 *データ更新日: {today}*

---
## 📊 主要指標の最新値
最新の経済データをFRED（セントルイス連邦準備銀行）より取得しました。

### 1. 雇用統計 (NFP)
* **最新値:** {nfp}

### 2. ドル指数 (DXY)
* **最新値:** {dxy}

### 3. 消費者物価 (CPI)
* **最新値:** {cpi}

---
## 📈 チャート確認
詳細な推移については、同フォルダ内に生成された `output_sns.png` を参照してください。

---
**Powered by KURURUGI Data System**
"""

# ==========================================
# 3. 画像生成 & メイン
# ==========================================
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
        ax.grid(True, alpha=0.2)
        
    plt.tight_layout()
    plt.savefig(OUTPUT_IMAGE)

def main():
    print("🚀 Running KURURUGI Macro Data System (Lean Version)...")
    try:
        config = load_config()
        data, latest = get_fred_data(config['indicators'])
        
        # Markdown生成（AI分析をスキップ）
        print("📝 Generating data report...")
        final_md = generate_simple_markdown(latest)
        with open(OUTPUT_MD, "w", encoding="utf-8") as f:
            f.write(final_md)
            
        # 画像生成
        print("🎨 Generating dashboard image...")
        create_sns_image(data, config)
        
        print("✅ Process completed! Reports updated.")
    except Exception as e:
        print(f"❌ Critical Error: {e}")
        exit(1)

if __name__ == "__main__":
    main()