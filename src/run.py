import os
import yaml
import requests
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib as mpl
import matplotlib.font_manager as fm
import datetime
import google.generativeai as genai
import sys

# --- 設定 ---
API_KEY = os.getenv("FRED_API_KEY")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
CONFIG_PATH = "config/indicators.yml"
OUTPUT_DIR = "output"

if GOOGLE_API_KEY:
    genai.configure(api_key=GOOGLE_API_KEY)
    ai_model = genai.GenerativeModel('gemini-1.5-flash')

def setup_font():
    local_font = 'ipaexg.ttf'
    if os.path.exists(local_font):
        fm.fontManager.addfont(local_font)
        mpl.rcParams['font.family'] = fm.FontProperties(fname=local_font).get_name()
    elif os.path.exists('/System/Library/Fonts/ヒラギノ角ゴシック W3.ttc'):
        mpl.rcParams['font.family'] = 'Hiragino Sans'
    else:
        mpl.rcParams['font.family'] = 'sans-serif'

setup_font()

def fetch_fred(series_id, units="lin"):
    url = f"https://api.stlouisfed.org/fred/series/observations?series_id={series_id}&api_key={API_KEY}&file_type=json&sort_order=desc&limit=10&units={units}"
    try:
        res = requests.get(url, timeout=10)
        res.raise_for_status()
        data = res.json()
        obs = [o for o in data['observations'] if o['value'] != '.']
        if len(obs) < 2: return None
        return {"actual": round(float(obs[0]['value']), 2), "previous": round(float(obs[1]['value']), 2)}
    except Exception: return None

def generate_ai_analysis(results):
    if not GOOGLE_API_KEY: return "AI分析キー未設定のためスキップ"
    data_str = "\n".join([f"{r[1]}: 最新{r[2]} (判定:{r[5]})" for r in results])
    prompt = f"プロの経済アナリストとして以下のデータから投資家向けnote記事「経済 Macro NOTE (KURURUGI)」の概況文をMarkdown形式で作成してください。\n\n{data_str}"
    try:
        response = ai_model.generate_content(prompt)
        return response.text
    except Exception as e: return f"AI分析エラー: {e}"

def main():
    if not os.path.exists(OUTPUT_DIR): os.makedirs(OUTPUT_DIR)
    with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
        conf = yaml.safe_load(f)

    results = []
    for ind in conf['indicators']:
        data = fetch_fred(ind['id'], units=ind.get('units', 'lin'))
        if data:
            diff = data['actual'] - data['previous']
            trend = "↑" if diff > 0.01 else "↓" if diff < -0.01 else "→"
            is_pos = (diff > 0) if not ind.get('invert', False) else (diff < 0)
            eval_text = "強い" if is_pos else "弱い"
            if abs(diff) <= 0.01: eval_text = "中立"
            results.append([ind['bucket'], ind['label'], f"{data['actual']}{ind.get('unit','')}", f"{data['previous']}{ind.get('unit','')}", trend, eval_text])

    # 1. note用詳細テーブル (プロ仕様)
    fig, ax = plt.subplots(figsize=(14, len(results)*0.8 + 3))
    ax.axis('off')
    plt.text(0.5, 0.96, "経済 Macro NOTE (KURURUGI)", transform=ax.transAxes, ha='center', fontsize=28, fontweight='bold', color='#1A237E')
    plt.text(0.5, 0.91, "Global Market Dashboard", transform=ax.transAxes, ha='center', fontsize=18, color='#555555')
    tbl = ax.table(cellText=results, colLabels=["カテゴリ", "指標名", "最新値", "前回値", "トレンド", "評価"], loc='center', cellLoc='center')
    tbl.auto_set_font_size(False)
    tbl.set_fontsize(13)
    tbl.scale(1.1, 2.8)
    for (row, col), cell in tbl.get_celld().items():
        cell.set_edgecolor('#EEEEEE')
        if row == 0: cell.set_facecolor('#1A237E'), cell.get_text().set_color('white'), cell.get_text().set_weight('bold')
        elif col == 5:
            text = cell.get_text().get_text()
            if text == "強い": cell.get_text().set_color('#D32F2F')
            elif text == "弱い": cell.get_text().set_color('#1976D2')
    plt.savefig(f"{OUTPUT_DIR}/note_table.png", bbox_inches='tight', dpi=160, facecolor='white')

    # 2. SNS用サマリー (重なり解消版)
    fig_sns, ax_sns = plt.subplots(figsize=(12, 6.75))
    ax_sns.axis('off')
    plt.text(0.5, 0.88, "DAILY MACRO HIGHLIGHT", transform=ax_sns.transAxes, ha='center', fontsize=32, fontweight='bold', color='#1A237E')
    plt.text(0.5, 0.80, "経済 Macro NOTE (KURURUGI)", transform=ax_sns.transAxes, ha='center', fontsize=20, color='#666666')
    target_labels = ["フィラデルフィア連銀景況指数", "ドルインデックス (先進国)", "非農業部門雇用者数 (NFP)"]
    picks = [r for r in results if r[1] in target_labels]
    for i, h in enumerate(picks[:3]):
        y = 0.58 - (i * 0.20)
        color = '#D32F2F' if h[5] == "強い" else '#1976D2' if h[5] == "弱い" else '#333333'
        plt.text(0.48, y, h[1], transform=ax_sns.transAxes, ha='right', fontsize=24, fontweight='bold')
        plt.text(0.52, y, f"{h[2]} ({h[4]})", transform=ax_sns.transAxes, ha='left', fontsize=28, color=color, fontweight='bold')
        plt.text(0.50, y - 0.06, f"前回: {h[3]}  /  判定: {h[5]}", transform=ax_sns.transAxes, ha='center', fontsize=14, color='gray')
    plt.savefig(f"{OUTPUT_DIR}/sns_share.png", bbox_inches='tight', dpi=100, facecolor='white')

    # 3. AI分析
    analysis = generate_ai_analysis(results)
    with open(f"{OUTPUT_DIR}/analysis.md", "w", encoding="utf-8") as f:
        f.write(analysis)
    print("✅ 全ての生成が完了しました（プロ仕様デザイン）")

if __name__ == "__main__":
    main()