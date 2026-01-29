import os
import yaml
import datetime
import pandas as pd
from fredapi import Fred
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import matplotlib.dates as mdates

# 環境設定
FRED_API_KEY = os.getenv("FRED_API_KEY")
CONFIG_PATH = "config/indicators.yml"
FONT_PATH = "ipaexg.ttf"
OUTPUT_IMAGE = "output/note_table.png"
OUTPUT_MD = "output/analysis.md"

def load_config():
    with open(CONFIG_PATH, 'r', encoding='utf-8') as f: return yaml.safe_load(f)

def get_fred_data(indicators):
    fred = Fred(api_key=FRED_API_KEY)
    data_results, yoy_results, latest_values = {}, {}, {}
    end_date = datetime.date.today()
    start_date = end_date - pd.DateOffset(months=38)
    
    for item in indicators:
        series_id, label = item['id'], item['label']
        try:
            series = fred.get_series(series_id, observation_start=start_date)
            series = series.resample('MS').last().ffill()
            # 金利差と利回りは「差分」、他は「比率」
            if any(x in label for x in ["Curve", "Yield"]):
                yoy = (series - series.shift(12))
            else:
                yoy = (series / series.shift(12) - 1) * 100
            data_results[label], yoy_results[label] = series.tail(24), yoy.tail(24)
            latest_values[label] = {'value': series.iloc[-1], 'yoy': yoy.iloc[-1]}
        except Exception as e: print(f"⚠️ {label} 取得失敗: {e}"); continue
    return data_results, yoy_results, latest_values

def generate_report(latest_values, thresholds):
    today = datetime.date.today().strftime("%Y/%m/%d")
    lines = [f"# 【Weekly Macro Data】経済 Macro NOTE", f"📅 *最終更新: {today}*", "---", "## 📊 主要指標サマリー", "---"]
    for label, v in latest_values.items():
        suffix = "pt 差" if any(x in label for x in ["Curve", "Yield"]) else "%"
        val = f"{v['value']:.2f}" if any(x in label for x in ["指数", "CPI", "PCE", "Curve", "Yield", "DXY", "Oil", "Gold"]) else f"{v['value']:,}"
        lines.append(f"### {label}\\n* 最新: {val} / 前年比(差): {v['yoy']:+.2f}{suffix}")
    return "\\n".join(lines)

def create_dashboard(data_results, yoy_results, thresholds):
    plt.style.use('dark_background')
    labels = list(data_results.keys())
    # 6行5列に拡張。高さを30に広げてサイズを維持。
    fig, axes = plt.subplots(6, 5, figsize=(30, 30))
    prop = fm.FontProperties(fname=FONT_PATH)
    fig.suptitle(f"Weekly Macroeconomic Dashboard (Updated: {datetime.date.today():%Y/%m/%d})", color='white', fontsize=36, fontproperties=prop, y=0.98)
    
    alert_color, normal_line, normal_bar = '#ff3333', '#00ffcc', '#ff66cc'
    
    for i, label in enumerate(labels):
        row_l = (i // 5) * 2
        row_y = row_l + 1
        col = i % 5
        ax_l, ax_y = axes[row_l, col], axes[row_y, col]
        
        # Level Chart
        data = data_results[label]
        c = alert_color if (label == "ミシガン大学消費者態度指数" and data.iloc[-1] < thresholds['michigan_val_min']) or \
           (label == "米10年-2年金利差 (Yield Curve)" and data.iloc[-1] < thresholds['yield_curve_max']) else normal_line
        ax_l.plot(data.index, data.values, color=c, linewidth=2.5, marker='o', markersize=4)
        ax_l.set_title(f"{label} (Level)", fontproperties=prop, fontsize=12)
        if "Curve" in label:
            ax_l.axhline(0, color='white', linewidth=1); ax_l.fill_between(data.index, data.values, 0, where=(data.values < 0), color=alert_color, alpha=0.3)

        # YoY Chart
        yoy = yoy_results[label]
        colors = [alert_color if (label == "非農業部門雇用者数 (NFP)" and v < thresholds['nfp_yoy_min']) or \
                  (label == "失業率" and v > thresholds['unrate_yoy_max']) or \
                  (label == "新規失業保険申請件数 (Claims)" and v > thresholds['claims_yoy_max']) or \
                  (label == "住宅着工件数 (Housing)" and v < thresholds.get('houst_yoy_min', 0)) else normal_bar for v in yoy]
        ax_y.bar(yoy.index, yoy.values, color=colors, alpha=0.8)
        suffix = "(YoY Diff)" if any(x in label for x in ["Curve", "Yield"]) else "(YoY %)"
        ax_y.set_title(f"{label} {suffix}", fontproperties=prop, fontsize=12)
        ax_y.axhline(0, color='white', linewidth=0.8)
        if label in ["消費者物価指数 (CPI)", "PCE デフレーター"]: ax_y.axhline(2.0, color='#ff4444', linestyle='--')

        for ax in [ax_l, ax_y]:
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%y/%m'))
            ax.xaxis.set_major_locator(mdates.MonthLocator(interval=6))
            ax.tick_params(labelsize=10); ax.grid(True, alpha=0.1)

    plt.subplots_adjust(top=0.95, bottom=0.03, hspace=0.45, wspace=0.25)
    plt.savefig(OUTPUT_IMAGE, dpi=300, bbox_inches='tight')

def main():
    try:
        config = load_config(); data, yoy, latest = get_fred_data(config['indicators']); th = config['thresholds']
        with open(OUTPUT_MD, "w", encoding="utf-8") as f: f.write(generate_report(latest, th))
        create_dashboard(data, yoy, th); print("✅ 30-Panel Ultimate Dashboard Complete!")
    except Exception as e: print(f"❌ Error: {e}")

if __name__ == "__main__": main()