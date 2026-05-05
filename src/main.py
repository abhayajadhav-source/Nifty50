import os, json, time, sys
from datetime import datetime
import pytz

sys.path.insert(0, os.path.dirname(__file__))
from gap_detector import analyze_gap
from breakout_detector import analyze_breakout
from quote_fetcher import get_upstox_quote, get_mock_quote
from telegram_notifier import send_alert, send_breakout_alert

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
        print("ERROR: UPSTOX_ACCESS_TOKEN missing from secrets")
        return

    with open("config/nifty50.json") as f:
        symbols = json.load(f)["symbols"]

    state_file = "alerted_today.json"
    today = datetime.now(IST).strftime("%Y-%m-%d")
    
    # Two separate de-dup sets: gap alerts and breakout alerts
    gap_alerted = set()
    breakout_alerted = set()
    
    if os.path.exists(state_file):
        try:
            with open(state_file) as f:
                data = json.load(f)
                if data.get("date") == today:
                    gap_alerted = set(data.get("gap_alerted", []))
                    breakout_alerted = set(data.get("breakout_alerted", []))
        except Exception:
            pass

    print(f"Scanning {len(symbols)} stocks (mock={MOCK_MODE})...")

    for sym in symbols:
        try:
            if MOCK_MODE:
                q = get_mock_quote(sym["name"])
            else:
                q = get_upstox_quote(sym["upstox"], upstox_token)

            # ===== Strategy 1: Gap and Retracement =====
            if sym["name"] not in gap_alerted:
                signal = analyze_gap(
                    symbol=sym["upstox"], name=sym["name"],
                    prev_close=q["prev_close"], open_price=q["open"],
                    current_price=q["ltp"],
                    low_since_open=q["low"], high_since_open=q["high"],
                )
                if signal and signal.in_entry_zone and signal.holding_above_floor:
                    print(f"  {sym['name']}: GAP SETUP — sending alert")
                    if send_alert(tg_token, tg_chat, signal):
                        gap_alerted.add(sym["name"])
                elif signal:
                    if not signal.in_entry_zone:
                        print(f"  {sym['name']}: gap {signal.gap_pct}% retrace {signal.retracement_pct}% not in zone")
                    elif not signal.holding_above_floor:
                        print(f"  {sym['name']}: broke floor")
                else:
                    gap_pct = ((q["open"] - q["prev_close"]) / q["prev_close"] * 100) if q["prev_close"] else 0
                    print(f"  {sym['name']}: no qualifying gap (gap={gap_pct:.2f}%)")
            
            # ===== Strategy 2: 52-Week Breakout =====
            if sym["name"] not in breakout_alerted:
                breakout_signal = analyze_breakout(
                    symbol=sym["upstox"], name=sym["name"],
                    current_price=q["ltp"], prev_close=q["prev_close"],
                    week52_high=q.get("week52_high", 0),
                    week52_low=q.get("week52_low", 0),
                )
                if breakout_signal:
                    print(f"  {sym['name']}: BREAKOUT {breakout_signal.breakout_type.value} — sending alert")
                    if send_breakout_alert(tg_token, tg_chat, breakout_signal):
                        breakout_alerted.add(sym["name"])
            
            time.sleep(0.3)
        except Exception as e:
            print(f"  {sym['name']}: ERROR - {e}")

    with open(state_file, "w") as f:
        json.dump({
            "date": today,
            "gap_alerted": list(gap_alerted),
            "breakout_alerted": list(breakout_alerted),
        }, f)

    print("Done.")


if __name__ == "__main__":
    main()
