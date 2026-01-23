import os
import yaml
import requests
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib as mpl

# Mac用フォント設定
mpl.rcParams['font.family'] = 'Hiragino Sans'

API_KEY = os.getenv("FRED_API_KEY", "YOUR_DIRECT_KEY_HERE")
CONFIG_PATH = "config/indicators.yml"
OUTPUT_DIR = "output"

def fetch_fred(series_id, units="lin"):
    url = f"https://api.stlouisfed.org/fred/series/observations?series_id={series_id}&api_key={API_KEY}&file_type=json&sort_order=desc&limit=10&units={units}"
    try:
        res = requests.get(url, timeout=10).json()
        obs = [o for o in res['observations'] if o['value'] != '.']
        if len(obs) < 2: return None
        # 小数点第2位に丸めて、投資家が見慣れた数値にする
        return {"actual": round(float(obs[0]['value']), 2), "previous": round(float(obs[1]['value']), 2)}
    except Exception: return None

def main():
    if not os.path.exists(OUTPUT_DIR): os.makedirs(OUTPUT_DIR)
    with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
        conf = yaml.safe_load(f)

    results = []
    print("--- 経済指標（実戦データ）を取得中... ---")
    for ind in conf['indicators']:
        data = fetch_fred(ind['id'], units=ind.get('units', 'lin'))
        if not data: continue
        
        diff = data['actual'] - data['previous']
        # 0.01以下の微細な動きは「→(中立)」と判定するロジック
        trend = "↑" if diff > 0.01 else "↓" if diff < -0.01 else "→"
        is_pos = (diff > 0) if not ind.get('invert', False) else (diff < 0)
        eval_text = "強い" if is_pos else "弱い"
        if abs(diff) <= 0.01: eval_text = "中立"

        results.append({
            "カテゴリ": ind['bucket'], 
            "指標名": ind['label'],
            "最新値": f"{data['actual']}{ind.get('unit','')}", 
            "前回値": f"{data['previous']}{ind.get('unit','')}",
            "トレンド": trend, 
            "評価": eval_text
        })

    df = pd.DataFrame(results)
    df.to_markdown(f"{OUTPUT_DIR}/note_table.md", index=False)

    # --- デザイン性の高いPNG生成 ---
    fig, ax = plt.subplots(figsize=(12, len(df)*0.6 + 1.2))
    ax.axis('off')
    tbl = ax.table(cellText=df.values, colLabels=df.columns, loc='center', cellLoc='center')
    
    # フォントサイズとセルの高さ調整
    tbl.auto_set_font_size(False)
    tbl.set_fontsize(11)
    tbl.scale(1.2, 2.0)
    
    # ヘッダーを「経済 Macro NOTE」風のダークカラーに
    for i in range(len(df.columns)):
        tbl[0, i].set_facecolor('#2C3E50')  # ネイビーグレー
        tbl[0, i].get_text().set_color('white')
        tbl[0, i].get_text().set_weight('bold')

    plt.savefig(f"{OUTPUT_DIR}/note_table.png", bbox_inches='tight', dpi=150)
    print(f"--- 完了！ ---")
    print(f"生成パス: {os.path.abspath(OUTPUT_DIR)}/note_table.png")

if __name__ == "__main__":
    main()