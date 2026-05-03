import finnhub
from datetime import datetime, timedelta

def fetch_recent_news(client, symbol, days=2):
    to_date = datetime.now().strftime("%Y-%m-%d")
    from_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    try:
        news = client.company_news(symbol, _from=from_date, to=to_date)
        return [{"headline": n["headline"],
                 "summary": (n.get("summary") or "")[:300],
                 "source": n["source"],
                 "url": n["url"]} for n in news[:5]]
    except Exception as e:
        return [{"error": str(e)}]
