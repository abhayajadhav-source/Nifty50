import hashlib, random
import requests


def get_upstox_quote(instrument_key, access_token):
    """
    Real-time quote from Upstox v2 API.
    Returns prev_close, today's open, current price (LTP), today's low, today's high.
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
    
    # Upstox returns key as "NSE_EQ:INE..." (with colon) — handle any key format
    quote = list(response_data.values())[0]
    
    if not quote:
        raise ValueError(f"No quote object in response for {instrument_key}")
    
    ohlc = quote.get("ohlc") or {}
    
    prev_close = ohlc.get("close", 0)
    open_price = ohlc.get("open", 0)
    ltp = quote.get("last_price", 0)
    
    if not all([prev_close, open_price, ltp]):
        raise ValueError(f"Incomplete OHLC data for {instrument_key}: prev={prev_close}, open={open_price}, ltp={ltp}")
    
    return {
        "prev_close": float(prev_close),
        "open": float(open_price),
        "ltp": float(ltp),
        "low": float(ohlc.get("low", 0)),
        "high": float(ohlc.get("high", 0)),
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
    return {"prev_close": prev, "open": open_p, "ltp": ltp, "low": low, "high": high}
