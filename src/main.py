import os, json, time, sys
from datetime import datetime
import pytz

sys.path.insert(0, os.path.dirname(__file__))
from gap_detector import analyze_gap
from quote_fetcher import get_upstox_quote, get_mock_quote
from telegram_notifier import send_alert

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
    alerted = set()
    if os.path.exists(state_file):
        try:
            with open(state_file) as f:
                data = json.load(f)
                if data.get("date") == today:
                    alerted = set(data.get("alerted", []))
        except Exception:
            pass

    print(f"Scanning {len(symbols)} stocks (mock={MOCK_MODE})...")

    for sym in symbols:
        if sym["name"] in alerted:
            print(f"  {sym['name']}: already alerted today, skipping")
            continue
        try:
            if MOCK_MODE:
                q = get_mock_quote(sym["name"])
            else:
                q = get_upstox_quote(sym["upstox"], upstox_token)

            signal = analyze_gap(
                symbol=sym["upstox"], name=sym["name"],
                prev_close=q["prev_close"], open_price=q["open"],
                current_price=q["ltp"],
                low_since_open=q["low"], high_since_open=q["high"],
            )
            if not signal:
                gap_pct = ((q["open"] - q["prev_close"]) / q["prev_close"] * 100) if q["prev_close"] else 0
                print(f"  {sym['name']}: no qualifying gap (gap={gap_pct:.2f}%)")
                continue
            if not signal.in_entry_zone:
                print(f"  {sym['name']}: gap {signal.gap_pct}% but retracement {signal.retracement_pct}% not in zone")
                continue
            if not signal.holding_above_floor:
                print(f"  {sym['name']}: broke floor, invalid")
                continue

            print(f"  {sym['name']}: VALID SETUP — sending alert")
            success = send_alert(tg_token, tg_chat, signal)
            if success:
                alerted.add(sym["name"])
            else:
                print(f"  {sym['name']}: alert failed, will retry next run")

            time.sleep(0.3)
        except Exception as e:
            print(f"  {sym['name']}: ERROR - {e}")

    with open(state_file, "w") as f:
        json.dump({"date": today, "alerted": list(alerted)}, f)

    print("Done.")


if __name__ == "__main__":
    main()
