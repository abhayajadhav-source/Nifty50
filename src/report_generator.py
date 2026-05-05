from datetime import datetime
import pytz

IST = pytz.timezone("Asia/Kolkata")


def generate_report(scan_data, output_path):
    """
    Generate a comprehensive markdown report of scan results.
    scan_data: dict with all scan results, alerts, ratings, etc.
    output_path: file path to write the report
    """
    timestamp = datetime.now(IST).strftime("%Y-%m-%d %H:%M IST")
    symbols = scan_data.get("symbols", [])
    quotes = scan_data.get("quotes", {})
    ratings = scan_data.get("ratings", {})
    atrs = scan_data.get("atrs", {})
    alerts_today = scan_data.get("alerts_today", {})
    errors = scan_data.get("errors", {})
    
    lines = []
    lines.append(f"# Nifty50 Scan Report")
    lines.append(f"Generated: {timestamp}")
    lines.append("")
    
    # Section 1: Summary
    lines.append("## 📊 Summary")
    lines.append("")
    total = len(symbols)
    success = total - len(errors)
    lines.append(f"- **Stocks scanned**: {success}/{total}")
    lines.append(f"- **Errors**: {len(errors)}")
    lines.append("")
    
    strategy_names = {
        "gap": "Gap & Retracement",
        "breakout": "52W Breakout",
        "gapfill": "Gap Fill Rejection",
        "orb": "ORB",
        "ma_trend": "MA Trend Following",
        "cprbo": "CPRBO",
    }
    
    total_alerts = sum(len(alerts_today.get(k, [])) for k in strategy_names)
    lines.append(f"### Today's Alerts ({total_alerts} total)")
    lines.append("")
    for key, label in strategy_names.items():
        alerted_stocks = alerts_today.get(key, [])
        if alerted_stocks:
            lines.append(f"- **{label}**: {len(alerted_stocks)} → {', '.join(alerted_stocks)}")
        else:
            lines.append(f"- **{label}**: 0")
    lines.append("")
    
    # Section 2: All stock details with analyst ratings
    lines.append("## 🏢 Stock-by-Stock Details")
    lines.append("")
    lines.append("| Stock | LTP (₹) | Day Change | Gap % | ATR | Analyst Rating | # Analysts | Target Mean (₹) | Upside | 52W High | 52W Low |")
    lines.append("|-------|---------|------------|-------|-----|----------------|-----------|-----------------|--------|----------|---------|")
    
    for sym in symbols:
        name = sym["name"]
        q = quotes.get(name, {})
        rating = ratings.get(name, {})
        atr = atrs.get(name)
        
        if not q:
            err = errors.get(name, "no data")
            lines.append(f"| {name} | ERROR | — | — | — | — | — | — | — | — | — |")
            continue
        
        ltp = q.get("ltp", 0)
        prev_close = q.get("prev_close", 0)
        open_p = q.get("open", 0)
        day_change_pct = ((ltp - prev_close) / prev_close * 100) if prev_close else 0
        gap_pct = ((open_p - prev_close) / prev_close * 100) if prev_close else 0
        
        atr_str = f"₹{atr}" if atr else "n/a"
        rating_label = rating.get("label", "N/A")
        num_analysts = rating.get("num_analysts") or "—"
        target_mean = rating.get("target_mean")
        target_str = f"₹{target_mean}" if target_mean else "—"
        upside = rating.get("upside_pct")
        upside_str = f"{upside:+.1f}%" if upside is not None else "—"
        w52_high = q.get("week52_high", 0)
        w52_low = q.get("week52_low", 0)
        
        lines.append(
            f"| {name} | ₹{ltp} | {day_change_pct:+.2f}% | {gap_pct:+.2f}% | {atr_str} "
            f"| {rating_label} | {num_analysts} | {target_str} | {upside_str} "
            f"| ₹{w52_high} | ₹{w52_low} |"
        )
    
    lines.append("")
    
    # Section 3: Alerted stocks deep-dive
    if total_alerts > 0:
        lines.append("## 🎯 Alerted Stocks Deep Dive")
        lines.append("")
        for key, label in strategy_names.items():
            alerted_stocks = alerts_today.get(key, [])
            if not alerted_stocks:
                continue
            lines.append(f"### {label}")
            lines.append("")
            for stock_name in alerted_stocks:
                q = quotes.get(stock_name, {})
                rating = ratings.get(stock_name, {})
                ltp = q.get("ltp", 0)
                lines.append(f"#### {stock_name}")
                lines.append(f"- LTP: ₹{ltp}")
                if rating.get("label") and rating.get("label") != "N/A":
                    lines.append(f"- Analyst View: **{rating['label']}** ({rating.get('num_analysts', '?')} analysts)")
                    if rating.get("target_mean"):
                        upside = rating.get("upside_pct")
                        upside_str = f", upside {upside:+.1f}%" if upside is not None else ""
                        lines.append(f"- Mean Target: ₹{rating['target_mean']}{upside_str}")
                lines.append("")
    
    # Section 4: Errors
    if errors:
        lines.append("## ⚠️ Errors")
        lines.append("")
        for stock_name, err_msg in errors.items():
            lines.append(f"- **{stock_name}**: {err_msg}")
        lines.append("")
    
    # Section 5: Ratings spotlight
    lines.append("## 💡 Top Analyst Picks")
    lines.append("")
    
    # Stocks with highest analyst upside
    stocks_with_upside = [
        (name, ratings[name]) for name in ratings
        if ratings[name].get("upside_pct") is not None and ratings[name].get("label") in ("Strong Buy", "Buy")
    ]
    stocks_with_upside.sort(key=lambda x: x[1].get("upside_pct", 0), reverse=True)
    
    if stocks_with_upside:
        lines.append("### Highest Upside (Buy/Strong Buy rated)")
        lines.append("")
        lines.append("| Stock | Rating | Current | Target | Upside |")
        lines.append("|-------|--------|---------|--------|--------|")
        for name, r in stocks_with_upside[:10]:
            lines.append(
                f"| {name} | {r['label']} | ₹{r.get('current_price', '?')} "
                f"| ₹{r.get('target_mean', '?')} | {r.get('upside_pct'):+.1f}% |"
            )
        lines.append("")
    
    # Stocks rated Sell/Strong Sell
    sell_rated = [
        (name, ratings[name]) for name in ratings
        if ratings[name].get("label") in ("Sell", "Strong Sell")
    ]
    if sell_rated:
        lines.append("### Sell-Rated Stocks")
        lines.append("")
        lines.append("| Stock | Rating | Current | Target | Upside |")
        lines.append("|-------|--------|---------|--------|--------|")
        for name, r in sell_rated:
            upside = r.get("upside_pct")
            upside_str = f"{upside:+.1f}%" if upside is not None else "—"
            lines.append(
                f"| {name} | {r['label']} | ₹{r.get('current_price', '?')} "
                f"| ₹{r.get('target_mean', '?')} | {upside_str} |"
            )
        lines.append("")
    
    # Footer
    lines.append("---")
    lines.append("")
    lines.append("*Generated by Nifty50 Gap Monitor. Analyst ratings from Yahoo Finance.*")
    lines.append("*Not investment advice. Verify all data independently before trading.*")
    
    with open(output_path, "w") as f:
        f.write("\n".join(lines))
    
    return output_path
