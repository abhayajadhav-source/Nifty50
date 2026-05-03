from dataclasses import dataclass
from enum import Enum
from typing import Optional

class GapType(Enum):
    GAP_UP = "GAP_UP"
    GAP_DOWN = "GAP_DOWN"

@dataclass
class GapSignal:
    symbol: str
    name: str
    gap_type: GapType
    prev_close: float
    open_price: float
    current_price: float
    gap_pct: float
    retracement_pct: float
    in_entry_zone: bool
    holding_above_floor: bool
    suggested_entry: float
    suggested_stop_loss: float
    suggested_target: float

def analyze_gap(symbol, name, prev_close, open_price,
                current_price, low_since_open, high_since_open) -> Optional[GapSignal]:
    gap_pct = ((open_price - prev_close) / prev_close) * 100
    if abs(gap_pct) < 1.0:
        return None
    
    gap_type = GapType.GAP_UP if gap_pct > 0 else GapType.GAP_DOWN
    
    if gap_type == GapType.GAP_UP:
        retracement_pct = ((open_price - current_price) / open_price) * 100
        max_retrace = ((open_price - low_since_open) / open_price) * 100
        in_entry_zone = 0.60 <= retracement_pct <= 0.75
        holding_above_floor = max_retrace <= 0.75
        entry = current_price
        stop_loss = entry * (1 - 0.0030)
        target = open_price
    else:
        retracement_pct = ((high_since_open - open_price) / open_price) * 100
        in_entry_zone = 0.60 <= retracement_pct <= 0.75
        holding_above_floor = retracement_pct <= 0.75
        entry = current_price
        stop_loss = entry * (1 + 0.0030)
        target = open_price
    
    return GapSignal(
        symbol=symbol, name=name, gap_type=gap_type,
        prev_close=prev_close, open_price=open_price,
        current_price=current_price,
        gap_pct=round(gap_pct, 2),
        retracement_pct=round(retracement_pct, 2),
        in_entry_zone=in_entry_zone,
        holding_above_floor=holding_above_floor,
        suggested_entry=round(entry, 2),
        suggested_stop_loss=round(stop_loss, 2),
        suggested_target=round(target, 2),
    )
