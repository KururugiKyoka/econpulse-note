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
    data_results, yoy_results, latest_values = {}, {}, {}
    
    for item in indicators:
        series_id, label = item['id'], item['label']
        series = fred.get_series(series_id).tail(25)
        
        data_results[label] = series.tail(12)
        yoy = (series / series.shift(12) - 1) * 100
        yoy_results[label] = yoy.tail(12)
        
        latest_values[label] = {'value': series.iloc[-1], 'yoy': yoy.iloc[-1]}
    return data_results, yoy_results, latest_values

def generate_report(latest_values):
    today = datetime.date.today().strftime("%Y/%m/%d")
    lines = [f"# 【Weekly Macro Data】経済 Macro NOTE", f"📅 *更新日: {today}*", "---"]
    for label, v in latest_values.items():
        val = f"{v['value']:.2f}" if any(x in label for x in ["指数", "CPI", "PCE", "利回り", "ドル"]) else f"{v['value']:,}"
        lines.append(f"### {label}\\n* **最新値:** {val}\\n* **前年比:** {v['yoy']:+.2f}%")
    return "\\n".join(lines)

def create_dashboard(data_results, yoy_results):
    plt.style.use('dark_background')
    labels = list(data_results.keys())
    num_inds = len(labels)
    
    # 4行4列のレイアウト（1指標につき2グラフ使用：レベルとYoY）
    fig, axes = plt.subplots(4, 4, figsize=(24, 18))
    prop = fm.FontProperties(fname=FONT_PATH)
    
    for i, label in enumerate(labels):
        row = i // 2  # 0,0,1,1,2,2,3,3
        col_base = (i % 2) * 2 # 0, 2
        
        # 左側：実数値（レベル）
        ax_l = axes[row, col_base]
        ax_l.plot(data_results[label].index, data_results[label].values, color='#00ffcc', linewidth=2, marker='o', markersize=3)
        ax_l.set_title(f"{label} (レベル)", fontproperties=prop, fontsize=10)
        ax_l.grid(True, alpha=0.15)
        ax_l.tick_params(axis='both', which='major', labelsize=8)

        # 右側：前年比（％）
        ax_r = axes[row, col_base + 1]
        ax_r.bar(yoy_results[label].index, yoy_results[label].values, color='#ff66cc', alpha=0.7)
        ax_r.set_title(f"{label} (YoY %)", fontproperties=prop, fontsize=10)
        ax_r.grid(True, alpha=0.15)
        ax_r.axhline(0, color='white', linewidth=0.5)
        ax_r.tick_params(axis='both', which='major', labelsize=8)

    plt.tight_layout()
    plt.savefig(OUTPUT_IMAGE, dpi=150)

def main():
    try:
        config = load_config()
        data, yoy, latest = get_fred_data(config['indicators'])
        with open(OUTPUT_MD, "w", encoding="utf-8") as f:
            f.write(generate_report(latest))
        create_dashboard(data, yoy)
        print("✅ Success! 16-chart dashboard generated.")
    except Exception as e:
        print(f"❌ Error: {e}"); exit(1)

if __name__ == "__main__":
    main()