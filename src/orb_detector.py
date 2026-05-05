from dataclasses import dataclass
from datetime import datetime
from typing import Optional
import pytz

IST = pytz.timezone("Asia/Kolkata")


@dataclass
class ORBSignal:
    symbol: str
    name: str
    direction: str          # "BUY" or "SELL"
    or_high: float
    or_low: float
    or_width: float
    or_width_atr_multiple: float
    current_price: float
    breakout_level: float   # the level that was broken
    atr: float
    suggested_entry: float
    suggested_stop_loss: float
    suggested_target: float


# Tunable
OR_END_TIME_IST = (9, 30)        # opening range = 9:15-9:30
LATEST_BREAKOUT_TIME_IST = (13, 30)  # don't fire ORB after 1:30 PM
MIN_OR_ATR = 0.4
MAX_OR_ATR = 1.2
STOP_LOSS_PCT = 0.30


def is_after_or_window():
    now = datetime.now(IST)
    minutes = now.hour * 60 + now.minute
    or_end = OR_END_TIME_IST[0] * 60 + OR_END_TIME_IST[1]
    latest = LATEST_BREAKOUT_TIME_IST[0] * 60 + LATEST_BREAKOUT_TIME_IST[1]
    return or_end <= minutes <= latest


def is_in_or_window():
    """True during 9:15-9:30 IST — when we should be tracking OR high/low."""
    now = datetime.now(IST)
    minutes = now.hour * 60 + now.minute
    market_open = 9 * 60 + 15
    or_end = OR_END_TIME_IST[0] * 60 + OR_END_TIME_IST[1]
    return market_open <= minutes < or_end


def analyze_orb(symbol, name, current_price, today_low, today_high,
                or_high, or_low, atr) -> Optional[ORBSignal]:
    """
    Detects breakout above OR high or below OR low,
    provided OR width is within filter range.
    """
    if not is_after_or_window():
        return None
    
    if not or_high or not or_low or or_high <= or_low:
        return None
    
    if not atr or atr <= 0:
        return None
    
    or_width = or_high - or_low
    or_atr = or_width / atr
    
    if or_atr < MIN_OR_ATR or or_atr > MAX_OR_ATR:
        return None
    
    # Breakout above OR high
    if current_price > or_high:
        direction = "BUY"
        breakout_level = or_high
        entry = current_price
        stop_loss = entry * (1 - STOP_LOSS_PCT / 100)
        target = entry + or_width  # measured move target
    # Breakdown below OR low
    elif current_price < or_low:
        direction = "SELL"
        breakout_level = or_low
        entry = current_price
        stop_loss = entry * (1 + STOP_LOSS_PCT / 100)
        target = entry - or_width
    else:
        return None  # still inside OR
    
    return ORBSignal(
        symbol=symbol, name=name, direction=direction,
        or_high=round(or_high, 2),
        or_low=round(or_low, 2),
        or_width=round(or_width, 2),
        or_width_atr_multiple=round(or_atr, 2),
        current_price=round(current_price, 2),
        breakout_level=round(breakout_level, 2),
        atr=round(atr, 2),
        suggested_entry=round(entry, 2),
        suggested_stop_loss=round(stop_loss, 2),
        suggested_target=round(target, 2),
    )
