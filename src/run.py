import os
import yaml
import datetime
import pandas as pd
from fredapi import Fred
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm

# 基本設定
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
        # 前年比計算のため25ヶ月分取得
        series = fred.get_series(series_id).tail(25)
        
        data_results[label] = series.tail(12)
        yoy = (series / series.shift(12) - 1) * 100
        yoy_results[label] = yoy.tail(12)
        
        latest_values[label] = {'value': series.iloc[-1], 'yoy': yoy.iloc[-1]}
    return data_results, yoy_results, latest_values

def generate_report(latest_values, thresholds):
    today = datetime.date.today().strftime("%Y/%m/%d")
    lines = [f"# 【Weekly Macro Data】経済 Macro NOTE", f"📅 *最終更新: {today}*", "---", "## 🚨 リセッション・アラート状況"]
    
    signals = []
    if latest_values['非農業部門雇用者数 (NFP)']['yoy'] < thresholds['nfp_yoy_min']: signals.append("⚠️ 雇用成長の危険な鈍化")
    if latest_values['失業率']['yoy'] > thresholds['unrate_yoy_max']: signals.append("🚨 失業率の急上昇（リセッションの予兆）")
    if latest_values['ミシガン大学消費者態度指数']['value'] < thresholds['michigan_val_min']: signals.append("📉 消費者センチメントの極端な悪化")
    
    lines.append("\\n".join(signals) if signals else "✅ 現在、明確な警告シグナルは検出されていません。")
    lines.append("---")
    
    for label, v in latest_values.items():
        val = f"{v['value']:.2f}" if any(x in label for x in ["指数", "CPI", "PCE", "利回り", "ドル"]) else f"{v['value']:,}"
        lines.append(f"### {label}\\n* **最新値:** {val}\\n* **前年比:** {v['yoy']:+.2f}%")
    return "\\n".join(lines)

def create_dashboard(data_results, yoy_results, thresholds):
    plt.style.use('dark_background')
    labels = list(data_results.keys())
    # 全体サイズを大きくし、タイトルのためのスペース(top=0.9)を確保
    fig, axes = plt.subplots(4, 4, figsize=(24, 20))
    prop = fm.FontProperties(fname=FONT_PATH)
    
    today_str = datetime.date.today().strftime("%Y/%m/%d")
    fig.suptitle(f"Weekly Macroeconomic Dashboard (Updated: {today_str})", 
                 color='white', fontsize=28, fontproperties=prop, y=0.96)
    
    alert_color = '#ff3333'
    normal_line = '#00ffcc'
    normal_bar = '#ff66cc'
    
    for i, label in enumerate(labels):
        row, col_base = i // 2, (i % 2) * 2
        
        # 実数値
        data = data_results[label]
        c_l = alert_color if label == "ミシガン大学消費者態度指数" and data.iloc[-1] < thresholds['michigan_val_min'] else normal_line
        axes[row, col_base].plot(data.index, data.values, color=c_l, linewidth=2.5, marker='o', markersize=5)
        axes[row, col_base].set_title(f"{label} (Level)", fontproperties=prop, fontsize=12)
        axes[row, col_base].tick_params(labelsize=10)
        axes[row, col_base].grid(True, alpha=0.15)

        # 前年比
        yoy = yoy_results[label]
        colors_r = []
        for val in yoy:
            c = normal_bar
            if label == "非農業部門雇用者数 (NFP)" and val < thresholds['nfp_yoy_min']: c = alert_color
            elif label == "失業率" and val > thresholds['unrate_yoy_max']: c = alert_color
            elif label == "小売売上高" and val < thresholds['retail_yoy_min']: c = alert_color
            colors_r.append(c)

        axes[row, col_base + 1].bar(yoy.index, yoy.values, color=colors_r, alpha=0.8)
        axes[row, col_base + 1].set_title(f"{label} (YoY %)", fontproperties=prop, fontsize=12)
        axes[row, col_base + 1].tick_params(labelsize=10)
        axes[row, col_base + 1].grid(True, alpha=0.15)
        axes[row, col_base + 1].axhline(0, color='white', linewidth=0.8)

    plt.subplots_adjust(top=0.92, bottom=0.05, hspace=0.3, wspace=0.2)
    # 高解像度(DPI=300)で保存
    plt.savefig(OUTPUT_IMAGE, dpi=300, bbox_inches='tight')

def main():
    try:
        config = load_config()
        data, yoy, latest = get_fred_data(config['indicators'])
        th = config['thresholds']
        
        with open(OUTPUT_MD, "w", encoding="utf-8") as f:
            f.write(generate_report(latest, th))
        
        create_dashboard(data, yoy, th)
        print("✅ Success! Dashboard with branding and dynamic thresholds generated.")
    except Exception as e:
        print(f"❌ Error: {e}"); exit(1)

if __name__ == "__main__":
    main()