import datetime as dt
from zoneinfo import ZoneInfo
import requests

JST = ZoneInfo("Asia/Tokyo")
BLS_URL = "https://api.bls.gov/publicAPI/v2/timeseries/data/"

def fetch_bls_latest(ind: dict) -> dict:
    sid = ind["series_id"]
    r = requests.post(BLS_URL, json={"seriesid": [sid]})
    r.raise_for_status()
    js = r.json()

    series = js["Results"]["series"][0]
    data = series["data"]
    latest = data[0]
    prev = data[1] if len(data) > 1 else None

    period = f'{latest["year"]}-{latest["period"]}'
    return {
        "value": latest.get("value", ""),
        "previous": prev.get("value", "") if prev else "",
        "period": period,
        "release_date_jst": dt.datetime.now(JST).strftime("%Y-%m-%d"),
    }
