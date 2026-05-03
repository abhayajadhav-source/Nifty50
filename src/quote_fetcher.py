import yfinance as yf
import hashlib, random
from datetime import datetime
import pytz

IST = pytz.timezone("Asia/Kolkata")

def get_yahoo_quote(yahoo_symbol):
    """
    Returns prev_close (yesterday's close), today's open, current price (LTP),
    today's low, and today's high using Yahoo Finance.
    Yahoo data for NSE has ~15 min delay on free tier.
    """
    ticker = yf.Ticker(yahoo_symbol)
    
    # 2-day daily history → yesterday's close + today's OHLC
    hist = ticker.history(period="2d", interval="1d")
    if len(hist) < 2:
        raise ValueError(f"Insufficient history for {yahoo_symbol}")
    
    prev_close = float(hist["Close"].iloc[-2])
    today_open = float(hist["Open"].iloc[-1])
    
    # 1-min intraday for current price + today's low/high
    intraday = ticker.history(period="1d", interval="1m")
    if len(intraday) == 0:
        # market just opened, fall back to daily
        return {
            "prev_close": prev_close,
            "open": today_open,
            "ltp": float(hist["Close"].iloc[-1]),
            "low": float(hist["Low"].iloc[-1]),
            "high": float(hist["High"].iloc[-1]),
        }
    
    return {
        "prev_close": prev_close,
        "open": today_open,
        "ltp": float(intraday["Close"].iloc[-1]),
        "low": float(intraday["Low"].min()),
        "high": float(intraday["High"].max()),
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
