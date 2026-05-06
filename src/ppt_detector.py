from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Dict
import pytz

IST = pytz.timezone("Asia/Kolkata")


@dataclass
class PPTSignal:
    symbol: str
    name: str
    direction: str
    pp: float
    r1: float
    r2: float
    s1: float
    s2: float
    pressure_level: float
    pressure_touches: int
    current_price: float
    breakout_pct: float
    suggested_entry: float
    suggested_stop_loss: float
    suggested_target: float


# Tunable
EARLIEST_TIME_IST = (10, 0)
LATEST_TIME_IST = (14, 0)
MIN_PRESSURE_TOUCHES = 2          # how many times price tested the level before breakout
PRESSURE_PROXIMITY_PCT = 0.3      # within this % of level counts as a "touch"
BREAKOUT_THRESHOLD_PCT = 0.2      # how much price must clear the level
MIN_DAY_RANGE_ATR_MULTIPLE = 0.5  # day's range must be >= this × ATR
STOP_LOSS_PCT = 0.30


def is_within_window():
    now = datetime.now(IST)
    minutes = now.hour * 60 + now.minute
    earliest = EARLIEST_TIME_IST[0] * 60 + EARLIEST_TIME_IST[1]
    latest = LATEST_TIME_IST[0] * 60 + LATEST_TIME_IST[1]
    return earliest <= minutes <= latest


def calculate_pivots(yesterday_ohlc: Dict) -> Dict:
    """Standard floor pivot calculation from yesterday's OHLC."""
    h = yesterday_ohlc["high"]
    l = yesterday_ohlc["low"]
    c = yesterday_ohlc["close"]
    
    pp = (h + l + c) / 3
    r1 = 2 * pp - l
    r2 = pp + (h - l)
    s1 = 2 * pp - h
    s2 = pp - (h - l)
    
    return {"pp": pp, "r1": r1, "r2": r2, "s1": s1, "s2": s2}


def is_near_level(price: float, level: float, proximity_pct: float = PRESSURE_PROXIMITY_PCT) -> bool:
    """Returns True if price is within proximity_pct of level."""
    if level == 0:
        return False
    return abs(price - level) / level * 100 <= proximity_pct


def analyze_ppt(symbol, name, current_price, open_price,
                today_high, today_low, yesterday_ohlc,
                pressure_state, atr) -> Optional[PPTSignal]:
    """
    Detects Pivot Pressure breakout.
    pressure_state: dict tracking touch counts {"r1_touches": N, "s1_touches": M}
    """
    if not is_within_window():
        return None
    
    if not yesterday_ohlc or not atr:
        return None
    
    pivots = calculate_pivots(yesterday_ohlc)
    pp, r1, r2, s1, s2 = pivots["pp"], pivots["r1"], pivots["r2"], pivots["s1"], pivots["s2"]
    
    # Day's range filter
    day_range = today_high - today_low
    if day_range < MIN_DAY_RANGE_ATR_MULTIPLE * atr:
        return None
    
    # Determine bias from open
    opened_above_pp = open_price > pp
    opened_below_pp = open_price < pp
    
    # Bullish PPT setup
    if opened_above_pp:
        # Bias maintained: today's low stayed at or above PP
        bias_held = today_low >= pp * 0.998  # small tolerance for wicks
        
        # Pressure has built at R1 (multiple touches)
        r1_touches = pressure_state.get("r1_touches", 0)
        pressure_built = r1_touches >= MIN_PRESSURE_TOUCHES
        
        # Breakout: current price clears R1 decisively
        breakout_threshold_price = r1 * (1 + BREAKOUT_THRESHOLD_PCT / 100)
        broke_out = current_price >= breakout_threshold_price
        
        if bias_held and pressure_built and broke_out:
            entry = current_price
            stop_loss = entry * (1 - STOP_LOSS_PCT / 100)
            # Target: R2 (next resistance after R1)
            target = r2
            breakout_pct = ((current_price - r1) / r1) * 100
            
            return PPTSignal(
                symbol=symbol, name=name, direction="BUY",
                pp=round(pp, 2), r1=round(r1, 2), r2=round(r2, 2),
                s1=round(s1, 2), s2=round(s2, 2),
                pressure_level=round(r1, 2),
                pressure_touches=r1_touches,
                current_price=round(current_price, 2),
                breakout_pct=round(breakout_pct, 2),
                suggested_entry=round(entry, 2),
                suggested_stop_loss=round(stop_loss, 2),
                suggested_target=round(target, 2),
            )
    
    # Bearish PPT setup
    if opened_below_pp:
        # Bias maintained: today's high stayed at or below PP
        bias_held = today_high <= pp * 1.002
        
        # Pressure built at S1
        s1_touches = pressure_state.get("s1_touches", 0)
        pressure_built = s1_touches >= MIN_PRESSURE_TOUCHES
        
        # Breakdown: current price below S1 decisively
        breakdown_threshold_price = s1 * (1 - BREAKOUT_THRESHOLD_PCT / 100)
        broke_down = current_price <= breakdown_threshold_price
        
        if bias_held and pressure_built and broke_down:
            entry = current_price
            stop_loss = entry * (1 + STOP_LOSS_PCT / 100)
            target = s2
            breakout_pct = ((s1 - current_price) / s1) * 100
            
            return PPTSignal(
                symbol=symbol, name=name, direction="SELL",
                pp=round(pp, 2), r1=round(r1, 2), r2=round(r2, 2),
                s1=round(s1, 2), s2=round(s2, 2),
                pressure_level=round(s1, 2),
                pressure_touches=s1_touches,
                current_price=round(current_price, 2),
                breakout_pct=round(breakout_pct, 2),
                suggested_entry=round(entry, 2),
                suggested_stop_loss=round(stop_loss, 2),
                suggested_target=round(target, 2),
            )
    
    return None


def update_pressure_state(current_state: Dict, current_price: float,
                          pivots: Dict) -> Dict:
    """
    Updates pressure touch counts. Called every cron run.
    A 'touch' counts when price comes within PRESSURE_PROXIMITY_PCT of R1 or S1.
    To avoid double-counting in the same cron interval, we only increment 
    if the previous price was NOT near the level.
    """
    new_state = dict(current_state)
    
    near_r1 = is_near_level(current_price, pivots["r1"])
    near_s1 = is_near_level(current_price, pivots["s1"])
    
    was_near_r1 = current_state.get("was_near_r1", False)
    was_near_s1 = current_state.get("was_near_s1", False)
    
    # New touch on R1: was not near, now is near
    if near_r1 and not was_near_r1:
        new_state["r1_touches"] = current_state.get("r1_touches", 0) + 1
    
    # New touch on S1: was not near, now is near
    if near_s1 and not was_near_s1:
        new_state["s1_touches"] = current_state.get("s1_touches", 0) + 1
    
    new_state["was_near_r1"] = near_r1
    new_state["was_near_s1"] = near_s1
    
    return new_state
