from datetime import datetime
import pytz

IST = pytz.timezone("Asia/Kolkata")


def _rating_class(label):
    if label in ("Strong Buy", "Buy"):
        return "rating-buy"
    if label in ("Sell", "Strong Sell"):
        return "rating-sell"
    if label == "Hold":
        return "rating-hold"
    return "rating-na"


def _change_class(value):
    if value is None:
        return "neutral"
    if value > 0:
        return "positive"
    if value < 0:
        return "negative"
    return "neutral"


def generate_report(scan_data, output_path):
    timestamp = datetime.now(IST).strftime("%Y-%m-%d %H:%M IST")
    symbols = scan_data.get("symbols", [])
    quotes = scan_data.get("quotes", {})
    ratings = scan_data.get("ratings", {})
    atrs = scan_data.get("atrs", {})
    alerts_today = scan_data.get("alerts_today", {})
    errors = scan_data.get("errors", {})

    total = len(symbols)
    success = total - len(errors)

    strategy_meta = {
        "gap": ("Gap & Retracement", "🟢"),
        "breakout": ("52W Breakout", "🚀"),
        "gapfill": ("Gap Fill Rejection", "🔵"),
        "orb": ("ORB", "⬆️"),
        "ma_trend": ("MA Trend", "📈"),
        "cprbo": ("CPRBO", "🎯"),
        "supply_zone": ("Supply Zone Breakout", "🔥"),
    }

    total_alerts = sum(len(alerts_today.get(k, [])) for k in strategy_meta)

    alert_cards_html = ""
    for key, (label, emoji) in strategy_meta.items():
        stocks = alerts_today.get(key, [])
        count = len(stocks)
        stocks_str = ", ".join(stocks) if stocks else "—"
        active_class = "alert-card-active" if count > 0 else ""
        alert_cards_html += f"""
        <div class="alert-card {active_class}">
            <div class="alert-card-emoji">{emoji}</div>
            <div class="alert-card-count">{count}</div>
            <div class="alert-card-label">{label}</div>
            <div class="alert-card-stocks">{stocks_str}</div>
        </div>
        """

    stock_rows = []
    for sym in symbols:
        name = sym["name"]
        q = quotes.get(name, {})
        rating = ratings.get(name, {})
        atr = atrs.get(name)

        if not q:
            err = errors.get(name, "no data")
            stock_rows.append(f"""
            <tr class="error-row">
                <td>{name}</td>
                <td colspan="10">⚠️ {err}</td>
            </tr>
            """)
            continue

        ltp = q.get("ltp", 0)
        prev_close = q.get("prev_close", 0)
        open_p = q.get("open", 0)
        day_change_pct = ((ltp - prev_close) / prev_close * 100) if prev_close else 0
        gap_pct = ((open_p - prev_close) / prev_close * 100) if prev_close else 0

        atr_str = f"₹{atr}" if atr else "—"
        rating_label = rating.get("label", "N/A")
        rating_cls = _rating_class(rating_label)
        num_analysts = rating.get("num_analysts") or "—"
        target_mean = rating.get("target_mean")
        target_str = f"₹{target_mean:,}" if target_mean else "—"
        upside = rating.get("upside_pct")
        upside_str = f"{upside:+.1f}%" if upside is not None else "—"
        upside_cls = _change_class(upside)
        w52_high = q.get("week52_high", 0)
        w52_low = q.get("week52_low", 0)

        day_cls = _change_class(day_change_pct)
        gap_cls = _change_class(gap_pct)

        alert_badges = ""
        for key, (label, emoji) in strategy_meta.items():
            if name in alerts_today.get(key, []):
                alert_badges
