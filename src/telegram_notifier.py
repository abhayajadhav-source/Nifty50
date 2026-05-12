import requests
from news_fetcher import format_news_for_telegram


def send_gap_fill_alert(bot_token, chat_id, signal, news_items=None):
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

⚠️ Verify live price in Upstox before placing.{format_news_for_telegram(news_items)}"""
    return _send(bot_token, chat_id, msg, signal.name)


def send_orb_alert(bot_token, chat_id, signal, news_items=None):
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

⚠️ Verify live price in Upstox before placing.{format_news_for_telegram(news_items)}"""
    return _send(bot_token, chat_id, msg, signal.name)


def send_ma_trend_alert(bot_token, chat_id, signal, news_items=None):
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

⚠️ Verify live price in Upstox before placing.{format_news_for_telegram(news_items)}"""
    return _send(bot_token, chat_id, msg, signal.name)


def send_cprbo_alert(bot_token, chat_id, signal, news_items=None):
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

⚠️ Verify live price in Upstox before placing.{format_news_for_telegram(news_items)}"""
    return _send(bot_token, chat_id, msg, signal.name)


def send_supply_zone_alert(bot_token, chat_id, signal, news_items=None):
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

⚠️ Verify live price in Upstox before placing.{format_news_for_telegram(news_items)}"""
    return _send(bot_token, chat_id, msg, signal.name)


def send_ppt_alert(bot_token, chat_id, signal, news_items=None):
    """Pivot Pressure Trade (Strategy 8)."""
    emoji = "💥" if signal.direction == "BUY" else "💢"
    breakout_word = "above" if signal.direction == "BUY" else "below"
    msg = f"""{emoji} {signal.name} — {signal.direction} setup (Pivot Pressure Trade)

📊 Pivot Levels (yesterday)
PP: ₹{signal.pp}
R2: ₹{signal.r2} | R1: ₹{signal.r1}
S1: ₹{signal.s1} | S2: ₹{signal.s2}

📈 Pressure & Breakout
Pressure built at: ₹{signal.pressure_level}
Touches before break: {signal.pressure_touches}
Current: ₹{signal.current_price}
Broke {breakout_word} pivot by: {signal.breakout_pct}%

🎯 Trade Plan
Entry: ₹{signal.suggested_entry}
Stop Loss: ₹{signal.suggested_stop_loss} (-0.30%)
Target: ₹{signal.suggested_target} (next pivot)

⏱️ Hold: 1-3 hours

⚠️ Verify live price in Upstox before placing.{format_news_for_telegram(news_items)}"""
    return _send(bot_token, chat_id, msg, signal.name)


def send_inside_candle_alert(bot_token, chat_id, signal, news_items=None):
    """Inside Candle Halt (Strategy 9 — Subasish Pani)."""
    emoji = "📦" if signal.direction == "BUY" else "📫"
    breakout_word = "above" if signal.direction == "BUY" else "below"
    msg = f"""{emoji} {signal.name} — {signal.direction} setup (Inside Candle Halt)

📊 Mother Candle (yesterday)
MC High: ₹{signal.mc_high}
MC Low: ₹{signal.mc_low}
MC Range: ₹{signal.mc_range} ({signal.mc_range_atr_multiple}× ATR)

📦 Today's Inside Action
Today High: ₹{signal.today_high_so_far}
Today Low: ₹{signal.today_low_so_far}
Pattern: Halt within MC range ✓

📈 Breakout
Current: ₹{signal.current_price}
Broke {breakout_word}: ₹{signal.breakout_level}
Breakout %: +{signal.breakout_pct}%

🎯 Trade Plan
Entry: ₹{signal.suggested_entry}
Stop Loss: ₹{signal.suggested_stop_loss}
Target: ₹{signal.suggested_target} (1.5× risk)

⏱️ Hold: Intraday (close by 3:15 PM)

⚠️ Verify live price in Upstox before placing.{format_news_for_telegram(news_items)}"""
    return _send(bot_token, chat_id, msg, signal.name)


def send_scalping_alert(bot_token, chat_id, signal, news_items=None):
    """Scalping Strategy (Strategy 10 — PDH/PDL/CPR/EMA + Candle Pattern)."""
    direction_emoji = "🎯" if signal.direction == "BUY" else "🔻"
    
    pattern_emoji = {
        "bull_maru": "🟢", "bear_maru": "🔴",
        "bull_pin": "🌟", "bear_pin": "⭐",
    }.get(signal.candle_pattern, "🕯")
    
    pattern_label = {
        "bull_maru": "Bullish Marubozu",
        "bear_maru": "Bearish Marubozu",
        "bull_pin": "Bullish Pin Bar",
        "bear_pin": "Bearish Pin Bar",
    }.get(signal.candle_pattern, signal.candle_pattern)
    
    setup_label = {
        "pdh": "Previous Day High",
        "pdl": "Previous Day Low",
        "cpr_tc": "CPR Top Central",
        "cpr_bc": "CPR Bottom Central",
        "cpr_pivot": "CPR Pivot",
        "ema20": "20 EMA Pullback",
    }.get(signal.setup_location, signal.setup_location)
    
    msg = f"""{direction_emoji} {signal.name} — {signal.direction} scalp (5-min)

