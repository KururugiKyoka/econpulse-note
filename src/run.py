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
        try:
            series = fred.get_series(series_id, observation_start=start_date)
            # 月初にリサンプリングして同期
            series = series.resample('MS').last().ffill()
            yoy = (series / series.shift(12) - 1) * 100
            
            data_results[label] = series.tail(12)
            yoy_results[label] = yoy.tail(12)
            latest_values[label] = {'value': series.iloc[-1], 'yoy': yoy.iloc[-1]}
        except Exception as e:
            print(f"❌ {label} ({series_id}) の取得に失敗: {e}")
            continue
    return data_results, yoy_results, latest_values

def calculate_recession_probability(latest_values, thresholds):
    signals, total = 0, 6
    checks = [
        ('非農業部門雇用者数 (NFP)', 'yoy', 'nfp_yoy_min', '<'),
        ('失業率', 'yoy', 'unrate_yoy_max', '>'),
        ('ミシガン大学消費者態度指数', 'value', 'michigan_val_min', '<'),
        ('小売売上高', 'yoy', 'retail_yoy_min', '<'),
        ('米10年-2年金利差 (Yield Curve)', 'value', 'yield_curve_max', '<'),
        ('鉱工業生産指数 (INDPRO)', 'yoy', 'indpro_yoy_min', '<')
    ]
    for label, key, th_key, op in checks:
        if label in latest_values:
            val = latest_values[label][key]
            if (op == '<' and val < thresholds[th_key]) or (op == '>' and val > thresholds[th_key]):
                signals += 1
    prob = int((signals / total) * 100)
    return prob, signals

def generate_report(latest_values, thresholds):
    today = datetime.date.today().strftime("%Y/%m/%d")
    prob, signals = calculate_recession_probability(latest_values, thresholds)
    status = "🚨 緊急事態" if prob >= 80 else "⚠️ 警戒" if prob >= 50 else "🧐 経過観察"
    
    lines = [f"# 【Weekly Macro Data】経済 Macro NOTE", f"📅 *最終更新: {today}*", "---",
             f"## 📊 景気後退予測スコア: {prob}%", f"**判定結果: {status}** ({signals} / 6 シグナル点灯)", "---"]
    
    for label, v in latest_values.items():
        val = f"{v['value']:.2f}" if any(x in label for x in ["指数", "CPI", "PCE", "Curve"]) else f"{v['value']:,}"
        lines.append(f"### {label}\\n* 最新値: {val} / 前年比: {v['yoy']:+.2f}%")
    return "\\n".join(lines)

def create_dashboard(data_results, yoy_results, thresholds):
    plt.style.use('dark_background')
    labels = list(data_results.keys())
    fig, axes = plt.subplots(4, 4, figsize=(24, 20))
    prop = fm.FontProperties(fname=FONT_PATH)
    fig.suptitle(f"Weekly Macroeconomic Dashboard (Updated: {datetime.date.today():%Y/%m/%d})", 
                 color='white', fontsize=28, fontproperties=prop, y=0.96)
    
    alert_color, normal_line, normal_bar = '#ff3333', '#00ffcc', '#ff66cc'
    
    for i in range(16):
        row, col = i // 4, i % 4
        ax = axes[row, col]
        
        # 取得できたラベルの数に合わせて描画
        label_idx = i // 2
        if label_idx >= len(labels):
            ax.set_facecolor('#111111') # 失敗箇所を黒塗りに
            ax.set_xticks([]); ax.set_yticks([])
            continue
            
        label = labels[label_idx]
        is_yoy = i % 2 == 1
        
        if not is_yoy: # 水準(Level)
            data = data_results[label]
            c = alert_color if (label == "ミシガン大学消費者態度指数" and data.iloc[-1] < thresholds['michigan_val_min']) or \
               (label == "米10年-2年金利差 (Yield Curve)" and data.iloc[-1] < thresholds['yield_curve_max']) else normal_line
            ax.plot(data.index, data.values, color=c, linewidth=2.5, marker='o', markersize=5)
            ax.set_title(f"{label} (Level)", fontproperties=prop, fontsize=11)
        else: # 前年比(YoY)
            yoy = yoy_results[label]
            colors = [alert_color if (label == "非農業部門雇用者数 (NFP)" and v < thresholds['nfp_yoy_min']) or \
                      (label == "失業率" and v > thresholds['unrate_yoy_max']) or \
                      (label == "小売売上高" and v < thresholds['retail_yoy_min']) or \
                      (label == "鉱工業生産指数 (INDPRO)" and v < thresholds['indpro_yoy_min']) else normal_bar for v in yoy]
            ax.bar(yoy.index, yoy.values, color=colors, alpha=0.8, width=20)
            ax.set_title(f"{label} (YoY %)", fontproperties=prop, fontsize=11)
            ax.axhline(0, color='white', linewidth=0.8)
            if label in ["消費者物価指数 (CPI)", "PCE デフレーター"]:
                ax.axhline(2.0, color='#ff4444', linestyle='--', linewidth=1.5)

        ax.xaxis.set_major_formatter(mdates.DateFormatter('%y/%m'))
        ax.xaxis.set_major_locator(mdates.MonthLocator(interval=4))
        ax.tick_params(labelsize=9); ax.grid(True, alpha=0.1)

    plt.subplots_adjust(top=0.92, bottom=0.05, hspace=0.35, wspace=0.25)
    plt.savefig(OUTPUT_IMAGE, dpi=300, bbox_inches='tight')

def main():
    try:
        config = load_config(); data, yoy, latest = get_fred_data(config['indicators']); th = config['thresholds']
        with open(OUTPUT_MD, "w", encoding="utf-8") as f: f.write(generate_report(latest, th))
        create_dashboard(data, yoy, th); print("✅ Dashboard Complete!")
    except Exception as e: print(f"❌ Error: {e}"); exit(1)

if __name__ == "__main__":
    main()