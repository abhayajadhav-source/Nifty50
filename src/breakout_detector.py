from dataclasses import dataclass
from enum import Enum
from typing import Optional


class BreakoutType(Enum):
    HIGH_BREAKOUT = "52W_HIGH_BREAKOUT"
    LOW_BREAKDOWN = "52W_LOW_BREAKDOWN"


@dataclass
class BreakoutSignal:
    symbol: str
    name: str
    breakout_type: BreakoutType
    current_price: float
    week52_level: float       # the 52w high or low being tested
    distance_pct: float        # how far from the level (negative = past it)
    prev_close: float
    day_change_pct: float


# Tunable: how close to 52w level counts as a breakout signal
# 0.0 = must touch or exceed; 0.5 = within 0.5% counts as approach
NEAR_BREAKOUT_THRESHOLD = 0.0  # strict: must actually break, not just approach


def analyze_breakout(symbol, name, current_price, prev_close,
                     week52_high, week52_low) -> Optional[BreakoutSignal]:
    """
    Detects if current price is breaking 52-week high or low.
    Returns None if no breakout, or a BreakoutSignal otherwise.
    """
    if not week52_high or not week52_low or not current_price or not prev_close:
        return None
    
    day_change_pct = ((current_price - prev_close) / prev_close) * 100
    
    # 52-week HIGH breakout: current price >= week52_high
    high_distance_pct = ((current_price - week52_high) / week52_high) * 100
    if high_distance_pct >= -NEAR_BREAKOUT_THRESHOLD:
        return BreakoutSignal(
            symbol=symbol, name=name,
            breakout_type=BreakoutType.HIGH_BREAKOUT,
            current_price=round(current_price, 2),
            week52_level=round(week52_high, 2),
            distance_pct=round(high_distance_pct, 2),
            prev_close=round(prev_close, 2),
            day_change_pct=round(day_change_pct, 2),
        )
    
    # 52-week LOW breakdown: current price <= week52_low
    low_distance_pct = ((current_price - week52_low) / week52_low) * 100
    if low_distance_pct <= NEAR_BREAKOUT_THRESHOLD:
        return BreakoutSignal(
            symbol=symbol, name=name,
            breakout_type=BreakoutType.LOW_BREAKDOWN,
            current_price=round(current_price, 2),
            week52_level=round(week52_low, 2),
            distance_pct=round(low_distance_pct, 2),
            prev_close=round(prev_close, 2),
            day_change_pct=round(day_change_pct, 2),
        )
    
    return None
