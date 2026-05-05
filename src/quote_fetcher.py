import hashlib, random
import requests


def get_upstox_quote(instrument_key, access_token):
    """
    Real-time quote from Upstox v2 API.
    Returns prev_close, today's open, current price (LTP), today's low, today's high.
    """
    # Strip any whitespace/newlines that may have been included in the token
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
    
    quote = list(data["data"].values())[0]
    ohlc = quote.get("ohlc", {})
    
    return {
        "prev_close": float(ohlc.get("close", 0)),
        "open": float(ohlc.get("open", 0)),
        "ltp": float(quote.get("last_price", 0)),
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
