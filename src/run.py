import os
import yaml
import datetime
import pandas as pd
from fredapi import Fred
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm

# 設定
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
    yoy_results = {}
    latest_values = {}
    
    for item in indicators:
        series_id = item['id']
        label = item['label']
        # 前年比計算のため25ヶ月分取得
        series = fred.get_series(series_id).tail(25)
        
        # 実数値（直近12ヶ月）
        data_results[label] = series.tail(12)
        
        # 前年比（％）を計算
        yoy = (series / series.shift(12) - 1) * 100
        yoy_results[label] = yoy.tail(12)
        
        latest_values[label] = {
            'value': series.iloc[-1],
            'yoy': yoy.iloc[-1]
        }
    return data_results, yoy_results, latest_values

def generate_report(latest_values):
    today = datetime.date.today().strftime("%Y/%m/%d")
    
    lines = [f"# 【Weekly Macro Data】経済 Macro NOTE (KURURUGI)", f"📅 *更新日: {today}*", "---", "## 📊 指標の最新値 (実数値 & 前年比)"]
    
    for label, v in latest_values.items():
        val = f"{v['value']:.2f}" if "指数" in label or "CPI" in label or "PCE" in label else f"{v['value']:,}"
        yoy_str = f"{v['yoy']:+.2f}%"
        lines.append(f"### {label}")
        lines.append(f"* **最新値:** {val}")
        lines.append(f"* **前年比:** {yoy_str}")
        lines.append("")
        
    lines.append("---\\n**Powered by KURURUGI Data System**")
    return "\\n".join(lines)

def create_dashboard(data_results, yoy_results):
    plt.style.use('dark_background')
    # 2段構成に変更 (上段: 実数値, 下段: 前年比)
    fig, axes = plt.subplots(2, 3, figsize=(18, 10))
    prop = fm.FontProperties(fname=FONT_PATH)
    labels = list(data_results.keys())
    
    for i in range(3):
        label = labels[i]
        
        # 上段：実数値（レベル）
        axes[0, i].plot(data_results[label].index, data_results[label].values, color='#00ffcc', linewidth=2, marker='o', markersize=4)
        axes[0, i].set_title(f"{label} (レベル)", fontproperties=prop)
        axes[0, i].grid(True, alpha=0.2)
        
        # 下段：前年比（％）
        axes[1, i].bar(yoy_results[label].index, yoy_results[label].values, color='#ff66cc', alpha=0.7)
        axes[1, i].set_title(f"{label} (前年比 %)", fontproperties=prop)
        axes[1, i].grid(True, alpha=0.2)
        # 0ラインを強調
        axes[1, i].axhline(0, color='white', linewidth=0.8)

    plt.tight_layout()
    plt.savefig(OUTPUT_IMAGE)

def main():
    print("🚀 Running KURURUGI Macro System (YoY Enhanced Version)...")
    try:
        config = load_config()
        data, yoy, latest = get_fred_data(config['indicators'])
        
        # Markdown生成
        with open(OUTPUT_MD, "w", encoding="utf-8") as f:
            f.write(generate_report(latest))
            
        # 画像生成
        create_dashboard(data, yoy)
        print("✅ Success! Updated with YoY data.")
    except Exception as e:
        print(f"❌ Error: {e}")
        exit(1)

if __name__ == "__main__":
    main()