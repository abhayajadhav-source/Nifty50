from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Dict, List, Tuple
import pytz

IST = pytz.timezone("Asia/Kolkata")


@dataclass
class ScalpingSignal:
    symbol: str
    name: str
    direction: str
    setup_location: str       # 'pdh', 'pdl', 'cpr_tc', 'cpr_bc', 'cpr_pivot', 'ema20'
    candle_pattern: str       # 'bull_maru', 'bear_maru', 'bull_pin', 'bear_pin'
    level_price: float        # the actual PDH/PDL/CPR/EMA level being tested
    candle_open: float
    candle_high: float
    candle_low: float
    candle_close: float
    cpr_pivot: float
    cpr_tc: float
    cpr_bc: float
    cpr_width_pct: float
    pdh: float
    pdl: float
    suggested_entry: float
    suggested_stop_loss: float
    suggested_target: float
    risk_reward: float
    trend: str                # 'up', 'down', 'flat'


# Tunable parameters
EARLIEST_TIME_IST = (9, 30)
LATEST_TIME_IST = (15, 0)

# Candle classification
MARUBOZU_BODY_PCT = 0.80          # body >= 80% of range
PINBAR_BODY_PCT = 0.35            # body <= 35% of range
PINBAR_WICK_RATIO = 2.0           # dominant wick >= 2x body

# Location proximity
PROXIMITY_PCT = 0.0025            # 0.25% from level counts as "at level"

# CPR width
WIDE_CPR_MIN_PCT = 0.005          # CPR width >= 0.5% of price = wide

# 20-EMA pullback
EMA_PERIOD = 20
TREND_LOOKBACK = 20
TREND_SLOPE_MIN = 0.0

# Trade management
TARGET_RR_MULTIPLE = 1.5
STOP_BUFFER_PCT = 0.05            # 0.05% tick buffer beyond candle high/low


def is_within_window():
    now = datetime.now(IST)
    minutes = now.hour * 60 + now.minute
    earliest = EARLIEST_TIME_IST[0] * 60 + EARLIEST_TIME_IST[1]
    latest = LATEST_TIME_IST[0] * 60 + LATEST_TIME_IST[1]
    return earliest <= minutes <= latest


def classify_candle(o: float, h: float, l: float, c: float) -> str:
    """Return one of: bull_maru, bear_maru, bull_pin, bear_pin, none."""
    rng = h - l
    if rng <= 0:
        return "none"
    
    body = abs(c - o)
    upper_wick = h - max(o, c)
    lower_wick = min(o, c) - l
    body_pct = body / rng if rng > 0 else 0
    
    # Marubozu — dominant body, very small wicks
    if body_pct >= MARUBOZU_BODY_PCT:
        return "bull_maru" if c > o else "bear_maru"
    
    # Pin bar — small body with one dominant wick
    if body_pct <= PINBAR_BODY_PCT and body > 0:
        if lower_wick >= PINBAR_WICK_RATIO * body and lower_wick > upper_wick:
            return "bull_pin"
        if upper_wick >= PINBAR_WICK_RATIO * body and upper_wick > lower_wick:
            return "bear_pin"
    
    return "none"


def compute_cpr(prev_h: float, prev_l: float, prev_c: float) -> Dict:
    """CPR levels from previous day's OHLC."""
    pivot = (prev_h + prev_l + prev_c) / 3
    bc = (prev_h + prev_l) / 2
    tc = 2 * pivot - bc
    if tc < bc:
        tc, bc = bc, tc
    width_pct = (tc - bc) / pivot if pivot > 0 else 0
    return {
        "pivot": pivot,
        "tc": tc,
        "bc": bc,
        "width_pct": width_pct,
        "is_wide": width_pct >= WIDE_CPR_MIN_PCT,
    }


def at_level(price: float, level: float, proximity_pct: float = PROXIMITY_PCT) -> bool:
    """Returns True if price within proximity_pct of level."""
    if level == 0:
        return False
    return abs(price - level) / level <= proximity_pct


def candle_touched(low: float, high: float, level: float) -> bool:
    """True if candle range straddles or sits within proximity of the level."""
    if low <= level <= high:
        return True
    return at_level(low, level) or at_level(high, level)


def calculate_ema(prices: List[float], period: int) -> List[float]:
    """Compute EMA series from a list of prices."""
    if len(prices) < period:
        return []
    
    multiplier = 2 / (period + 1)
    ema_values = [sum(prices[:period]) / period]  # SMA as first value
    
    for price in prices[period:]:
        ema_value = (price - ema_values[-1]) * multiplier + ema_values[-1]
        ema_values.append(ema_value)
    
    return ema_values


def determine_trend(ema_values: List[float], lookback: int = TREND_LOOKBACK) -> str:
    """Return 'up', 'down', or 'flat' based on EMA slope."""
    if len(ema_values) < lookback + 1:
        return "flat"
    
    recent = ema_values[-lookback:]
    if recent[0] == 0:
        return "flat"
    slope = (recent[-1] - recent[0]) / recent[0]
    
    if slope > TREND_SLOPE_MIN:
        return "up"
    if slope < -TREND_SLOPE_MIN:
        return "down"
    return "flat"


