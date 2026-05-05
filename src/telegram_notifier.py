import requests


def send_alert(bot_token, chat_id, signal):
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
Current: ₹{signal.current_price}
52W Level: ₹{signal.week52_level}
{distance_text}

📈 Day's Change
Prev Close: ₹{signal.prev_close} | Day Change: {signal.day_change_pct}%

💡 {direction_hint}
Momentum signal. Use your own SL/target.

⚠️ Verify live price in Upstox before placing."""

    return _send(bot_token, chat_id, msg, signal.name)


def send_gap_fill_alert(bot_token, chat_id, signal):
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

⏱️ Hold: 30-90 min (mean reversion)

⚠️ Verify live price in Upstox before placing."""

    return _send(bot_token, chat_id, msg, signal.name)


def send_orb_alert(bot_token, chat_id, signal):
    emoji = "⬆️" if signal.direction == "BUY" else "⬇️"

    msg = f"""{emoji} {signal.name} — {signal.direction} setup (Opening Range Breakout)

📊 Opening Range (9:15-9:30)
OR High: ₹{signal.or_high} | OR Low: ₹{signal.or_low}
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

⚠️ Verify live price in Upstox before placing."""

    return _send(bot_token, chat_id, msg, signal.name)


def send_ma_trend_alert(bot_token, chat_id, signal):
    emoji = "📈" if signal.direction == "BUY" else "📉"

    msg = f"""{emoji} {signal.name} — {signal.direction} setup (MA Trend Following)

📊 Trend Confirmation (30-min EMAs)
EMA-9 (Fast): ₹{signal.ema_fast}
EMA-21 (Slow): ₹{signal.ema_slow}
Current: ₹{signal.current_price}
Distance from EMA-9: {signal.distance_from_fast_pct}%

✓ Price near fast EMA (pullback in sustained trend)

🎯 Trade Plan
Entry: ₹{signal.suggested_entry}
Stop Loss: ₹{signal.suggested_stop_loss} (-0.30%)
Target: ₹{signal.suggested_target} (2× risk)

⏱️ Hold: 2-5 hours

⚠️ Verify live price in Upstox before placing."""

    return _send(bot_token, chat_id, msg, signal.name)


def send_cprbo_alert(bot_token, chat_id, signal):
    emoji = "🎯"

    msg = f"""{emoji} {signal.name} — {signal.direction} setup (CPR Late Breakout)

📊 CPR Levels (yesterday)
Pivot: ₹{signal.pivot}
TC (Top): ₹{signal.tc}
BC (Bottom): ₹{signal.bc}
CPR Width: {signal.cpr_width_pct}% (narrow = trend potential)

📈 Today's Range
Morning High: ₹{signal.morning_high}
Morning Low: ₹{signal.morning_low}
Current: ₹{signal.current_price}
Broke {'above' if signal.direction == 'BUY' else 'below'}: ₹{signal.breakout_level}

🎯 Trade Plan
Entry: ₹{signal.suggested_entry}
Stop Loss: ₹{signal.suggested_stop_loss} (-0.30%)
Target: ₹{signal.suggested_target} (measured move)

⏱️ Hold: 1-3 hours

⚠️ Verify live price in Upstox before placing."""

    return _send(bot_token, chat_id, msg, signal.name)


def send_summary(bot_token, chat_id, summary_data):
    total = summary_data.get("total_scanned", 0)
    errors = summary_data.get("errors", 0)
    success = total - errors
    timestamp = summary_data.get("timestamp", "")

    alerts_today = summary_data.get("alerts_today", {})
    new_alerts = summary_data.get("new_alerts_this_run", {})

    strategy_names = {
        "gap": "Gap & Retracement",
        "breakout": "52W Breakout",
        "gapfill": "Gap Fill Rejection",
        "orb": "ORB",
        "ma_trend": "MA Trend",
        "cprbo": "CPRBO",
    }

    alert_lines = []
    total_alerts_today = 0
    for key, label in strategy_names.items():
        count = len(alerts_today.get(key, []))
        if count > 0:
            new_count = new_alerts.get(key, 0)
            new_marker = f" (+{new_count} new)" if new_count > 0 else ""
            alert_lines.append(f"  • {label}: {count}{new_marker}")
            total_alerts_today += count

    if not alert_lines:
        alert_lines.append("  • No alerts yet today")

    msg = f"""📋 Scan Summary — {timestamp}

🔍 This Run
Stocks scanned: {success}/{total}
Errors: {errors}

📊 Today's Alerts ({total_alerts_today} total)
{chr(10).join(alert_lines)}

⏱️ System running normally"""

    return _send(bot_token, chat_id, msg, "summary")


def _send(bot_token, chat_id, msg, stock_name):
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    r = requests.post(url, json={"chat_id": chat_id, "text": msg})

    if r.status_code == 200:
        if stock_name != "summary":
            print(f"    ✓ Telegram alert sent for {stock_name}")
        else:
            print(f"    ✓ Telegram summary sent")
        return True
    else:
        print(f"    ✗ Telegram FAILED for {stock_name}")
        print(f"       Status: {r.status_code}")
        print(f"       Response: {r.text[:200]}")
        return False
