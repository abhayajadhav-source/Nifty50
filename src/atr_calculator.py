def calculate_atr(candles, period=14):
    """
    Calculate Average True Range from a list of daily candles.
    candles: list of dicts with 'high', 'low', 'close'
    period: ATR period (default 14)
    Returns ATR value or None if insufficient data.
    """
    if not candles or len(candles) < period + 1:
        return None
    
    true_ranges = []
    for i in range(1, len(candles)):
        curr = candles[i]
        prev_close = candles[i - 1]["close"]
        
        tr = max(
            curr["high"] - curr["low"],
            abs(curr["high"] - prev_close),
            abs(curr["low"] - prev_close),
        )
        true_ranges.append(tr)
    
    if len(true_ranges) < period:
        return None
    
    # Simple average of last `period` true ranges
    atr = sum(true_ranges[-period:]) / period
    return round(atr, 2)
