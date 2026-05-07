import requests
from datetime import datetime, timedelta


SERPER_URL = "https://google.serper.dev/news"
MAX_NEWS_ITEMS = 3
NEWS_RECENCY_HOURS = 24


def fetch_stock_news(api_key, stock_name, max_items=MAX_NEWS_ITEMS):
    """
    Fetches recent news headlines for a stock via Serper Google News API.
    Returns list of {title, snippet, source, date, link} dicts. Empty list on failure.
    """
    if not api_key:
        return []
    
    # Build search query — Indian stock context
    query = f"{stock_name} stock NSE India"
    
    headers = {
        "X-API-KEY": api_key,
        "Content-Type": "application/json",
    }
    
    payload = {
        "q": query,
        "gl": "in",         # geo: India
        "hl": "en",         # language: English
        "num": max_items,
        "tbs": "qdr:d",     # time filter: past 24 hours
    }
    
    try:
        r = requests.post(SERPER_URL, json=payload, headers=headers, timeout=10)
        if r.status_code != 200:
            print(f"    Serper API error: {r.status_code} - {r.text[:200]}")
            return []
        
        data = r.json()
        news_items = data.get("news", [])
        
        results = []
        for item in news_items[:max_items]:
            results.append({
                "title": item.get("title", ""),
                "snippet": item.get("snippet", "")[:200],
                "source": item.get("source", ""),
                "date": item.get("date", ""),
                "link": item.get("link", ""),
            })
        return results
    except requests.exceptions.Timeout:
        print(f"    Serper API timeout for {stock_name}")
        return []
    except Exception as e:
        print(f"    Serper API failed for {stock_name}: {e}")
        return []


def format_news_for_telegram(news_items):
    """Returns a Telegram-friendly multi-line news block. Empty string if no news."""
    if not news_items:
        return ""
    
    lines = ["\n📰 Recent News (last 24h):"]
    for i, item in enumerate(news_items, 1):
        title = item["title"][:120]  # truncate long titles
        source = item.get("source", "Unknown")
        date = item.get("date", "")
        # Format like: "1. <title> — <source>, <date>"
        line = f"  {i}. {title}"
        if source or date:
            meta = f" — {source}" if source else ""
            meta += f", {date}" if date else ""
            line += meta
        lines.append(line)
    
    return "\n".join(lines)


def is_significant_gap(open_price, prev_close, threshold_pct=1.5):
    """Returns True if gap is >= threshold (default 1.5%)."""
    if not open_price or not prev_close:
        return False
    gap_pct = abs((open_price - prev_close) / prev_close) * 100
    return gap_pct >= threshold_pct
