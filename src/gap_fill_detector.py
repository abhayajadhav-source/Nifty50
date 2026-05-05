from dataclasses import dataclass
from datetime import datetime
from typing import Optional
import pytz

IST = pytz.timezone("Asia/Kolkata")


@dataclass
class GapFillSignal:
    symbol: str
    name: str
    direction: str          # "BUY" or "SELL"
    gap_type: str           # "GAP_UP" or "GAP_DOWN"
    prev_close: float
    open_price: float
    current_price: float
    today_low: float
    today_high: float
    gap_pct: float
    gap_size: float         # absolute price gap
    atr: float
    atr_multiple: float     # gap_size / atr
    suggested_entry: float
    suggested_stop_loss: float
    suggested_target: float


# Tunable
MIN_ATR_MULTIPLE = 0.5      # gap must be at least 0.5x ATR
EARLIEST_TIME_IST = (9, 20)
LATEST_TIME_IST = (10, 50)  # 9:20 + 90 min hold window
STOP_LOSS_PCT = 0.30


def is_within_window():
    now = datetime.now(IST)
    minutes = now.hour * 60 + now.minute
    earliest = EARLIEST_TIME_IST[0] * 60 + EARLIEST_TIME_IST[1]
    latest = LATEST_TIME_IST[0] * 60 + LATEST_TIME_IST[1]
    return earliest <= minutes <= latest


def is_likely_results_day():
    """Coarse heuristic: most Nifty50 result announcements happen on Thursdays."""
    return datetime.now(IST).weekday() == 3


def analyze_gap_fill(symbol, name, prev_close, open_price, current_price,
                     today_low, today_high, atr) -> Optional[GapFillSignal]:
    """
    Detects gap-fill-and-reject pattern:
    - Stock gapped at open
    - Price retraced (filled) the gap (touched or crossed prev_close)
    - Price has now rejected and moved back in gap direction
    """
    if not is_within_window():
        return None
    
    if is_likely_results_day():
        return None
    
    if not atr or atr <= 0:
        return None
    
    gap_size = abs(open_price - prev_close)
    if gap_size < MIN_ATR_MULTIPLE * atr:
        return None
    
    gap_pct = ((open_price - prev_close) / prev_close) * 100
    is_gap_up = gap_pct > 0
    
    if is_gap_up:
        # Gap up: did price come down to fill (touch or cross prev_close)?
        gap_filled = today_low <= prev_close
        # Reject = price now back above prev_close moving up
        rejected = current_price > prev_close
        if not (gap_filled and rejected):
            return None
        direction = "BUY"
        gap_type = "GAP_UP"
        entry = current_price
        stop_loss = entry * (1 - STOP_LOSS_PCT / 100)
        target = open_price  # target: reclaim opening level
    else:
        # Gap down: did price rise to fill (touch or cross prev_close)?
        gap_filled = today_high >= prev_close
        rejected = current_price < prev_close
        if not (gap_filled and rejected):
            return None
        direction = "SELL"
        gap_type = "GAP_DOWN"
        entry = current_price
        stop_loss = entry * (1 + STOP_LOSS_PCT / 100)
        target = open_price
    
    return GapFillSignal(
        symbol=symbol, name=name, direction=direction, gap_type=gap_type,
        prev_close=round(prev_close, 2),
        open_price=round(open_price, 2),
        current_price=round(current_price, 2),
        today_low=round(today_low, 2),
        today_high=round(today_high, 2),
        gap_pct=round(gap_pct, 2),
        gap_size=round(gap_size, 2),
        atr=round(atr, 2),
        atr_multiple=round(gap_size / atr, 2),
        suggested_entry=round(entry, 2),
        suggested_stop_loss=round(stop_loss, 2),
        suggested_target=round(target, 2),
    )
