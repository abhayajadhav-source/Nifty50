from datetime import datetime
import pytz

IST = pytz.timezone("Asia/Kolkata")


def _rating_class(label):
    """CSS class based on analyst rating."""
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
    """Generate a polished HTML report."""
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
    }
    
    total_alerts = sum(len(alerts_today.get(k, [])) for k in strategy_meta)
    
    # Build per-strategy alert summary cards
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
    
    # Build main stock table
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
        
        # Check if this stock alerted on any strategy
        alert_badges = ""
        for key, (label, emoji) in strategy_meta.items():
            if name in alerts_today.get(key, []):
                alert_badges += f'<span class="alert-badge" title="{label}">{emoji}</span>'
        
        stock_rows.append(f"""
        <tr>
            <td class="stock-name">{name} {alert_badges}</td>
            <td class="num">₹{ltp:,}</td>
            <td class="num {day_cls}">{day_change_pct:+.2f}%</td>
            <td class="num {gap_cls}">{gap_pct:+.2f}%</td>
            <td class="num">{atr_str}</td>
            <td><span class="rating-pill {rating_cls}">{rating_label}</span></td>
            <td class="num">{num_analysts}</td>
            <td class="num">{target_str}</td>
            <td class="num {upside_cls}">{upside_str}</td>
            <td class="num">₹{w52_high:,}</td>
            <td class="num">₹{w52_low:,}</td>
        </tr>
        """)
    
    # Top picks section
    stocks_with_upside = [
        (name, ratings[name]) for name in ratings
        if ratings[name].get("upside_pct") is not None and ratings[name].get("label") in ("Strong Buy", "Buy")
    ]
    stocks_with_upside.sort(key=lambda x: x[1].get("upside_pct", 0), reverse=True)
    
    top_picks_rows = ""
    for name, r in stocks_with_upside[:10]:
        upside = r.get("upside_pct", 0)
        cls = _change_class(upside)
        top_picks_rows += f"""
        <tr>
            <td class="stock-name">{name}</td>
            <td><span class="rating-pill {_rating_class(r['label'])}">{r['label']}</span></td>
            <td class="num">₹{r.get('current_price', '—'):,}</td>
            <td class="num">₹{r.get('target_mean', '—'):,}</td>
            <td class="num {cls}">{upside:+.1f}%</td>
        </tr>
        """
    
    sell_rated = [
        (name, ratings[name]) for name in ratings
        if ratings[name].get("label") in ("Sell", "Strong Sell")
    ]
    sell_rows = ""
    for name, r in sell_rated:
        upside = r.get("upside_pct")
        upside_str = f"{upside:+.1f}%" if upside is not None else "—"
        cls = _change_class(upside) if upside is not None else "neutral"
        sell_rows += f"""
        <tr>
            <td class="stock-name">{name}</td>
            <td><span class="rating-pill {_rating_class(r['label'])}">{r['label']}</span></td>
            <td class="num">₹{r.get('current_price', '—'):,}</td>
            <td class="num">₹{r.get('target_mean', '—'):,}</td>
            <td class="num {cls}">{upside_str}</td>
        </tr>
        """
    
    error_section = ""
    if errors:
        error_rows = "\n".join(
            f'<tr><td class="stock-name">{n}</td><td class="error-msg">{e}</td></tr>'
            for n, e in errors.items()
        )
        error_section = f"""
        <section class="card">
            <h2>⚠️ Errors ({len(errors)})</h2>
            <table class="data-table">
                <thead>
                    <tr><th>Stock</th><th>Error</th></tr>
                </thead>
                <tbody>{error_rows}</tbody>
            </table>
        </section>
        """
    
    sell_section = ""
    if sell_rows:
        sell_section = f"""
        <section class="card">
            <h2>📉 Sell-Rated Stocks</h2>
            <table class="data-table">
                <thead>
                    <tr><th>Stock</th><th>Rating</th><th>Current</th><th>Target</th><th>Upside</th></tr>
                </thead>
                <tbody>{sell_rows}</tbody>
            </table>
        </section>
        """
    
    top_picks_section = ""
    if top_picks_rows:
        top_picks_section = f"""
        <section class="card">
            <h2>💡 Top Analyst Picks (Buy/Strong Buy by Upside)</h2>
            <table class="data-table">
                <thead>
                    <tr><th>Stock</th><th>Rating</th><th>Current</th><th>Target</th><th>Upside</th></tr>
                </thead>
                <tbody>{top_picks_rows}</tbody>
            </table>
        </section>
        """
    
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Nifty50 Scan Report — {timestamp}</title>
<style>
:root {{
    --bg: #f5f7fa;
    --card-bg: #ffffff;
    --text: #1a202c;
    --text-muted: #718096;
    --border: #e2e8f0;
    --primary: #2563eb;
    --positive: #059669;
    --negative: #dc2626;
    --neutral: #64748b;
    --buy: #059669;
    --buy-bg: #d1fae5;
    --sell: #dc2626;
    --sell-bg: #fee2e2;
    --hold: #d97706;
    --hold-bg: #fef3c7;
    --na: #94a3b8;
    --na-bg: #f1f5f9;
    --shadow: 0 1px 3px rgba(0,0,0,0.05), 0 1px 2px rgba(0,0,0,0.03);
    --shadow-md: 0 4px 6px rgba(0,0,0,0.07), 0 2px 4px rgba(0,0,0,0.04);
}}