📍 Setup Location: {setup_label}
Level: ₹{signal.level_price}
Trend: {signal.trend.upper()}

{pattern_emoji} Candle Pattern: {pattern_label}
Open: ₹{signal.candle_open} | Close: ₹{signal.candle_close}
High: ₹{signal.candle_high} | Low: ₹{signal.candle_low}

📊 Key Levels
PDH: ₹{signal.pdh} | PDL: ₹{signal.pdl}
CPR: TC ₹{signal.cpr_tc}, Pivot ₹{signal.cpr_pivot}, BC ₹{signal.cpr_bc}
CPR Width: {signal.cpr_width_pct}% ({'wide' if signal.cpr_width_pct >= 0.5 else 'narrow'})

🎯 Trade Plan
Entry: ₹{signal.suggested_entry}
Stop Loss: ₹{signal.suggested_stop_loss}
Target: ₹{signal.suggested_target}
R:R = 1:{signal.risk_reward}

⏱️ Hold: 15-30 min (scalp — book fast!)
Time stop: 30 min if not hit

⚠️ Verify live price in Upstox before placing.{format_news_for_telegram(news_items)}"""
    
    return _send(bot_token, chat_id, msg, signal.name)


def send_gap_alert(bot_token, chat_id, stock_name, gap_pct, prev_close, open_price, current_price, news_items=None):
    """Pre-market gap notification — purely informational."""
    direction = "GAP UP 🟢" if gap_pct > 0 else "GAP DOWN 🔴"
    msg = f"""⚡ {stock_name} — {direction} ({abs(gap_pct):.2f}%)

📈 Pre-market Move
Yesterday close: ₹{prev_close}
Today open: ₹{open_price}
Current: ₹{current_price}

This is informational only. No strategy triggered yet — watch for setup.{format_news_for_telegram(news_items)}"""
    return _send(bot_token, chat_id, msg, stock_name)


def send_summary(bot_token, chat_id, summary_data):
    """Detailed periodic summary at 9:30, 11:30, 13:30, 15:30 IST."""
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
        "ppt": "Pivot Pressure Trade",
        "inside_candle": "Inside Candle Halt",
        "scalping": "Scalping (5-min)",
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

    if total_alerts_today == 0:
        alerts_section = "✅ No setups triggered yet today.\nAll 8 strategies are scanning normally."
    else:
        alerts_section = f"📊 Today's Alerts ({total_alerts_today} total)\n" + "\n".join(alert_lines)

    msg = f"""📋 Scan Summary — {timestamp}

🔍 This Run
Stocks scanned: {success}/{total}
Errors: {errors}

{alerts_section}

⏱️ System running normally"""

    return _send(bot_token, chat_id, msg, "summary")


def send_heartbeat(bot_token, chat_id, heartbeat_data):
    """Lightweight 'still alive' message between summaries."""
    timestamp = heartbeat_data.get("timestamp", "")
    total = heartbeat_data.get("total_scanned", 0)
    total_alerts_today = heartbeat_data.get("total_alerts_today", 0)
    
    if total_alerts_today == 0:
        status = "No setups today yet — quiet market or strategies waiting for trigger."
    else:
        status = f"{total_alerts_today} alert(s) sent earlier today. No new alerts in last hour."
    
    msg = f"""💚 Heartbeat — {timestamp}

System scanning {total} stocks every 5 min.
{status}

Next periodic summary at next scheduled time (9:30/11:30/13:30/15:30 IST)."""
    
    return _send(bot_token, chat_id, msg, "heartbeat")


def _send(bot_token, chat_id, msg, stock_name):
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    r = requests.post(url, json={"chat_id": chat_id, "text": msg})
    if r.status_code == 200:
        if stock_name == "summary":
            print(f"    ✓ Telegram summary sent")
        elif stock_name == "heartbeat":
            print(f"    ✓ Telegram heartbeat sent")
        else:
            print(f"    ✓ Telegram alert sent for {stock_name}")
        return True
    else:
        print(f"    ✗ Telegram FAILED for {stock_name}")
        print(f"       Status: {r.status_code}")
        print(f"       Response: {r.text[:200]}")
        return False
