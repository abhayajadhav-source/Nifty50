import yfinance as yf


def get_analyst_rating(yahoo_symbol):
    """
    Fetch analyst recommendations from Yahoo Finance.
    Returns dict with rating breakdown, mean target, current consensus.
    """
    try:
        ticker = yf.Ticker(yahoo_symbol)
        info = ticker.info or {}
        
        # Recommendation key: from "strongBuy" to "strongSell"
        recommendation_mean = info.get("recommendationMean")
        recommendation_key = info.get("recommendationKey", "none")
        target_mean = info.get("targetMeanPrice")
        target_high = info.get("targetHighPrice")
        target_low = info.get("targetLowPrice")
        num_analysts = info.get("numberOfAnalystOpinions")
        current_price = info.get("currentPrice") or info.get("regularMarketPrice")
        
        upside_pct = None
        if target_mean and current_price:
            upside_pct = round(((target_mean - current_price) / current_price) * 100, 2)
        
        # Map mean (1.0=Strong Buy, 5.0=Strong Sell) to label
        label = "N/A"
        if recommendation_mean:
            if recommendation_mean <= 1.5:
                label = "Strong Buy"
            elif recommendation_mean <= 2.5:
                label = "Buy"
            elif recommendation_mean <= 3.5:
                label = "Hold"
            elif recommendation_mean <= 4.5:
                label = "Sell"
            else:
                label = "Strong Sell"
        
        return {
            "label": label,
            "key": recommendation_key,
            "mean": round(recommendation_mean, 2) if recommendation_mean else None,
            "num_analysts": num_analysts,
            "target_mean": round(target_mean, 2) if target_mean else None,
            "target_high": round(target_high, 2) if target_high else None,
            "target_low": round(target_low, 2) if target_low else None,
            "current_price": round(current_price, 2) if current_price else None,
            "upside_pct": upside_pct,
            "available": True,
        }
    except Exception as e:
        return {"label": "N/A", "available": False, "error": str(e)}
