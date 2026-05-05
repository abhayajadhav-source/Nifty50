import hashlib, random
import requests


def get_upstox_quote(instrument_key, access_token):
    """
    Real-time quote from Upstox v2 API.
    Returns prev_close, today's open, LTP, today's low, today's high,
    52-week high, and 52-week low.
    """
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
        raise ValueError(f"Empty data for {instrument_key} (possibly invalid ISIN or stock not in F&O)")
    
    quote = list(response_data.values())[0]
    
    if not quote:
        raise ValueError(f"No quote object in response for {instrument_key}")
    
    ohlc = quote.get("ohlc") or {}
    
    prev_close = ohlc.get("close", 0)
    open_price = ohlc.get("open", 0)
    ltp = quote.get("last_price", 0)
    
    if not all([prev_close, open_price, ltp]):
        raise ValueError(f"Incomplete OHLC data for {instrument_key}: prev={prev_close}, open={open_price}, ltp={ltp}")
    
    # 52-week high/low — Upstox returns these in the quote object
    week52_high = quote.get("upper_circuit_limit") or 0  # placeholder; real field below
    week52_low = quote.get("lower_circuit_limit") or 0
    
    # The actual 52-week fields in Upstox v2 response:
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


def get_mock_quote(name):
    """Synthetic quote for dry runs. Deterministic per stock name."""
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
    
    # Mock 52-week high/low — make some stocks near their high/low
    breakout_chance = random.random()
    if breakout_chance < 0.15:
        # Near 52-week high
        week52_high = ltp * 0.998
        week52_low = ltp * 0.65
    elif breakout_chance < 0.30:
        # Near 52-week low
        week52_high = ltp * 1.45
        week52_low = ltp * 1.002
    else:
        week52_high = ltp * 1.30
        week52_low = ltp * 0.70
    
    return {
        "prev_close": prev, "open": open_p, "ltp": ltp,
        "low": low, "high": high,
        "week52_high": round(week52_high, 2),
        "week52_low": round(week52_low, 2),
    }
