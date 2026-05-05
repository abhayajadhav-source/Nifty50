import requests


def send_alert(bot_token, chat_id, signal):
    """Gap-retracement alert."""
    emoji = "🟢" if signal.gap_type.value == "GAP_UP" else "🔴"
    direction = "BUY" if signal.gap_type.value == "GAP_UP" else "SELL"
    
    msg = f"""{emoji} {signal.name} — {direction} setup (Gap & Retracement)

📊 Setup
Gap: {signal.gap_pct}% ({signal.gap_type.value})
Prev Close: ₹{signal.prev_close} | Open: ₹{signal.open_price}
Current: ₹{signal.current_price} | Retraced: {signal.retracement_pct}%

🎯 Trade Plan
Entry: ₹{signal.suggested_entry}
Stop Loss: ₹{signal.suggested_stop_loss} (-0.30%)
Target: ₹{signal.suggested_target}

⚠️ Verify live price in Upstox before placing.
Place trade manually."""
    
    return _send(bot_token, chat_id, msg, signal.name)


def send_breakout_alert(bot_token, chat_id, signal):
    """52-week high/low breakout alert."""
    is_high = signal.breakout_type.value == "52W_HIGH_BREAKOUT"
    emoji = "🚀" if is_high else "🔻"
    label = "52-Week HIGH BREAKOUT" if is_high else "52-Week LOW BREAKDOWN"
    direction_hint = "Bullish momentum" if is_high else "Bearish momentum"
    
    if is_high:
        distance_text = f"+{signal.distance_pct}% above 52W high" if signal.distance_pct >= 0 else "At 52W high"
    else:
        distance_text = f"{signal.distance_pct}% below 52W low" if signal.distance_pct <= 0 else "At 52W low"
    
    msg = f"""{emoji} {signal.name} — {label}

📊 Breakout Info
Current Price: ₹{signal.current_price}
52W Level: ₹{signal.week52_level}
{distance_text}

📈 Day's Change
Prev Close: ₹{signal.prev_close}
Day Change: {signal.day_change_pct}%

💡 {direction_hint}
This is a momentum signal, not a complete trade plan.

⚠️ Verify live price in Upstox before placing.
Place trade manually."""
    
    return _send(bot_token, chat_id, msg, signal.name)


def send_gap_fill_alert(bot_token, chat_id, signal):
    """Gap Fill Rejection alert (Strategy 3)."""
    emoji = "🔵" if signal.direction == "BUY" else "🟣"
    
    msg = f"""{emoji} {signal.name} — {signal.direction} setup (Gap Fill Rejection)

📊 Setup
Gap: {signal.gap_pct}% ({signal.gap_type})
Gap Size: ₹{signal.gap_size} ({signal.atr_multiple}× ATR)
ATR (14d): ₹{signal.atr}

📈 Today's Action
Prev Close: ₹{signal.prev_close} | Open: ₹{signal.open_price}
Today: Low ₹{signal.today_low} | High ₹{signal.today_high}
Current: ₹{signal.current_price}
Gap was filled and rejected ✓

🎯 Trade Plan
Entry: ₹{signal.suggested_entry}
Stop Loss: ₹{signal.suggested_stop_loss} (-0.30%)
Target: ₹{signal.suggested_target}

⏱️ Hold: 30-90 min (mean reversion play)

⚠️ Verify live price in Upstox before placing.
Place trade manually."""
    
    return _send(bot_token, chat_id, msg, signal.name)


def send_orb_alert(bot_token, chat_id, signal):
    """Opening Range Breakout alert (Strategy 4)."""
    emoji = "⬆️" if signal.direction == "BUY" else "⬇️"
    
    msg = f"""{emoji} {signal.name} — {signal.direction} setup (Opening Range Breakout)

📊 Opening Range (9:15-9:30)
OR High: ₹{signal.or_high}
OR Low: ₹{signal.or_low}
OR Width: ₹{signal.or_width} ({signal.or_width_atr_multiple}× ATR)
ATR (14d): ₹{signal.atr}

📈 Breakout
Current: ₹{signal.current_price}
Broke {'above' if signal.direction == 'BUY' else 'below'}: ₹{signal.breakout_level}

🎯 Trade Plan
Entry: ₹{signal.suggested_entry}
Stop Loss: ₹{signal.suggested_stop_loss} (-0.30%)
Target: ₹{signal.suggested_target} (measured move)

⏱️ Hold: 1-4 hours

⚠️ Verify live price in Upstox before placing.
Place trade manually."""
    
    return _send(bot_token, chat_id, msg, signal.name)


def _send(bot_token, chat_id, msg, stock_name):
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    r = requests.post(url, json={"chat_id": chat_id, "text": msg})
    
    if r.status_code == 200:
        print(f"    ✓ Telegram alert sent for {stock_name}")
        return True
    else:
        print(f"    ✗ Telegram FAILED for {stock_name}")
        print(f"       Status: {r.status_code}")
        print(f"       Response: {r.text[:200]}")
        return False
