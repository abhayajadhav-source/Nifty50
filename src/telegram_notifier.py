import requests


def send_alert(bot_token, chat_id, signal):
    emoji = "🟢" if signal.gap_type.value == "GAP_UP" else "🔴"
    direction = "BUY" if signal.gap_type.value == "GAP_UP" else "SELL"
    
    msg = f"""{emoji} {signal.name} — {direction} setup

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
    
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    r = requests.post(url, json={"chat_id": chat_id, "text": msg})
    
    if r.status_code == 200:
        print(f"    ✓ Telegram alert sent for {signal.name}")
        return True
    else:
        print(f"    ✗ Telegram FAILED for {signal.name}")
        print(f"       Status: {r.status_code}")
        print(f"       Response: {r.text[:200]}")
        return False