def analyze_scalping(symbol: str, name: str,
                     intraday_5min_candles: List[Dict],
                     yesterday_ohlc: Dict) -> Optional[ScalpingSignal]:
    """
    Detect scalping setup on the most recent 5-min candle.
    
    intraday_5min_candles: list of dicts with 'open', 'high', 'low', 'close', 'volume'
                         (oldest first, includes current/just-closed candle as last)
    yesterday_ohlc: dict with 'high', 'low', 'close'
    
    Returns ScalpingSignal if a valid setup exists on the latest candle, else None.
    """
    if not is_within_window():
        return None
    
    if not yesterday_ohlc:
        return None
    
    if not intraday_5min_candles or len(intraday_5min_candles) < EMA_PERIOD + 1:
        return None
    
    # Compute PDH/PDL/CPR
    pdh = yesterday_ohlc["high"]
    pdl = yesterday_ohlc["low"]
    cpr = compute_cpr(pdh, pdl, yesterday_ohlc["close"])
    
    # Compute EMA on close prices
    closes = [c["close"] for c in intraday_5min_candles]
    ema_series = calculate_ema(closes, EMA_PERIOD)
    if not ema_series:
        return None
    
    current_ema = ema_series[-1]
    trend = determine_trend(ema_series)
    
    # Get the latest (signal) candle
    signal_candle = intraday_5min_candles[-1]
    o, h, l, c = signal_candle["open"], signal_candle["high"], signal_candle["low"], signal_candle["close"]
    
    # Classify the candle
    pattern = classify_candle(o, h, l, c)
    if pattern == "none":
        return None
    
    bullish = pattern in ("bull_maru", "bull_pin")
    bearish = pattern in ("bear_maru", "bear_pin")
    
    # ============ LOCATION CHECKS ============
    candidate_setups: List[Tuple[str, float]] = []  # (setup_name, level_price)
    
    # PDH / PDL
    if candle_touched(l, h, pdh):
        candidate_setups.append(("pdh", pdh))
    if candle_touched(l, h, pdl):
        candidate_setups.append(("pdl", pdl))
    
    # CPR — only if WIDE
    if cpr["is_wide"]:
        for cpr_name, cpr_level in (("cpr_tc", cpr["tc"]),
                                     ("cpr_pivot", cpr["pivot"]),
                                     ("cpr_bc", cpr["bc"])):
            if candle_touched(l, h, cpr_level):
                candidate_setups.append((cpr_name, cpr_level))
    
    # 20-EMA pullback on trending day
    if candle_touched(l, h, current_ema):
        if trend == "up" and bullish:
            candidate_setups.append(("ema20", current_ema))
        elif trend == "down" and bearish:
            candidate_setups.append(("ema20", current_ema))
    
    if not candidate_setups:
        return None
    
    # ============ DIRECTION ALIGNMENT ============
    long_friendly = {"pdl", "cpr_bc", "cpr_pivot", "ema20"}
    short_friendly = {"pdh", "cpr_tc", "cpr_pivot", "ema20"}
    
    # Find the first matching setup (priority: PDH/PDL > CPR > EMA)
    selected_setup = None
    side = None
    
    for setup_name, level in candidate_setups:
        if bullish and setup_name in long_friendly:
            selected_setup = (setup_name, level)
            side = "BUY"
            break
        elif bearish and setup_name in short_friendly:
            selected_setup = (setup_name, level)
            side = "SELL"
            break
    
    if not selected_setup:
        return None
    
    setup_name, level = selected_setup
    
    # ============ BUILD TRADE ============
    entry = c  # close of signal candle
    
    if side == "BUY":
        stop_loss = l * (1 - STOP_BUFFER_PCT / 100)  # below candle low with tick buffer
        risk = entry - stop_loss
        if risk <= 0:
            return None
        target = entry + TARGET_RR_MULTIPLE * risk
    else:  # SELL
        stop_loss = h * (1 + STOP_BUFFER_PCT / 100)  # above candle high
        risk = stop_loss - entry
        if risk <= 0:
            return None
        target = entry - TARGET_RR_MULTIPLE * risk
    
    risk_reward = abs(target - entry) / abs(entry - stop_loss)
    
    return ScalpingSignal(
        symbol=symbol,
        name=name,
        direction=side,
        setup_location=setup_name,
        candle_pattern=pattern,
        level_price=round(level, 2),
        candle_open=round(o, 2),
        candle_high=round(h, 2),
        candle_low=round(l, 2),
        candle_close=round(c, 2),
        cpr_pivot=round(cpr["pivot"], 2),
        cpr_tc=round(cpr["tc"], 2),
        cpr_bc=round(cpr["bc"], 2),
        cpr_width_pct=round(cpr["width_pct"] * 100, 2),
        pdh=round(pdh, 2),
        pdl=round(pdl, 2),
        suggested_entry=round(entry, 2),
        suggested_stop_loss=round(stop_loss, 2),
        suggested_target=round(target, 2),
        risk_reward=round(risk_reward, 2),
        trend=trend,
    )
