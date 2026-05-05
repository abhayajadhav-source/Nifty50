import hashlib, random
from datetime import datetime, timedelta
import requests


def get_upstox_quote(instrument_key, access_token):
    """Real-time quote from Upstox v2 API."""
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
    """Last N days of daily candles for ATR
