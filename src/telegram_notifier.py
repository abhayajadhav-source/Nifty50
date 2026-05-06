import requests


def send_gap_fill_alert(bot_token, chat_id, signal):
    """Gap Fill Rejection (Strategy 3)."""
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
    """ORB (Strategy 4)."""
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
    """MA Trend (Strategy 5)."""
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
    """CPRBO (Strategy 6)."""
    emoji = "🎯"
    msg = f"""{emoji} {signal.name} — {signal.direction} setup (CPR Late Breakout)

📊 CPR Levels (yesterday)
Pivot: ₹{signal.pivot}
TC (Top): ₹{signal.tc}
BC (Bottom): ₹{signal.bc}
CPR Width: {signal.cpr_width_pct}% (narrow = trend potential)

📈 Today's Range
Morning High: ₹{signal.morning_high} | Morning Low: ₹{signal.morning_low}
Current: ₹{signal.current_price}
Broke {'above' if signal.direction == 'BUY' else 'below'}: ₹{signal.breakout_level}

🎯 Trade Plan
Entry: ₹{signal.suggested_entry}
Stop Loss: ₹{signal.suggested_stop_loss} (-0.30%)
Target: ₹{signal.suggested_target} (measured move)

⏱️ Hold: 1-3 hours

⚠️ Verify live price in Upstox before placing."""
    return _send(bot_token, chat_id, msg, signal.name)


def send_supply_zone_alert(bot_token, chat_id, signal):
    """Supply Zone Breakout (Strategy 7)."""
    emoji = "🔥"
    msg = f"""{emoji} {signal.name} — {signal.direction} setup (Supply Zone Breakout)

📊 Zone Details
Zone Level: ₹{signal.zone_level}
Zone Age: {signal.zone_age_days} days old
Cluster Size: {signal.cluster_size} touches (more = stronger zone)

📈 Breakout
Current: ₹{signal.current_price}
Breakout %: +{signal.breakout_pct}% above zone

🎯 Trade Plan
Entry: ₹{signal.suggested_entry}
Stop Loss: ₹{signal.suggested_stop_loss} (-0.30%)
Target: ₹{signal.suggested_target} (2× risk)

⏱️ Hold: 1-3 days (positional)

⚠️ Verify live price in Upstox before placing."""
    return _send(bot_token, chat_id, msg, signal.name)


def send_summary(bot_token, chat_id, summary_data):
    """Periodic Telegram summary at key times."""
    total = summary_data.get("total_scanned", 0)
    errors = summary_data.get("errors", 0)
    success = total - errors
    timestamp = summary_data.get("timestamp", "")

    alerts_today = summary_data.get("alerts_today", {})
    new_alerts = summary_data.get("new_alerts_this_run", {})

    strategy_names = {
        "gapfill": "Gap Fill Rejection",
        "orb": "ORB",
        "ma_trend": "MA Trend",
        "cprbo": "CPRBO",
        "supply_zone": "Supply Zone Breakout",
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