@media (prefers-color-scheme: dark) {{
    :root {{
        --bg: #0f172a;
        --card-bg: #1e293b;
        --text: #f1f5f9;
        --text-muted: #94a3b8;
        --border: #334155;
        --buy-bg: #064e3b;
        --sell-bg: #7f1d1d;
        --hold-bg: #78350f;
        --na-bg: #334155;
    }}
}}

* {{ box-sizing: border-box; }}

body {{
    margin: 0;
    background: var(--bg);
    color: var(--text);
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "Inter", system-ui, sans-serif;
    font-size: 14px;
    line-height: 1.5;
    padding: 24px 16px;
}}

.container {{
    max-width: 1400px;
    margin: 0 auto;
}}

header {{
    margin-bottom: 24px;
    text-align: center;
}}

header h1 {{
    margin: 0 0 8px 0;
    font-size: 28px;
    font-weight: 700;
    background: linear-gradient(135deg, #2563eb, #7c3aed);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
}}

.subtitle {{
    color: var(--text-muted);
    font-size: 14px;
}}

.metrics-grid {{
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
    gap: 12px;
    margin-bottom: 24px;
}}

.metric {{
    background: var(--card-bg);
    border-radius: 10px;
    padding: 16px;
    box-shadow: var(--shadow);
    text-align: center;
}}

.metric-value {{
    font-size: 28px;
    font-weight: 700;
    color: var(--primary);
    margin: 4px 0;
}}

.metric-label {{
    font-size: 12px;
    color: var(--text-muted);
    text-transform: uppercase;
    letter-spacing: 0.05em;
}}

.card {{
    background: var(--card-bg);
    border-radius: 12px;
    padding: 20px;
    margin-bottom: 20px;
    box-shadow: var(--shadow);
}}

.card h2 {{
    margin: 0 0 16px 0;
    font-size: 18px;
    font-weight: 600;
    color: var(--text);
}}

.alerts-grid {{
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
    gap: 12px;
}}

.alert-card {{
    background: var(--bg);
    border: 1px solid var(--border);
    border-radius: 10px;
    padding: 14px;
    transition: transform 0.15s, box-shadow 0.15s;
}}

.alert-card-active {{
    border-color: var(--primary);
    background: linear-gradient(135deg, rgba(37,99,235,0.05), rgba(124,58,237,0.05));
    box-shadow: var(--shadow-md);
}}

.alert-card-emoji {{
    font-size: 24px;
    margin-bottom: 4px;
}}

.alert-card-count {{
    font-size: 28px;
    font-weight: 700;
    color: var(--primary);
}}

.alert-card-label {{
    font-size: 13px;
    font-weight: 600;
    color: var(--text);
    margin-bottom: 4px;
}}

.alert-card-stocks {{
    font-size: 12px;
    color: var(--text-muted);
    word-break: break-word;
}}

.data-table {{
    width: 100%;
    border-collapse: collapse;
    font-size: 13px;
}}

.data-table th {{
    text-align: left;
    padding: 10px 8px;
    font-weight: 600;
    color: var(--text-muted);
    text-transform: uppercase;
    letter-spacing: 0.04em;
    font-size: 11px;
    border-bottom: 2px solid var(--border);
    cursor: pointer;
    user-select: none;
    position: sticky;
    top: 0;
    background: var(--card-bg);
    z-index: 1;
}}

.data-table th:hover {{
    color: var(--primary);
}}

.data-table td {{
    padding: 10px 8px;
    border-bottom: 1px solid var(--border);
}}

.data-table tr:hover td {{
    background: var(--bg);
}}

.data-table .num {{
    text-align: right;
    font-variant-numeric: tabular-nums;
    font-feature-settings: "tnum";
}}

.stock-name {{
    font-weight: 600;
}}

.alert-badge {{
    display: inline-block;
    margin-left: 4px;
    font-size: 12px;
}}

.positive {{ color: var(--positive); font-weight: 600; }}
.negative {{ color: var(--negative); font-weight: 600; }}
.neutral {{ color: var(--neutral); }}

.rating-pill {{
    display: inline-block;
    padding: 3px 10px;
    border-radius: 999px;
    font-size: 11px;
    font-weight: 600;
    white-space: nowrap;
}}

.rating-buy {{ background: var(--buy-bg); color: var(--buy); }}
.rating-sell {{ background: var(--sell-bg); color: var(--sell); }}
.rating-hold {{ background: var(--hold-bg); color: var(--hold); }}
.rating-na {{ background: var(--na-bg); color: var(--na); }}

.error-row td {{
    background: var(--sell-bg);
    color: var(--sell);
}}

.error-msg {{
    font-family: monospace;
    font-size: 12px;
    color: var(--negative);
}}

.search-box {{
    width: 100%;
    padding: 10px 14px;
    margin-bottom: 12px;
    border: 1px solid var(--border);
    border-radius: 8px;
    font-size: 14px;
    background: var(--bg);
    color: var(--text);
}}

.search-box:focus {{
    outline: 2px solid var(--primary);
    outline-offset: -1px;
}}

.table-wrap {{
    overflow-x: auto;
    max-height: 600px;
    overflow-y: auto;
}}

footer {{
    text-align: center;
    color: var(--text-muted);
    font-size: 12px;
    margin-top: 32px;
    padding: 16px;
}}

@media (max-width: 600px) {{
    body {{ padding: 12px 8px; }}
    header h1 {{ font-size: 22px; }}
    .metric-value {{ font-size: 22px; }}
    .alerts-grid {{ grid-template-columns: 1fr; }}
}}
</style>
</head>
<body>
<div class="container">
    <header>
        <h1>Nifty50 Scan Report</h1>
        <div class="subtitle">Generated {timestamp}</div>
    </header>
    
    <div class="metrics-grid">
        <div class="metric">
            <div class="metric-label">Stocks Scanned</div>
            <div class="metric-value">{success}/{total}</div>
        </div>
        <div class="metric">
            <div class="metric-label">Total Alerts</div>
            <div class="metric-value">{total_alerts}</div>
        </div>
        <div class="metric">
            <div class="metric-label">Errors</div>
            <div class="metric-value" style="color: {'var(--negative)' if errors else 'var(--text-muted)'}">{len(errors)}</div>
        </div>
        <div class="metric">
            <div class="metric-label">Buy Rated</div>
            <div class="metric-value" style="color: var(--buy)">{len([r for r in ratings.values() if r.get('label') in ('Buy', 'Strong Buy')])}</div>
        </div>
        <div class="metric">
            <div class="metric-label">Sell Rated</div>
            <div class="metric-value" style="color: var(--sell)">{len([r for r in ratings.values() if r.get('label') in ('Sell', 'Strong Sell')])}</div>
        </div>
    </div>
    
    <section class="card">
        <h2>📊 Today's Alert Summary</h2>
        <div class="alerts-grid">
            {alert_cards_html}
        </div>
    </section>
    
    <section class="card">
        <h2>🏢 All Stocks</h2>
        <input class="search-box" id="searchInput" placeholder="🔍 Search stocks..." oninput="filterTable()">
        <div class="table-wrap">
            <table class="data-table" id="stocksTable">
                <thead>
                    <tr>
                        <th onclick="sortTable(0)">Stock</th>
                        <th onclick="sortTable(1)">LTP</th>
                        <th onclick="sortTable(2)">Day %</th>
                        <th onclick="sortTable(3)">Gap %</th>
                        <th onclick="sortTable(4)">ATR</th>
                        <th onclick="sortTable(5)">Rating</th>
                        <th onclick="sortTable(6)"># Analysts</th>
                        <th onclick="sortTable(7)">Target</th>
                        <th onclick="sortTable(8)">Upside</th>
                        <th onclick="sortTable(9)">52W High</th>
                        <th onclick="sortTable(10)">52W Low</th>
                    </tr>
                </thead>
                <tbody>
                    {''.join(stock_rows)}
                </tbody>
            </table>
        </div>
    </section>
    
    {top_picks_section}
    {sell_section}
    {error_section}
    
    <footer>
        Generated by Nifty50 Gap Monitor • Analyst ratings from Yahoo Finance<br>
        Not investment advice. Verify all data independently before trading.
    </footer>
</div>

<script>
function filterTable() {{
    const input = document.getElementById('searchInput').value.toLowerCase();
    const table = document.getElementById('stocksTable');
    const rows = table.getElementsByTagName('tr');
    for (let i = 1; i < rows.length; i++) {{
        const cells = rows[i].getElementsByTagName('td');
        let match = false;
        for (let j = 0; j < cells.length; j++) {{
            if (cells[j].textContent.toLowerCase().includes(input)) {{
                match = true;
                break;
            }}
        }}
        rows[i].style.display = match ? '' : 'none';
    }}
}}

let sortDirection = {{}};
function sortTable(colIndex) {{
    const table = document.getElementById('stocksTable');
    const tbody = table.tBodies[0];
    const rows = Array.from(tbody.rows);
    
    sortDirection[colIndex] = !sortDirection[colIndex];
    const dir = sortDirection[colIndex] ? 1 : -1;
    
    rows.sort((a, b) => {{
        const aText = a.cells[colIndex]?.textContent.trim() || '';
        const bText = b.cells[colIndex]?.textContent.trim() || '';
        
        // Try parsing as number first
        const aNum = parseFloat(aText.replace(/[₹,%+]/g, ''));
        const bNum = parseFloat(bText.replace(/[₹,%+]/g, ''));
        
        if (!isNaN(aNum) && !isNaN(bNum)) {{
            return (aNum - bNum) * dir;
        }}
        return aText.localeCompare(bText) * dir;
    }});
    
    rows.forEach(row => tbody.appendChild(row));
}}
</script>
</body>
</html>"""
    
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)
    
    return output_path
