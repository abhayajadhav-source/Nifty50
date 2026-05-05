import os, json, time, sys
from datetime import datetime
import pytz

sys.path.insert(0, os.path.dirname(__file__))
from gap_detector import analyze_gap
from breakout_detector import analyze_breakout
from gap_fill_detector import analyze_gap_fill
from orb_detector import analyze_orb, is_in_or_window, is_after_or_window
from ma_trend_detector import analyze_ma_trend
from cprbo_detector import analyze_cprbo
from atr_calculator import calculate_atr
from quote_fetcher import (
    get_upstox_quote, get_upstox_daily_candles, get_upstox_intraday_candles,
    get_upstox_yesterday_ohlc, get_mock_quote, get_mock_candles,
    get_mock_intraday_candles, get_mock_yesterday_ohlc,
)
from telegram_notifier import (
    send_alert, send_breakout_alert, send_gap_fill_alert, send_orb_alert,
    send_ma_trend_alert, send_cprbo_alert,
)

IST = pytz.timezone("Asia/Kolkata")
MOCK_MODE = os.getenv("MOCK_MODE", "false").lower() == "true"

# Time markers
MORNING_END_IST = (10, 30)  # capture morning high/low through this time


def is_market_hours():
    now = datetime.now(IST)
    if now.weekday() >= 5:
        return False
    minutes = now.hour * 60 + now.minute
    return 9 * 60 + 15 <= minutes <= 15 * 60 + 30


def is_in_morning_window():
    """9:15 to 10:30 — track morning high/low."""
    now = datetime.now(IST)
    minutes = now.hour * 60 + now.minute
    return 9 * 60 + 15 <= minutes <= MORNING_END_IST[0] * 60 + MORNING_END_IST[1]


def is_after_1030_ist():
    now = datetime.now(IST)
    minutes = now.hour * 60 + now.minute
    return minutes >= 10 * 60 + 30


def is_after_1300_ist():
    now = datetime.now(IST)
    minutes = now.hour * 60 + now.minute
    return minutes >= 13 * 60


