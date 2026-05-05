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
    
    # distance_pct is negative when below high, positive when above
    if is_high:
        if signal.distance_pct >= 0:
            distance_text = f"+{signal.distance_pct}% above 52W high"
        else:
            distance_text = f"At 52W high"
    else:
        if signal.distance_pct <= 0:
            distance_text = f"{signal.distance_pct}% below 52W low"
        else:
            distance_text = f"At 52W low"
    
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
Use your own analysis for entry/SL/target.

⚠️ Verify live price in Upstox before placing.
Place trade manually."""
    
    return _send(bot_token, chat_id, msg, signal.name)


def _send(bot_token, chat_id, msg, stock_name):
    """Internal function to send Telegram message."""
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
