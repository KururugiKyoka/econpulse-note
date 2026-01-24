import os
import yaml
import datetime
import json
import pandas as pd
from fredapi import Fred
import google.generativeai as genai
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm

# ==========================================
# 1. 環境設定・定数
# ==========================================
FRED_API_KEY = os.getenv("FRED_API_KEY")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
CONFIG_PATH = "config/indicators.yml"
FONT_PATH = "ipaexg.ttf"  # プロジェクトルートに配置されている前提
OUTPUT_IMAGE = "output_sns.png"
OUTPUT_MD = "analysis.md"

# Gemini設定
genai.configure(api_key=GOOGLE_API_KEY)
# 'gemini-1.5-flash' ではなく 'gemini-1.5-flash-latest' またはシンプルに 'gemini-1.5-flash'
# ここでは最も互換性の高い指定方法に変更します
model = genai.GenerativeModel('gemini-1.5-flash')

# ==========================================
# 2. データ取得・処理ロジック
# ==========================================
def load_config():
    with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)

def get_fred_data(indicators):
    fred = Fred(api_key=FRED_API_KEY)
    data_results = {}
    latest_values = {}
    
    for item in indicators:
        series_id = item['id']
        label = item['label']
        # 直近1年分のデータを取得
        series = fred.get_series(series_id)
        data_results[label] = series.tail(12)
        latest_values[label] = series.iloc[-1]
        
    return data_results, latest_values

# ==========================================
# 3. AI分析ロジック (Gemini)
# ==========================================
def analyze_with_gemini(latest_values):
    prompt = f"""
    あなたはプロのマクロ経済アナリストです。以下の最新経済指標データ（FRED）を分析し、
    投資家向けレポート「経済 Macro NOTE (KURURUGI)」の内容を生成してください。

    【データ】
    - 非農業部門雇用者数 (NFP): {latest_values.get('非農業部門雇用者数 (NFP)', 'N/A')}
    - ドルインデックス (DXY): {latest_values.get('ドルインデックス', 'N/A')}
    - 消費者物価指数 (CPI): {latest_values.get('消費者物価指数 (CPI)', 'N/A')}

    【出力ルール】
    必ず以下のキーを持つJSON形式で出力してください。Markdownの装飾はJSON内部には含めず、テキストのみにしてください。
    - summary: 今週の要点3つ（箇条書き形式のテキスト）
    - nfp_insight: 雇用統計から読み取れる労働市場の洞察
    - dxy_trend: ドル指数の短期的なトレンド（上昇/下落/レンジ）
    - dxy_insight: 通貨パワーバランスに関する分析
    - cpi_insight: インフレリスクとFRBの動向予測
    - overall_outlook: 総括と来週の戦略的視点
    """
    
    response = model.generate_content(prompt)
    # JSON部分のみを抽出（```json ... ``` の除去）
    raw_text = response.text.replace('```json', '').replace('```', '').strip()
    return json.loads(raw_text)

# ==========================================
# 4. Markdown生成 (プロフェッショナル版)
# ==========================================
def generate_professional_markdown(analysis, latest_values):
    today = datetime.date.today().strftime("%Y/%m/%d")
    
    template = f"""# 【Weekly Macro Insight】雇用・物価・ドルの連動から読み解く市場の現在地
📅 *作成日: {today}*

---

## 📈 エグゼクティブ・サマリー
今週の主要マクロ指標から見える、投資家が押さえるべき**「3つの要諦」**です。

> {analysis.get('summary', '分析データを生成中...')}

---

## 🔍 指標別ディープ・ダイブ

### 1. 非農業部門雇用者数 (NFP)：労働市場の底堅さ
* **Fact:** 最新値 {latest_values.get('非農業部門雇用者数 (NFP)', '取得失敗')}
* **Insight:** {analysis.get('nfp_insight', '分析中...')}

### 2. ドルインデックス (DXY)：通貨のパワーバランス
| 指標 | 現在値 | トレンド |
| :--- | :--- | :--- |
| **DXY** | {latest_values.get('ドルインデックス', '---')} | {analysis.get('dxy_trend', '---')} |

* **分析の視点:**
{analysis.get('dxy_insight', '分析中...')}

### 3. 消費者物価指数 (CPI)：インフレの再加速リスク
* **注目ポイント:** {analysis.get('cpi_insight', '分析中...')}

---

## 💡 総括と今後の戦略的視点
{analysis.get('overall_outlook', '分析中...')}

---

**経済 Macro NOTE (KURURUGI)**
*本記事は自動データ収集およびAIによる高度分析をベースに構成されています。投資判断は自己責任でお願いいたします。*
"""
    return template

# ==========================================
# 5. 画像生成ロジック (SNS用)
# ==========================================
def create_sns_image(data_results, config):
    plt.style.use('dark_background')
    fig, axes = plt.subplots(1, 3, figsize=(18, 6))
    
    # 日本語フォント設定
    prop = fm.FontProperties(fname=FONT_PATH)
    
    target_labels = config.get('target_labels', list(data_results.keys()))
    
    for i, label in enumerate(target_labels):
        if i >= 3: break
        ax = axes[i]
        df = data_results[label]
        ax.plot(df.index, df.values, color='#00ffcc', linewidth=2)
        ax.set_title(label, fontproperties=prop, fontsize=14)
        ax.grid(alpha=0.2)
        
    plt.tight_layout()
    plt.savefig(OUTPUT_IMAGE)
    print(f"Image saved: {OUTPUT_IMAGE}")

# ==========================================
# 6. メイン実行
# ==========================================
def main():
    print("🚀 Starting Economic Macro Insight generation...")
    
    # 1. 設定読み込み
    config = load_config()
    
    # 2. FREDからデータ取得
    data_results, latest_values = get_fred_data(config['indicators'])
    
    # 3. Geminiで分析
    print("🧠 Analyzing data with Gemini...")
    analysis_json = analyze_with_gemini(latest_values)
    
    # 4. Markdown生成・保存
    print("📝 Generating professional report...")
    final_md = generate_professional_markdown(analysis_json, latest_values)
    with open(OUTPUT_MD, "w", encoding="utf-8") as f:
        f.write(final_md)
    
    # 5. 画像生成
    print("🎨 Creating SNS dashboard...")
    create_sns_image(data_results, config)
    
    print("✅ All processes completed successfully!")

if __name__ == "__main__":
    main()