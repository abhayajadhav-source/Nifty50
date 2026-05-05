import os, json, time, sys
from datetime import datetime
import pytz

sys.path.insert(0, os.path.dirname(__file__))
from gap_detector import analyze_gap
from breakout_detector import analyze_breakout
from gap_fill_detector import analyze_gap_fill
from orb_detector import analyze_orb, is_in_or_window, is_after_or_window
from atr_calculator import calculate_atr
from quote_fetcher import get_upstox_quote, get_upstox_daily_candles, get_mock_quote, get_mock_candles
from telegram_notifier import send_alert, send_breakout_alert, send_gap_fill_alert, send_orb_alert

IST = pytz.timezone("Asia/Kolkata")
MOCK_MODE = os.getenv("MOCK_MODE", "false").lower() == "true"


def is_market_hours():
    now = datetime.now(IST)
    if now.weekday() >= 5:
        return False
    minutes = now.hour * 60 + now.minute
    return 9 * 60 + 15 <= minutes <= 15 * 60 + 30


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
    or_levels = {}
    atr_cache = {}

    if os.path.exists(state_file):
        try:
            with open(state_file) as f:
                data = json.load(f)
                if data.get("date") == today:
                    gap_alerted = set(data.get("gap_alerted", []))
                    breakout_alerted = set(data.get("breakout_alerted", []))
                    gapfill_alerted = set(data.get("gapfill_alerted", []))
                    orb_alerted = set(data.get("orb_alerted", []))
                    or_levels = data.get("or_levels", {})
                    atr_cache = data.get("atr_cache", {})
        except Exception:
            pass

    in_or = is_in_or_window()
    after_or = is_after_or_window()
    print(f"Scanning {len(symbols)} stocks (mock={MOCK_MODE}) | in_or_window={in_or} | after_or_window={after_or}")

    for sym in symbols:
        try:
            if MOCK_MODE:
                q = get_mock_quote(sym["name"])
                candles = get_mock_candles(sym["name"])
            else:
                q = get_upstox_quote(sym["upstox"], upstox_token)

            # Compute or fetch ATR (cache once per day per stock)
            if sym["name"] not in atr_cache:
                if MOCK_MODE:
                    atr_value = calculate_atr(candles)
                else:
                    try:
                        candles = get_upstox_daily_candles(sym["upstox"], upstox_token, days=20)
                        atr_value = calculate_atr(candles)
                    except Exception as e:
                        print(f"  {sym['name']}: ATR fetch failed - {e}")
                        atr_value = None
                if atr_value:
                    atr_cache[sym["name"]] = atr_value
            atr = atr_cache.get(sym["name"])

            # Track Opening Range during 9:15-9:30 IST
            if in_or:
                cur = or_levels.get(sym["name"], {})
                cur_high = max(cur.get("high", 0), q["high"])
                existing_low = cur.get("low")
                cur_low = min(existing_low, q["low"]) if existing_low else q["low"]
                or_levels[sym["name"]] = {"high": cur_high, "low": cur_low}

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

            # Per-stock status line — confirms the stock was processed
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
            "or_levels": or_levels,
            "atr_cache": atr_cache,
        }, f)

    print("Done.")


if __name__ == "__main__":
    main()
