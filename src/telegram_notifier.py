def send_supply_zone_alert(bot_token, chat_id, signal):
    """Supply Zone Breakout alert (Strategy 7)."""
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

⚠️ Verify live price in Upstox before placing.
Place trade manually."""
    
    return _send(bot_token, chat_id, msg, signal.name)
