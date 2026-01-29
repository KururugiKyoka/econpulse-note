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
    lines = [f"# 【Weekly Macro Data】経済 Macro NOTE", f"📅 *更新日: {today}*", "---", "## 🚨 リセッション・シグナル状況"]
    
    # 簡易判定ロジック
    signals = []
    if latest_values['非農業部門雇用者数 (NFP)']['yoy'] < 0.5: signals.append("⚠️ 雇用成長の危険な鈍化")
    if latest_values['失業率']['yoy'] > 5.0: signals.append("🚨 失業率の急上昇（リセッションの予兆）")
    if latest_values['ミシガン大学消費者態度指数']['value'] < 60: signals.append("📉 消費者センチメントの極端な悪化")
    
    lines.append("\\n".join(signals) if signals else "✅ 現在、明確な警告シグナルは検出されていません。")
    lines.append("---")
    
    for label, v in latest_values.items():
        val = f"{v['value']:.2f}" if any(x in label for x in ["指数", "CPI", "PCE", "利回り", "ドル"]) else f"{v['value']:,}"
        lines.append(f"### {label}\\n* **最新値:** {val}\\n* **前年比:** {v['yoy']:+.2f}%")
    return "\\n".join(lines)

def create_dashboard(data_results, yoy_results):
    plt.style.use('dark_background')
    labels = list(data_results.keys())
    fig, axes = plt.subplots(4, 4, figsize=(24, 18))
    prop = fm.FontProperties(fname=FONT_PATH)
    
    alert_color = '#ff3333' # 警告用（レッド）
    normal_line = '#00ffcc' # 通常時（シアン）
    normal_bar = '#ff66cc'  # 通常時（ピンク）
    
    for i, label in enumerate(labels):
        row, col_base = i // 2, (i % 2) * 2
        
        # --- 実数値グラフの判定と描画 ---
        data = data_results[label]
        color_l = normal_line
        # 特例：ミシガン大学指数が60を下回ったらレッド
        if label == "ミシガン大学消費者態度指数" and data.iloc[-1] < 60:
            color_l = alert_color
            
        axes[row, col_base].plot(data.index, data.values, color=color_l, linewidth=2, marker='o', markersize=4)
        axes[row, col_base].set_title(f"{label} (レベル)", fontproperties=prop, fontsize=11)
        axes[row, col_base].grid(True, alpha=0.15)

        # --- 前年比(YoY)グラフの判定と描画 ---
        yoy = yoy_results[label]
        colors_r = [normal_bar] * len(yoy)
        
        # 条件付き強調ロジック
        for j in range(len(yoy)):
            val = yoy.iloc[j]
            # 1. 雇用の伸びが0.5%未満（減速・収縮）
            if label == "非農業部門雇用者数 (NFP)" and val < 0.5: colors_r[j] = alert_color
            # 2. 失業率の前年比が5%超（急上昇）
            if label == "失業率" and val > 5.0: colors_r[j] = alert_color
            # 3. 小売売上高がマイナス（実質的な景気後退）
            if label == "小売売上高" and val < 0: colors_r[j] = alert_color

        axes[row, col_base + 1].bar(yoy.index, yoy.values, color=colors_r, alpha=0.8)
        axes[row, col_base + 1].set_title(f"{label} (YoY %)", fontproperties=prop, fontsize=11)
        axes[row, col_base + 1].grid(True, alpha=0.15)
        axes[row, col_base + 1].axhline(0, color='white', linewidth=0.5)

    plt.tight_layout()
    plt.savefig(OUTPUT_IMAGE, dpi=150)

def main():
    try:
        config = load_config()
        data, yoy, latest = get_fred_data(config['indicators'])
        with open(OUTPUT_MD, "w", encoding="utf-8") as f:
            f.write(generate_report(latest))
        create_dashboard(data, yoy)
        print("✅ Success! Alert-enhanced dashboard generated.")
    except Exception as e:
        print(f"❌ Error: {e}"); exit(1)

if __name__ == "__main__":
    main()