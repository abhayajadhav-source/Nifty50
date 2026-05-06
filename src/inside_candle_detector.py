from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Dict
import pytz

IST = pytz.timezone("Asia/Kolkata")


@dataclass
class InsideCandleSignal:
    symbol: str
    name: str
    direction: str
    mc_high: float            # mother candle high
    mc_low: float             # mother candle low
    mc_range: float           # MC high - low
    mc_range_atr_multiple: float
    today_high_so_far: float
    today_low_so_far: float
    current_price: float
    breakout_level: float
    breakout_pct: float
    suggested_entry: float
    suggested_stop_loss: float
    suggested_target: float


# Tunable parameters
EARLIEST_TIME_IST = (9, 30)
LATEST_TIME_IST = (14, 30)
MIN_MC_RANGE_ATR_MULTIPLE = 0.7    # MC must have meaningful range
BREAKOUT_BUFFER_PCT = 0.15          # how much price must clear MC high/low
MAX_INSIDE_BREACH_PCT = 0.1         # tolerance for "inside" check
STOP_LOSS_PCT = 0.30
TARGET_RR_MULTIPLE = 1.5             # target = 1.5x risk


def is_within_window():
    now = datetime.now(IST)
    minutes = now.hour * 60 + now.minute
    earliest = EARLIEST_TIME_IST[0] * 60 + EARLIEST_TIME_IST[1]
    latest = LATEST_TIME_IST[0] * 60 + LATEST_TIME_IST[1]
    return earliest <= minutes <= latest


def is_inside_candle_setup(today_high: float, today_low: float,
                           mc_high: float, mc_low: float,
                           tolerance_pct: float = MAX_INSIDE_BREACH_PCT) -> bool:
    """
    Returns True if today's range so far is inside the mother candle's range.
    Allows tiny breaches (within tolerance) to handle wicks.
    """
    if not all([today_high, today_low, mc_high, mc_low]):
        return False
    
    # Today's high should not exceed MC high by more than tolerance
    high_breach_pct = ((today_high - mc_high) / mc_high) * 100
    if high_breach_pct > tolerance_pct:
        return False
    
    # Today's low should not be below MC low by more than tolerance
    low_breach_pct = ((mc_low - today_low) / mc_low) * 100
    if low_breach_pct > tolerance_pct:
        return False
    
    return True


def analyze_inside_candle(symbol, name, current_price, today_high, today_low,
                          yesterday_ohlc, atr) -> Optional[InsideCandleSignal]:
    """
    Detects breakout from an inside candle (halt) pattern.
    yesterday_ohlc: dict with 'high', 'low', 'close' from yesterday
    atr: 14-day ATR for filter
    """
    if not is_within_window():
        return None
    
    if not yesterday_ohlc or not atr:
        return None
    
    mc_high = yesterday_ohlc.get("high", 0)
    mc_low = yesterday_ohlc.get("low", 0)
    
    if not mc_high or not mc_low or mc_high <= mc_low:
        return None
    
    mc_range = mc_high - mc_low
    mc_range_atr_multiple = mc_range / atr
    
    # MC must have meaningful range
    if mc_range_atr_multiple < MIN_MC_RANGE_ATR_MULTIPLE:
        return None
    
    # Need to have had an inside-candle pattern earlier in the day
    # (Today's high/low must be roughly inside MC range, or just barely escaping at the breakout)
    # Detect breakout direction
    
    # Bullish breakout: current price clears MC high
    breakout_threshold_high = mc_high * (1 + BREAKOUT_BUFFER_PCT / 100)
    if current_price >= breakout_threshold_high and today_high >= mc_high:
        # Confirm pattern: today_low must have stayed roughly inside
        # (i.e., today's low ≥ MC low; a small breach is OK)
        low_breach_pct = ((mc_low - today_low) / mc_low) * 100 if today_low else 100
        if low_breach_pct > MAX_INSIDE_BREACH_PCT * 3:
            return None  # already broke down before breaking up — not clean
        
        direction = "BUY"
        breakout_level = mc_high
        entry = current_price
        # SL: tighter of MC low or 0.30% from entry
        sl_from_pct = entry * (1 - STOP_LOSS_PCT / 100)
        sl_from_mc = mc_low
        # Use the higher (tighter) stop
        stop_loss = max(sl_from_pct, sl_from_mc)
        risk = entry - stop_loss
        target = entry + risk * TARGET_RR_MULTIPLE
        breakout_pct = ((current_price - mc_high) / mc_high) * 100
    
    # Bearish breakdown: current price below MC low
    elif current_price <= mc_low * (1 - BREAKOUT_BUFFER_PCT / 100) and today_low <= mc_low:
        # Confirm pattern: today_high must have stayed roughly inside
        high_breach_pct = ((today_high - mc_high) / mc_high) * 100 if today_high else 100
        if high_breach_pct > MAX_INSIDE_BREACH_PCT * 3:
            return None
