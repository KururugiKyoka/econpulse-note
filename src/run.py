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
    end_date = datetime.date.today()
    start_date = end_date - pd.DateOffset(months=26)
    
    for item in indicators:
        series_id, label = item['id'], item['label']
        series = fred.get_series(series_id, observation_start=start_date)
        series = series.resample('MS').last()
        yoy = (series / series.shift(12) - 1) * 100
        data_results[label] = series.tail(12)
        yoy_results[label] = yoy.tail(12)
        latest_values[label] = {'value': series.iloc[-1], 'yoy': yoy.iloc[-1]}
    return data_results, yoy_results, latest_values

def calculate_recession_probability(latest_values, thresholds):
    """
    先行指標(PMI/Yield)と遅行指標(雇用)を組み合わせた判定ロジック
    """
    signals = 0
    total_checks = 6
    
    if latest_values['非農業部門雇用者数 (NFP)']['yoy'] < thresholds['nfp_yoy_min']: signals += 1
    if latest_values['失業率']['yoy'] > thresholds['unrate_yoy_max']: signals += 1
    if latest_values['ミシガン大学消費者態度指数']['value'] < thresholds['michigan_val_min']: signals += 1
    if latest_values['小売売上高']['yoy'] < thresholds['retail_yoy_min']: signals += 1
    if latest_values['米10年-2年金利差 (Yield Curve)']['value'] < thresholds['yield_curve_max']: signals += 1
    if latest_values['製造業PMI (Manufacturing)']['value'] < thresholds['pmi_min']: signals += 1
    
    prob = int((signals / total_checks) * 100)
    return prob, signals

def generate_report(latest_values, thresholds):
    today = datetime.date.today().strftime("%Y/%m/%d")
    prob, signals_count = calculate_recession_probability(latest_values, thresholds)
    status_msg = "🚨 緊急事態" if prob >= 80 else "⚠️ 警戒" if prob >= 50 else "🧐 経過観察"
    
    lines = [
        f"# 【Weekly Macro Data】経済 Macro NOTE",
        f"📅 *最終更新: {today}*", "---",
        f"## 📊 景気後退予測スコア: {prob}%",
        f"**判定結果: {status_msg}** ({signals_count} / 6 シグナル点灯)",
        "*※先行指標(PMI,金利差)と実体指標を統合した判定*", "---"
    ]
    
    if latest_values['製造業PMI (Manufacturing)']['value'] < thresholds['pmi_min']:
        lines.append(f"- 🔴 **製造業PMI:** 数値 {latest_values['製造業PMI (Manufacturing)']['value']:.1f}。50を割り込み、企業の生産意欲が収縮しています。")
    if latest_values['米10年-2年金利差 (Yield Curve)']['value'] < thresholds['yield_curve_max']:
        lines.append("- 🔴 **債券市場:** 逆イールドが継続しており、将来の景気後退を強く示唆しています。")
    
    lines.append("---")
    for label, v in latest_values.items():
        val = f"{v['value']:.2f}" if any(x in label for x in ["指数", "CPI", "PCE", "Curve", "PMI"]) else f"{v['value']:,}"
        lines.append(f"### {label}\\n* **最新値:** {val} / **前年比:** {v['yoy']:+.2f}%")
    return "\\n".join(lines)

def create_dashboard(data_results, yoy_results, thresholds):
    plt.style.use('dark_background')
    labels = list(data_results.keys())
    fig, axes = plt.subplots(4, 4, figsize=(24, 20))
    prop = fm.FontProperties(fname=FONT_PATH)
    fig.suptitle(f"Weekly Macroeconomic Dashboard (Updated: {datetime.date.today():%Y/%m/%d})", color='white', fontsize=28, fontproperties=prop, y=0.96)
    
    alert_color, normal_line, normal_bar = '#ff3333', '#00ffcc', '#ff66cc'
    
    for i, label in enumerate(labels):
        row, col_base = i // 2, (i % 2) * 2
        ax_l = axes[row, col_base]
        data = data_results[label]
        # アラート判定（実数値）
        c_l = normal_line
        if (label == "ミシガン大学消費者態度指数" and data.iloc[-1] < thresholds['michigan_val_min']) or \
           (label == "米10年-2年金利差 (Yield Curve)" and data.iloc[-1] < thresholds['yield_curve_max']) or \
           (label == "製造業PMI (Manufacturing)" and data.iloc[-1] < thresholds['pmi_min']):
            c_l = alert_color
            
        ax_l.plot(data.index, data.values, color=c_l, linewidth=2.5, marker='o', markersize=5)
        ax_l.set_title(f"{label} (Level)", fontproperties=prop, fontsize=12)
        if label == "製造業PMI (Manufacturing)": ax_l.axhline(50, color='white', linestyle='--', linewidth=1)
        
        ax_r = axes[row, col_base + 1]
        yoy = yoy_results[label]
        # アラート判定（YoY）
        colors_r = [alert_color if (label == "非農業部門雇用者数 (NFP)" and val < thresholds['nfp_yoy_min']) or (label == "失業率" and val > thresholds['unrate_yoy_max']) or (label == "小売売上高" and val < thresholds['retail_yoy_min']) else normal_bar for val in yoy]
        ax_r.bar(yoy.index, yoy.values, color=colors_r, alpha=0.8, width=20)
        ax_r.set_title(f"{label} (YoY %)", fontproperties=prop, fontsize=12)
        ax_r.axhline(0, color='white', linewidth=0.8)
        
        if label in ["消費者物価指数 (CPI)", "PCE デフレーター"]:
            ax_r.axhline(2.0, color='#ff4444', linestyle='--', linewidth=1.5); ax_r.text(yoy.index[0], 2.1, "Target 2.0%", color='#ff4444', fontsize=9, fontproperties=prop)

        for ax in [ax_l, ax_r]:
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%y/%m')); ax.xaxis.set_major_locator(mdates.MonthLocator(interval=3))
            ax.tick_params(labelsize=10); ax.grid(True, alpha=0.15)

    plt.subplots_adjust(top=0.92, bottom=0.05, hspace=0.3, wspace=0.2)
    plt.savefig(OUTPUT_IMAGE, dpi=300, bbox_inches='tight')

def main():
    try:
        config = load_config(); data, yoy, latest = get_fred_data(config['indicators']); th = config['thresholds']
        with open(OUTPUT_MD, "w", encoding="utf-8") as f: f.write(generate_report(latest, th))
        create_dashboard(data, yoy, th); print("✅ Success! PMI-enhanced model deployed.")
    except Exception as e: print(f"❌ Error: {e}"); exit(1)

if __name__ == "__main__":
    main()