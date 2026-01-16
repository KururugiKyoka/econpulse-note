import os
import datetime as dt
from zoneinfo import ZoneInfo
import requests

JST = ZoneInfo("Asia/Tokyo")

def fetch_fred_latest(ind: dict) -> dict:
    api_key = os.environ.get("FRED_API_KEY", "")
    if not api_key:
        raise RuntimeError("FRED_API_KEY is missing")

    sid = ind["series_id"]
    url = "https://api.stlouisfed.org/fred/series/observations"
    params = {
        "series_id": sid,
        "api_key": api_key,
        "file_type": "json",
        "sort_order": "desc",
        "limit": 2
    }
    r = requests.get(url, params=params)
    r.raise_for_status()
    obs = r.json()["observations"]
    latest = obs[0]
    prev = obs[1] if len(obs) > 1 else None

    return {
        "value": latest.get("value", ""),
        "previous": prev.get("value", "") if prev else "",
        "period": latest.get("date", ""),
        "release_date_jst": dt.datetime.now(JST).strftime("%Y-%m-%d"),
    }
