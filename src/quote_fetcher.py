import hashlib
import random
from datetime import datetime, timedelta
import requests


def get_upstox_quote(instrument_key, access_token):
    clean_token = (access_token or "").strip()
    headers = {
        "Authorization": f"Bearer {clean_token}",
        "Accept": "application/json",
    }
    url = f"https://api.upstox.com/v2/market-quote/quotes?instrument_key={instrument_key}"

    r = requests.get(url, headers=headers, timeout=10)
    if r.status_code != 200:
        raise ValueError(f"Upstox API error {r.status_code}: {r.text[:200]}")

    data = r.json()
    if data.get("status") != "success":
        raise ValueError(f"Upstox returned non-success: {str(data)[:200]}")

    response_data = data.get("data", {})
    if not response_data:
        raise ValueError(f"Empty data for {instrument_key}")

    quote = list(response_data.values())[0]
    if not quote:
        raise ValueError(f"No quote object for {instrument_key}")

    ohlc = quote.get("ohlc") or {}
    prev_close = ohlc.get("close", 0)
    open_price = ohlc.get("open", 0)
    ltp = quote.get("last_price", 0)

    if not all([prev_close, open_price, ltp]):
        raise ValueError(f"Incomplete OHLC for {instrument_key}")

    week52_high = quote.get("week_52_high") or quote.get("year_high") or 0
    week52_low = quote.get("week_52_low") or quote.get("year_low") or 0

    return {
        "prev_close": float(prev_close),
        "open": float(open_price),
        "ltp": float(ltp),
        "low": float(ohlc.get("low", 0)),
        "high": float(ohlc.get("high", 0)),
        "week52_high": float(week52_high),
        "week52_low": float(week52_low),
    }


def get_upstox_daily_candles(instrument_key, access_token, days=20):
    clean_token = (access_token or "").strip()
    headers = {
        "Authorization": f"Bearer {clean_token}",
        "Accept": "application/json",
    }

    to_date = datetime.now().strftime("%Y-%m-%d")
    from_date = (datetime.now() - timedelta(days=days + 10)).strftime("%Y-%m-%d")

    encoded_key = instrument_key.replace("|", "%7C")
    url = f"https://api.upstox.com/v2/historical-candle/{encoded_key}/day/{to_date}/{from_date}"

    r = requests.get(url, headers=headers, timeout=15)
    if r.status_code != 200:
        raise ValueError(f"Upstox candles error {r.status_code}: {r.text[:200]}")

    data = r.json()
    if data.get("status") != "success":
        raise ValueError(f"Upstox candles non-success: {str(data)[:200]}")

    candles = data.get("data", {}).get("candles", [])
    return [
        {"high": float(c[2]), "low": float(c[3]), "close": float(c[4])}
        for c in candles[-days:]
    ]


def get_upstox_intraday_candles(instrument_key, access_token, interval="30minute"):
    clean_token = (access_token or "").strip()
    headers = {
        "Authorization": f"Bearer {clean_token}",
        "Accept": "application/json",
    }

    encoded_key = instrument_key.replace("|", "%7C")
    url = f"https://api.upstox.com/v2/historical-candle/intraday/{encoded_key}/{interval}"

    r = requests.get(url, headers=headers, timeout=15)
    if r.status_code != 200:
        raise ValueError(f"Upstox intraday error {r.status_code}: {r.text[:200]}")

    data = r.json()
    if data.get("status") != "success":
        raise ValueError(f"Upstox intraday non-success: {str(data)[:200]}")

    candles = data.get("data", {}).get("candles", [])
    candles_oldest_first = list(reversed(candles))
    return [
        {"high": float(c[2]), "low": float(c[3]), "close": float(c[4])}
        for c in candles_oldest_first
    ]


def get_upstox_yesterday_ohlc(instrument_key, access_token):
    candles = get_upstox_daily_candles(instrument_key, access_token, days=2)
    if len(candles) < 1:
        raise ValueError(f"No daily candle for {instrument_key}")
    yesterday = candles[-1]
    return {
        "high": yesterday["high"],
        "low": yesterday["low"],
        "close": yesterday["close"],
    }


def get_mock_quote(name):
    seed = int(hashlib.md5(name.encode()).hexdigest(), 16) % 10000
    random.seed(seed)
    prev = round(random.uniform(500, 3000), 2)
    gap = random.choice([-1.5, -1.2, 0.3, 1.1, 1.5])
    open_p = round(prev * (1 + gap / 100), 2)
    retrace = random.uniform(0.50, 0.80)
    if gap > 0:
        ltp = round(open_p * (1 - retrace / 100), 2)
        low, high = ltp, open_p
    else:
        ltp = round(open_p * (1 + retrace / 100), 2)
        low, high = open_p, ltp

    breakout_chance = random.random()
    if breakout_chance < 0.15:
        week52_high = ltp * 0.998
        week52_low = ltp * 0.65
    elif breakout_chance < 0.30:
        week52_high = ltp * 1.45
        week52_low = ltp * 1.002
    else:
        week52_high = ltp * 1.30
        week52_low = ltp * 0.70

    return {
        "prev_close": prev,
        "open": open_p,
        "ltp": ltp,
        "low": low,
        "high": high,
        "week52_high": round(week52_high, 2),
        "week52_low": round(week52_low, 2),
    }


def get_mock_candles(name, days=14):
    seed = int(hashlib.md5(name.encode()).hexdigest(), 16) % 10000
    random.seed(seed)
    base_price = random.uniform(500, 3000)
    candles = []
    price = base_price
    for _ in range(days):
        daily_range = price * random.uniform(0.01, 0.025)
        high = price + daily_range / 2
        low = price - daily_range / 2
        close = random.uniform(low, high)
        candles.append({"high": round(high, 2), "low": round(low, 2), "close": round(close, 2)})
        price = close * (1 + random.uniform(-0.01, 0.01))
    return candles


def get_mock_intraday_candles(name, count=12):
    seed = int(hashlib.md5(name.encode()).hexdigest(), 16) % 10000
    random.seed(seed + 99)
    base_price = random.uniform(500, 3000)
    candles = []
    price = base_price
    trend = random.choice([-1, 0, 1])
    for _ in range(count):
        bar_range = price * random.uniform(0.002, 0.008)
        high = price + bar_range / 2
        low = price - bar_range / 2
        close = random.uniform(low, high)
        candles.append({"high": round(high, 2), "low": round(low, 2), "close": round(close, 2)})
        price = close * (1 + trend * 0.001 + random.uniform(-0.001, 0.001))
    return candles


def get_mock_yesterday_ohlc(name):
    seed = int(hashlib.md5(name.encode()).hexdigest(), 16) % 10000
    random.seed(seed + 50)
    base = random.uniform(500, 3000)
    daily_range = base * random.uniform(0.01, 0.025)
    return {
        "high": round(base + daily_range / 2, 2),
        "low": round(base - daily_range / 2, 2),
        "close": round(random.uniform(base - daily_range / 4, base + daily_range / 4), 2),
    }