def main():
    if not MOCK_MODE and not is_market_hours():
        print("Outside IST market hours. Exiting.")
        return

    tg_token = os.environ["TELEGRAM_TOKEN"]
    tg_chat = os.environ["TELEGRAM_CHAT_ID"]
    upstox_token = os.environ.get("UPSTOX_ACCESS_TOKEN", "")

    if not MOCK_MODE and not upstox_token:
        print("ERROR: UPSTOX_ACCESS_TOKEN missing")
        return

    with open("config/nifty50.json") as f:
        symbols = json.load(f)["symbols"]

    state_file = "alerted_today.json"
    today = datetime.now(IST).strftime("%Y-%m-%d")

    gap_alerted = set()
    breakout_alerted = set()
    gapfill_alerted = set()
    orb_alerted = set()
    ma_trend_alerted = set()
    cprbo_alerted = set()
    or_levels = {}
    morning_levels = {}      # {stock_name: {"high": x, "low": y}}
    atr_cache = {}
    cpr_cache = {}           # {stock_name: {"high": .., "low": .., "close": ..}}

    if os.path.exists(state_file):
        try:
            with open(state_file) as f:
                data = json.load(f)
                if data.get("date") == today:
                    gap_alerted = set(data.get("gap_alerted", []))
                    breakout_alerted = set(data.get("breakout_alerted", []))
                    gapfill_alerted = set(data.get("gapfill_alerted", []))
                    orb_alerted = set(data.get("orb_alerted", []))
                    ma_trend_alerted = set(data.get("ma_trend_alerted", []))
                    cprbo_alerted = set(data.get("cprbo_alerted", []))
                    or_levels = data.get("or_levels", {})
                    morning_levels = data.get("morning_levels", {})
                    atr_cache = data.get("atr_cache", {})
                    cpr_cache = data.get("cpr_cache", {})
        except Exception:
            pass

    in_or = is_in_or_window()
    after_or = is_after_or_window()
    in_morning = is_in_morning_window()
    after_1030 = is_after_1030_ist()
    after_1300 = is_after_1300_ist()
    
    print(f"Scanning {len(symbols)} stocks (mock={MOCK_MODE})")
    print(f"  Windows: in_or={in_or}, after_or={after_or}, in_morning={in_morning}, after_1030={after_1030}, after_1300={after_1300}")

    for sym in symbols:
        try:
            if MOCK_MODE:
                q = get_mock_quote(sym["name"])
            else:
                q = get_upstox_quote(sym["upstox"], upstox_token)

            # Compute or fetch ATR (cache once per day)
            if sym["name"] not in atr_cache:
                if MOCK_MODE:
                    daily_candles = get_mock_candles(sym["name"])
                    atr_value = calculate_atr(daily_candles)
                else:
                    try:
                        daily_candles = get_upstox_daily_candles(sym["upstox"], upstox_token, days=20)
                        atr_value = calculate_atr(daily_candles)
                    except Exception as e:
                        print(f"  {sym['name']}: ATR fetch failed - {e}")
                        atr_value = None
                if atr_value:
                    atr_cache[sym["name"]] = atr_value
            atr = atr_cache.get(sym["name"])

            # Cache yesterday's OHLC for CPR (once per day)
            if after_1300 and sym["name"] not in cpr_cache:
                if MOCK_MODE:
                    cpr_cache[sym["name"]] = get_mock_yesterday_ohlc(sym["name"])
                else:
                    try:
                        cpr_cache[sym["name"]] = get_upstox_yesterday_ohlc(sym["upstox"], upstox_token)
                    except Exception as e:
                        print(f"  {sym['name']}: yesterday OHLC fetch failed - {e}")

            # Track Opening Range during 9:15-9:30
            if in_or:
                cur = or_levels.get(sym["name"], {})
                cur_high = max(cur.get("high", 0), q["high"])
                existing_low = cur.get("low")
                cur_low = min(existing_low, q["low"]) if existing_low else q["low"]
                or_levels[sym["name"]] = {"high": cur_high, "low": cur_low}

            # Track Morning High/Low during 9:15-10:30
            if in_morning:
                cur_m = morning_levels.get(sym["name"], {})
                m_high = max(cur_m.get("high", 0), q["high"])
                existing_m_low = cur_m.get("low")
                m_low = min(existing_m_low, q["low"]) if existing_m_low else q["low"]
                morning_levels[sym["name"]] = {"high": m_high, "low": m_low}

            # ===== Strategy 1: Gap & Retracement =====
            if sym["name"] not in gap_alerted:
                signal = analyze_gap(
                    symbol=sym["upstox"], name=sym["name"],
                    prev_close=q["prev_close"], open_price=q["open"],
                    current_price=q["ltp"],
                    low_since_open=q["low"], high_since_open=q["high"],
                )
                if signal and signal.in_entry_zone and signal.holding_above_floor:
                    print(f"  {sym['name']}: GAP setup")
                    if send_alert(tg_token, tg_chat, signal):
                        gap_alerted.add(sym["name"])

            # ===== Strategy 2: 52-Week Breakout =====
            if sym["name"] not in breakout_alerted:
                bsignal = analyze_breakout(
                    symbol=sym["upstox"], name=sym["name"],
                    current_price=q["ltp"], prev_close=q["prev_close"],
                    week52_high=q.get("week52_high", 0),
                    week52_low=q.get("week52_low", 0),
                )
                if bsignal:
                    print(f"  {sym['name']}: BREAKOUT {bsignal.breakout_type.value}")
                    if send_breakout_alert(tg_token, tg_chat, bsignal):
                        breakout_alerted.add(sym["name"])

            # ===== Strategy 3: Gap Fill Rejection =====
            if sym["name"] not in gapfill_alerted and atr:
                gfsignal = analyze_gap_fill(
                    symbol=sym["upstox"], name=sym["name"],
                    prev_close=q["prev_close"], open_price=q["open"],
                    current_price=q["ltp"],
                    today_low=q["low"], today_high=q["high"],
                    atr=atr,
                )
                if gfsignal:
                    print(f"  {sym['name']}: GAP FILL REJECTION {gfsignal.direction}")
                    if send_gap_fill_alert(tg_token, tg_chat, gfsignal):
                        gapfill_alerted.add(sym["name"])

            # ===== Strategy 4: Opening Range Breakout =====
            if sym["name"] not in orb_alerted and atr and after_or:
                or_data = or_levels.get(sym["name"], {})
                if or_data.get("high") and or_data.get("low"):
                    osignal = analyze_orb(
                        symbol=sym["upstox"], name=sym["name"],
                        current_price=q["ltp"],
                        today_low=q["low"], today_high=q["high"],
                        or_high=or_data["high"], or_low=or_data["low"],
                        atr=atr,
                    )
                    if osignal:
                        print(f"  {sym['name']}: ORB {osignal.direction}")
                        if send_orb_alert(tg_token, tg_chat, osignal):
                            orb_alerted.add(sym["name"])

            # ===== Strategy 5: MA Trend Following =====
            if sym["name"] not in ma_trend_alerted and after_1030:
                if MOCK_MODE:
                    intraday = get_mock_intraday_candles(sym["name"])
                else:
                    try:
                        intraday = get_upstox_intraday_candles(sym["upstox"], upstox_token, "30minute")
                    except Exception as e:
                        intraday = []
                
                if intraday:
                    msignal = analyze_ma_trend(
                        symbol=sym["upstox"], name=sym["name"],
                        current_price=q["ltp"],
                        candles=intraday,
                    )
                    if msignal:
                        print(f"  {sym['name']}: MA TREND {msignal.direction}")
                        if send_ma_trend_alert(tg_token, tg_chat, msignal):
                            ma_trend_alerted.add(sym["name"])

            # ===== Strategy 6: CPRBO =====
            if sym["name"] not in cprbo_alerted and after_1300:
                yest_ohlc = cpr_cache.get(sym["name"])
                m_data = morning_levels.get(sym["name"], {})
                if yest_ohlc and m_data.get("high") and m_data.get("low"):
                    csignal = analyze_cprbo(
                        symbol=sym["upstox"], name=sym["name"],
                        current_price=q["ltp"],
                        today_low=q["low"], today_high=q["high"],
                        morning_high=m_data["high"], morning_low=m_data["low"],
                        yesterday_ohlc=yest_ohlc,
                    )
                    if csignal:
                        print(f"  {sym['name']}: CPRBO {csignal.direction}")
                        if send_cprbo_alert(tg_token, tg_chat, csignal):
                            cprbo_alerted.add(sym["name"])

            # Per-stock summary
            gap_pct = ((q["open"] - q["prev_close"]) / q["prev_close"] * 100) if q["prev_close"] else 0
            atr_str = f"₹{atr}" if atr else "n/a"
            print(f"  {sym['name']}: scanned (gap={gap_pct:.2f}%, ltp=₹{q['ltp']}, atr={atr_str})")

            time.sleep(0.4)
        except Exception as e:
            print(f"  {sym['name']}: ERROR - {e}")

    with open(state_file, "w") as f:
        json.dump({
            "date": today,
            "gap_alerted": list(gap_alerted),
            "breakout_alerted": list(breakout_alerted),
            "gapfill_alerted": list(gapfill_alerted),
            "orb_alerted": list(orb_alerted),
            "ma_trend_alerted": list(ma_trend_alerted),
            "cprbo_alerted": list(cprbo_alerted),
            "or_levels": or_levels,
            "morning_levels": morning_levels,
            "atr_cache": atr_cache,
            "cpr_cache": cpr_cache,
        }, f)

    print("Done.")


if __name__ == "__main__":
    main()
