from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List, Dict
import pytz

IST = pytz.timezone("Asia/Kolkata")


@dataclass
class SupplyZoneSignal:
    symbol: str
    name: str
    direction: str
    zone_level: float
    zone_age_days: int
    cluster_size: int
    current_price: float
    breakout_pct: float
    suggested_entry: float
    suggested_stop_loss: float
    suggested_target: float


# Tunable parameters
EARLIEST_TIME_IST = (10, 0)
SWING_LOOKBACK = 2          # bars on each side to qualify a swing high
ZONE_CLUSTER_PCT = 0.5      # highs within this % count as same zone
MIN_CLUSTER_SIZE = 2        # at least 2 touches form a zone
BREAKOUT_THRESHOLD_PCT = 0.3  # price must clear zone by this %
MIN_ZONE_AGE_DAYS = 5       # zone must be at least N days old
MAX_ZONE_AGE_DAYS = 20      # don't consider zones older than 20 days
NOT_BROKEN_THRESHOLD_PCT = 1.0  # zone is "fresh" if price hasn't been >1% above
STOP_LOSS_PCT = 0.30
TARGET_RISK_MULTIPLE = 2.0


def is_within_window():
    now = datetime.now(IST)
    minutes = now.hour * 60 + now.minute
    earliest = EARLIEST_TIME_IST[0] * 60 + EARLIEST_TIME_IST[1]
    market_close = 15 * 60 + 30
    return earliest <= minutes <= market_close


def find_swing_highs(candles: List[Dict]) -> List[tuple]:
    """
    Returns list of (index, high_price) where high is a local swing high.
    A swing high = candle whose high > N candles before AND N candles after.
    """
    swings = []
    n = len(candles)
    for i in range(SWING_LOOKBACK, n - SWING_LOOKBACK):
        ch = candles[i]["high"]
        is_swing = True
        for k in range(1, SWING_LOOKBACK + 1):
            if candles[i - k]["high"] >= ch or candles[i + k]["high"] >= ch:
                is_swing = False
                break
        if is_swing:
            swings.append((i, ch))
    return swings


def cluster_swings_into_zones(swings: List[tuple]) -> List[Dict]:
    """
    Group swing highs that are within ZONE_CLUSTER_PCT of each other.
    Returns list of zones: [{"level": avg, "indices": [...], "size": N}]
    """
    if not swings:
        return []
    
    # Sort by price descending so we cluster from top down
    sorted_swings = sorted(swings, key=lambda x: x[1], reverse=True)
    
    zones = []
    used = set()
    
    for i, (idx, price) in enumerate(sorted_swings):
        if i in used:
            continue
        cluster_indices = [idx]
        cluster_prices = [price]
        used.add(i)
        
        for j in range(i + 1, len(sorted_swings)):
            if j in used:
                continue
            other_idx, other_price = sorted_swings[j]
            if abs(other_price - price) / price * 100 <= ZONE_CLUSTER_PCT:
                cluster_indices.append(other_idx)
                cluster_prices.append(other_price)
                used.add(j)
        
        if len(cluster_indices) >= MIN_CLUSTER_SIZE:
            avg_level = sum(cluster_prices) / len(cluster_prices)
            most_recent_idx = max(cluster_indices)
            zones.append({
                "level": avg_level,
                "indices": cluster_indices,
                "size": len(cluster_indices),
                "most_recent_idx": most_recent_idx,
            })
    
    return zones


def is_zone_fresh(zone: Dict, candles: List[Dict]) -> bool:
    """A zone is fresh if no candle after the most recent swing closed >1% above zone level."""
    most_recent_idx = zone["most_recent_idx"]
    level = zone["level"]
    
    for i in range(most_recent_idx + 1, len(candles)):
        c = candles[i]
        if c["close"] > level * (1 + NOT_BROKEN_THRESHOLD_PCT / 100):
            return False
    return True


def analyze_supply_zone(symbol, name, current_price, candles) -> Optional[SupplyZoneSignal]:
    """
    Detects breakout above a recent supply zone.
    candles: list of dicts with 'high', 'low', 'close' (oldest first, last 20 days)
    """
    if not is_within_window():
        return None
    
    if not candles or len(candles) < SWING_LOOKBACK * 2 + MIN_CLUSTER_SIZE:
        return None
    
    # Use last MAX_ZONE_AGE_DAYS candles
    candles = candles[-MAX_ZONE_AGE_DAYS:]
    n = len(candles)
    
    # Find swing highs
    swings = find_swing_highs(candles)
    if len(swings) < MIN_CLUSTER_SIZE:
        return None
    
    # Cluster into zones
    zones = cluster_swings_into_zones(swings)
    if not zones:
        return None
    
    # Filter to fresh zones, recent enough
    valid_zones = []
    for z in zones:
        zone_age = n - 1 - z["most_recent_idx"]  # bars since the most recent swing
        if zone_age < MIN_ZONE_AGE_DAYS:
            continue  # too recent — not really tested
        if zone_age > MAX_ZONE_AGE_DAYS:
            continue
        if not is_zone_fresh(z, candles):
            continue
        valid_zones.append((z, zone_age))
    
    if not valid_zones:
        return None
    
    # Pick the closest valid zone below current price (the one being broken)
    candidate = None
    for z, age in valid_zones:
        if current_price > z["level"]:
            distance_pct = ((current_price - z["level"]) / z["level"]) * 100
            if distance_pct >= BREAKOUT_THRESHOLD_PCT:
                # Actual breakout
                if candidate is None or z["level"] > candidate[0]["level"]:
                    candidate = (z, age, distance_pct)
    
    if not candidate:
        return None
    
    zone, age, breakout_pct = candidate
    
    direction = "BUY"
    entry = current_price
    stop_loss = entry * (1 - STOP_LOSS_PCT / 100)
    target = entry + (entry - stop_loss) * TARGET_RISK_MULTIPLE
    
    return SupplyZoneSignal(
        symbol=symbol,
        name=name,
        direction=direction,
        zone_level=round(zone["level"], 2),
        zone_age_days=age,
        cluster_size=zone["size"],
        current_price=round(current_price, 2),
        breakout_pct=round(breakout_pct, 2),
        suggested_entry=round(entry, 2),
        suggested_stop_loss=round(stop_loss, 2),
        suggested_target=round(target, 2),
    )
