from pathlib import Path
import yaml
import pandas as pd
import matplotlib.pyplot as plt

from fetchers.bls import fetch_bls_latest
from fetchers.fred import fetch_fred_latest


import argparse
import calendar
import datetime as dt
from zoneinfo import ZoneInfo

JST = ZoneInfo("Asia/Tokyo")

def should_run(now: dt.datetime) -> bool:
    d = now.astimezone(JST).date()
    last = calendar.monthrange(d.year, d.month)[1]
    return (d.day == 16) or (d.day == last)

FETCHERS = {"bls": fetch_bls_latest, "fred": fetch_fred_latest}

def build_markdown(df: pd.DataFrame) -> str:
    lines = [
        "| 分類 | 指標 | 対象期 | 結果 | 予測 | 前回 |",
        "|---|---|---:|---:|---:|---:|"
    ]
    for _, r in df.iterrows():
        lines.append(
            f'| {r["bucket"]} | {r["label"]} | {r["period"]} | {r["actual"]} | {r["consensus"]} | {r["previous"]} |'
        )
    return "\n".join(lines)

def render_png(df: pd.DataFrame, out_path: Path, title: str):
    import matplotlib.font_manager as fm

    # 日本語フォントを優先して見つける（見つからなければDejaVuにフォールバック）
    candidates = [
        "Noto Sans CJK JP",
        "Noto Sans JP",
        "Hiragino Sans",
        "YuGothic",
        "Apple SD Gothic Neo",
        "AppleGothic",
        "DejaVu Sans",
    ]
font_path = None
    for name in candidates:
        try:
            path = fm.findfont(fm.FontProperties(family=name), fallback_to_default=False)
            font_path = path
            break
        except Exception:
            continue

    fp = fm.FontProperties(fname=font_path) if font_path else fm.FontProperties()

    import matplotlib.pyplot as plt
    plt.rcParams["axes.unicode_minus"] = False

    fig = plt.figure(figsize=(14, max(4, 0.45 * (len(df)+1))), dpi=150)
    ax = fig.add_subplot(111)
    ax.axis("off")

    ax.set_title(title, loc="left", fontsize=14, fontproperties=fp)

    table = ax.table(
        cellText=df[["bucket","label","period","actual","consensus","previous"]].values,
        colLabels=["分類","指標","対象期","結果","予測","前回"],
        loc="upper left",
        cellLoc="left",
        colLoc="left"
    )

    # テーブルの全セル文字にフォントを適用
    table.auto_set_font_size(False)
    table.set_fontsize(10)
    table.scale(1, 1.2)

    for cell in table.get_celld().values():
        cell.get_text().set_fontproperties(fp)

    fig.tight_layout()
    fig.savefig(out_path, bbox_inches="tight")
    plt.close(fig)

def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('--force', action='store_true', help='日付に関係なく実行')
    args = ap.parse_args(argv)

    if (not args.force) and (not should_run(dt.datetime.now(JST))):
        print('Skip: not scheduled day (run on 16th or month-end). Use --force to override.')
        return
    cfg_path = Path("config/indicators.yaml")
    if not cfg_path.exists():
        raise FileNotFoundError("config/indicators.yaml が見つかりません")

    cfg = yaml.safe_load(cfg_path.read_text(encoding="utf-8"))
    indicators = cfg.get("indicators", [])
    if not indicators:
        raise ValueError("indicators.yaml の indicators が空です")

    rows = []
    for ind in indicators:
        fetcher = FETCHERS[ind["source"]]
        actual = fetcher(ind)
        rows.append({
            "bucket": ind["bucket"],
            "label": ind["label"],
            "period": actual.get("period",""),
            "actual": actual.get("value",""),
            "previous": actual.get("previous",""),
            "consensus": "",  # 予測は取れたら後で埋める
        })

    df = pd.DataFrame(rows)

    out_dir = Path("output")
    out_dir.mkdir(exist_ok=True)

    md_path = out_dir / "note_table.md"
    png_path = out_dir / "note_table.png"
    csv_path = out_dir / "raw.csv"

    md_path.write_text(build_markdown(df), encoding="utf-8")
    render_png(df, png_path, "日米 主要経済指標（テスト）")
    df.to_csv(csv_path, index=False, encoding="utf-8")

    print("OK:", md_path, png_path, csv_path)

if __name__ == "__main__":
    main()
