from dataclasses import dataclass
from datetime import datetime
from typing import Optional
import pytz

IST = pytz.timezone("Asia/Kolkata")


@dataclass
class CPRBOSignal:
    symbol: str
    name: str
    direction: str
    pivot: float
    bc: float
    tc: float
    cpr_width_pct: float
    morning_high: float
    morning_low: float
    current_price: float
    breakout_level: float
    suggested_entry: float
    suggested_stop_loss: float
    suggested_target: float


# Tunable
EARLIEST_TIME_IST = (13, 0)
LATEST_TIME_IST = (15, 0)
MAX_CPR_WIDTH_PCT = 0.5  # narrow CPR = better breakout (wider CPR = sideways stock)
STOP_LOSS_PCT = 0.30


def is_within_window():
    now = datetime.now(IST)
    minutes = now.hour * 60 + now.minute
    earliest = EARLIEST_TIME_IST[0] * 60 + EARLIEST_TIME_IST[1]
    latest = LATEST_TIME_IST[0] * 60 + LATEST_TIME_IST[1]
    return earliest <= minutes <= latest


def calculate_cpr(yesterday_ohlc):
    """Calculate Central Pivot Range from yesterday's OHLC."""
    high = yesterday_ohlc["high"]
    low = yesterday_ohlc["low"]
    close = yesterday_ohlc["close"]
    
    pivot = (high + low + close) / 3
    bc = (high + low) / 2  # Bottom Central
    tc = 2 * pivot - bc    # Top Central
    
    # Sometimes BC > TC depending on price action; ensure tc > bc
    if tc < bc:
        tc, bc = bc, tc
    
    return {"pivot": pivot, "bc": bc, "tc": tc}


def analyze_cprbo(symbol, name, current_price, today_low, today_high,
                  morning_high, morning_low, yesterday_ohlc) -> Optional[CPRBOSignal]:
    """
    Detects late-day breakout above/below morning range,
    when stock has been trading on one side of CPR all day.
    """
    if not is_within_window():
        return None
    
    if not yesterday_ohlc or not morning_high or not morning_low:
        return None
    
    cpr = calculate_cpr(yesterday_ohlc)
    pivot, bc, tc = cpr["pivot"], cpr["bc"], cpr["tc"]
    
    # Filter: CPR width — narrow CPR signals trending day potential
    cpr_width_pct = ((tc - bc) / pivot) * 100
    if cpr_width_pct > MAX_CPR_WIDTH_PCT:
        return None
    
    # Bullish CPRBO: today's low has been above CPR top all day, AND current breaks morning_high
    if today_low > tc and current_price > morning_high:
        direction = "BUY"
        breakout_level = morning_high
        entry = current_price
        stop_loss = entry * (1 - STOP_LOSS_PCT / 100)
        target = entry + (morning_high - morning_low)  # measured move
    # Bearish CPRBO: today's high entirely below CPR bottom, AND current breaks morning_low
    elif today_high < bc and current_price < morning_low:
        direction = "SELL"
        breakout_level = morning_low
        entry = current_price
        stop_loss = entry * (1 + STOP_LOSS_PCT / 100)
        target = entry - (morning_high - morning_low)
    else:
        return None
    
    return CPRBOSignal(
        symbol=symbol, name=name, direction=direction,
        pivot=round(pivot, 2),
        bc=round(bc, 2),
        tc=round(tc, 2),
        cpr_width_pct=round(cpr_width_pct, 3),
        morning_high=round(morning_high, 2),
        morning_low=round(morning_low, 2),
        current_price=round(current_price, 2),
        breakout_level=round(breakout_level, 2),
        suggested_entry=round(entry, 2),
        suggested_stop_loss=round(stop_loss, 2),
        suggested_target=round(target, 2),
    )
