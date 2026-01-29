import os
import yaml
import datetime
import pandas as pd
from fredapi import Fred
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import matplotlib.dates as mdates

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
    data_results, yoy_results, latest_values = {}, {}, {}
    
    # 前年比計算のため26ヶ月分取得
    end_date = datetime.date.today()
    start_date = end_date - pd.DateOffset(months=26)
    
    for item in indicators:
        series_id, label = item['id'], item['label']
        series = fred.get_series(series_id, observation_start=start_date)
        
        # すべてのデータを「月初リサンプリング」で統一（時間軸の同期）
        series = series.resample('MS').last()
        yoy = (series / series.shift(12) - 1) * 100
        
        # 直近12ヶ月を切り出し
        data_results[label] = series.tail(12)
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
    fig, axes = plt.subplots(4, 4, figsize=(24, 20))
    prop = fm.FontProperties(fname=FONT_PATH)
    
    today_str = datetime.date.today().strftime("%Y/%m/%d")
    fig.suptitle(f"Weekly Macroeconomic Dashboard (Updated: {today_str})", 
                 color='white', fontsize=28, fontproperties=prop, y=0.96)
    
    alert_color, normal_line, normal_bar = '#ff3333', '#00ffcc', '#ff66cc'
    
    for i, label in enumerate(labels):
        row, col_base = i // 2, (i % 2) * 2
        # 実数値グラフ
        ax_l = axes[row, col_base]
        data = data_results[label]
        c_l = alert_color if label == "ミシガン大学消費者態度指数" and data.iloc[-1] < thresholds['michigan_val_min'] else normal_line
        ax_l.plot(data.index, data.values, color=c_l, linewidth=2.5, marker='o', markersize=5)
        ax_l.set_title(f"{label} (Level)", fontproperties=prop, fontsize=12)
        
        # 前年比グラフ
        ax_r = axes[row, col_base + 1]
        yoy = yoy_results[label]
        colors_r = [alert_color if (label == "非農業部門雇用者数 (NFP)" and val < thresholds['nfp_yoy_min']) or (label == "失業率" and val > thresholds['unrate_yoy_max']) or (label == "小売売上高" and val < thresholds['retail_yoy_min']) else normal_bar for val in yoy]
        ax_r.bar(yoy.index, yoy.values, color=colors_r, alpha=0.8, width=20)
        ax_r.set_title(f"{label} (YoY %)", fontproperties=prop, fontsize=12)
        ax_r.axhline(0, color='white', linewidth=0.8)

        # 横軸フォーマットの統一
        for ax in [ax_l, ax_r]:
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%y/%m'))
            ax.xaxis.set_major_locator(mdates.MonthLocator(interval=3))
            ax.tick_params(labelsize=10); ax.grid(True, alpha=0.15)

    plt.subplots_adjust(top=0.92, bottom=0.05, hspace=0.3, wspace=0.2)
    plt.savefig(OUTPUT_IMAGE, dpi=300, bbox_inches='tight')

def main():
    try:
        config = load_config()
        data, yoy, latest = get_fred_data(config['indicators'])
        th = config['thresholds']
        with open(OUTPUT_MD, "w", encoding="utf-8") as f:
            f.write(generate_report(latest, th))
        create_dashboard(data, yoy, th)
        print("✅ Success!")
    except Exception as e:
        print(f"❌ Error: {e}"); exit(1)

if __name__ == "__main__":
    main()