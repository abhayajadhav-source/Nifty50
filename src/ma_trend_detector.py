from dataclasses import dataclass
from datetime import datetime
from typing import Optional, List
import pytz

IST = pytz.timezone("Asia/Kolkata")


@dataclass
class MATrendSignal:
    symbol: str
    name: str
    direction: str
    current_price: float
    ema_fast: float
    ema_slow: float
    distance_from_fast_pct: float
    suggested_entry: float
    suggested_stop_loss: float
    suggested_target: float


# Tunable
EARLIEST_TIME_IST = (10, 30)
LATEST_TIME_IST = (14, 30)  # 10:30 + 4 hours
EMA_FAST_PERIOD = 9
EMA_SLOW_PERIOD = 21
PULLBACK_PCT = 0.3   # how close to fast EMA counts as a pullback (%)
RISING_BARS = 3      # fast EMA must rise this many bars in a row
STOP_LOSS_PCT = 0.30


def is_within_window():
    now = datetime.now(IST)
    minutes = now.hour * 60 + now.minute
    earliest = EARLIEST_TIME_IST[0] * 60 + EARLIEST_TIME_IST[1]
    latest = LATEST_TIME_IST[0] * 60 + LATEST_TIME_IST[1]
    return earliest <= minutes <= latest


def calculate_ema(values: List[float], period: int) -> Optional[List[float]]:
    """Returns list of EMAs (same length as values, with first period-1 entries being None placeholders)."""
    if not values or len(values) < period:
        return None
    
    multiplier = 2 / (period + 1)
    emas = [None] * (period - 1)
    
    # Start with SMA for first EMA value
    sma = sum(values[:period]) / period
    emas.append(sma)
    
    for i in range(period, len(values)):
        ema = (values[i] - emas[-1]) * multiplier + emas[-1]
        emas.append(ema)
    
    return emas


def analyze_ma_trend(symbol, name, current_price, candles) -> Optional[MATrendSignal]:
    """
    Detects sustained MA trend with pullback entry.
    candles: list of dicts with 'close' (oldest first)
    """
    if not is_within_window():
        return None
    
    if not candles or len(candles) < EMA_SLOW_PERIOD + RISING_BARS:
        return None
    
    closes = [c["close"] for c in candles]
    ema_fast_list = calculate_ema(closes, EMA_FAST_PERIOD)
    ema_slow_list = calculate_ema(closes, EMA_SLOW_PERIOD)
    
    if not ema_fast_list or not ema_slow_list:
        return None
    
    ema_fast = ema_fast_list[-1]
    ema_slow = ema_slow_list[-1]
    
    if ema_fast is None or ema_slow is None:
        return None
    
    # Check direction of fast EMA over last RISING_BARS bars
    recent_fast = [v for v in ema_fast_list[-RISING_BARS - 1:] if v is not None]
    if len(recent_fast) < RISING_BARS + 1:
        return None
    
    is_rising = all(recent_fast[i] > recent_fast[i - 1] for i in range(1, len(recent_fast)))
    is_falling = all(recent_fast[i] < recent_fast[i - 1] for i in range(1, len(recent_fast)))
    
    distance_from_fast = ((current_price - ema_fast) / ema_fast) * 100
    abs_distance = abs(distance_from_fast)
    
    # Bullish trend: price > fast > slow, fast rising, current near fast (pullback to MA)
    if is_rising and current_price > ema_fast > ema_slow and abs_distance <= PULLBACK_PCT:
        direction = "BUY"
        entry = current_price
        stop_loss = entry * (1 - STOP_LOSS_PCT / 100)
        # Target: 2x risk
        target = entry + (entry - stop_loss) * 2
    # Bearish trend: price < fast < slow, fast falling, current near fast (pullback to MA)
    elif is_falling and current_price < ema_fast < ema_slow and abs_distance <= PULLBACK_PCT:
        direction = "SELL"
        entry = current_price
        stop_loss = entry * (1 + STOP_LOSS_PCT / 100)
        target = entry - (stop_loss - entry) * 2
    else:
        return None
    
    return MATrendSignal(
        symbol=symbol, name=name, direction=direction,
        current_price=round(current_price, 2),
        ema_fast=round(ema_fast, 2),
        ema_slow=round(ema_slow, 2),
        distance_from_fast_pct=round(distance_from_fast, 2),
        suggested_entry=round(entry, 2),
        suggested_stop_loss=round(stop_loss, 2),
        suggested_target=round(target, 2),
    )
