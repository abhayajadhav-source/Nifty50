import os, json, time, sys
from datetime import datetime
import pytz

sys.path.insert(0, os.path.dirname(__file__))
from gap_fill_detector import analyze_gap_fill
from orb_detector import analyze_orb, is_in_or_window, is_after_or_window
from ma_trend_detector import analyze_ma_trend
from cprbo_detector import analyze_cprbo
from supply_zone_detector import analyze_supply_zone
from ppt_detector import analyze_ppt, calculate_pivots, update_pressure_state
from inside_candle_detector import analyze_inside_candle
from atr_calculator import calculate_atr
from quote_fetcher import (
    get_upstox_quote, get_upstox_daily_candles, get_upstox_intraday_candles,
    get_upstox_yesterday_ohlc, get_mock_quote, get_mock_candles,
    get_mock_intraday_candles, get_mock_yesterday_ohlc,
)
from telegram_notifier import (
    send_gap_fill_alert, send_orb_alert, send_ma_trend_alert,
    send_cprbo_alert, send_supply_zone_alert, send_ppt_alert,
    send_inside_candle_alert, send_summary,
)
from gmail_notifier import send_run_summary_email

IST = pytz.timezone("Asia/Kolkata")
MOCK_MODE = os.getenv("MOCK_MODE", "false").lower() == "true"

MORNING_END_IST = (10, 30)


def is_market_hours():
    now = datetime.now(IST)
    if now.weekday() >= 5:
        return False
    minutes = now.hour * 60 + now.minute
    return 9 * 60 + 15 <= minutes <= 15 * 60 + 30


def is_in_morning_window():
    now = datetime.now(IST)
    minutes = now.hour * 60 + now.minute
    return 9 * 60 + 15 <= minutes <= MORNING_END_IST[0] * 60 + MORNING_END_IST[1]


def is_after_market_open():
    now = datetime.now(IST)
    minutes = now.hour * 60 + now.minute
    return minutes >= 9 * 60 + 15


def is_after_930_ist():
    now = datetime.now(IST)
    minutes = now.hour * 60 + now.minute
    return minutes >= 9 * 60 + 30


def is_after_1000_ist():
    now = datetime.now(IST)
    minutes = now.hour * 60 + now.minute
    return minutes >= 10 * 60


def is_after_1030_ist():
    now = datetime.now(IST)
    minutes = now.hour * 60 + now.minute
    return minutes >= 10 * 60 + 30


def is_after_1300_ist():
    now = datetime.now(IST)
    minutes = now.hour * 60 + now.minute
    return minutes >= 13 * 60


def signal_to_dict(s):
    return {
        "name": getattr(s, "name", ""),
        "direction": getattr(s, "direction", ""),
        "entry": getattr(s, "suggested_entry", ""),
        "stop_loss": getattr(s, "suggested_stop_loss", ""),
        "target": getattr(s, "suggested_target", ""),
    }


def main():
    if not MOCK_MODE and not is_market_hours():
        print("Outside IST market hours. Exiting.")
        return

    tg_token = os.environ["TELEGRAM_TOKEN"]
    tg_chat = os.environ["TELEGRAM_CHAT_ID"]
    upstox_token = os.environ.get("UPSTOX_ACCESS_TOKEN", "")
    gmail_user = os.environ.get("GMAIL_USER", "")
    gmail_pwd = os.environ.get("GMAIL_APP_PASSWORD", "")
    gmail_recipient = os.environ.get("GMAIL_RECIPIENT", "")
print(f"DEBUG: GMAIL_USER set={bool(gmail_user)}, GMAIL_APP_PASSWORD set={bool(gmail_pwd)}, GMAIL_RECIPIENT set={bool(gmail_recipient)}")
    if not MOCK_MODE and not upstox_token:
        print("ERROR: UPSTOX_ACCESS_TOKEN missing")
        return

    with open("config/nifty50.json") as f:
        symbols = json.load(f)["symbols"]

    state_file = "alerted_today.json"
    today = datetime.now(IST).strftime("%Y-%m-%d")

    gapfill_alerted = set()
    orb_alerted = set()
    ma_trend_alerted = set()
    cprbo_alerted = set()
    supply_zone_alerted = set()
    ppt_alerted = set()
    inside_candle_alerted = set()
    or_levels = {}
    morning_levels = {}
    atr_cache = {}
    cpr_cache = {}
    pressure_state = {}
    daily_candles_cache = {}

    if os.path.exists(state_file):
        try:
            with open(state_file) as f:
                data = json.load(f)
                if data.get("date") == today:
                    gapfill_alerted = set(data.get("gapfill_alerted", []))
                    orb_alerted = set(data.get("orb_alerted", []))
                    ma_trend_alerted = set(data.get("ma_trend_alerted", []))
                    cprbo_alerted = set(data.get("cprbo_alerted", []))
                    supply_zone_alerted = set(data.get("supply_zone_alerted", []))
                    ppt_alerted = set(data.get("ppt_alerted", []))
                    inside_candle_alerted = set(data.get("inside_candle_alerted", []))
                    or_levels = data.get("or_levels", {})
                    morning_levels = data.get("morning_levels", {})
                    atr_cache = data.get("atr_cache", {})
                    cpr_cache = data.get("cpr_cache", {})
                    pressure_state = data.get("pressure_state", {})
        except Exception:
            pass

    initial_counts = {
        "gapfill": len(gapfill_alerted),
        "orb": len(orb_alerted),
        "ma_trend": len(ma_trend_alerted),
        "cprbo": len(cprbo_alerted),
        "supply_zone": len(supply_zone_alerted),
        "ppt": len(ppt_alerted),
        "inside_candle": len(inside_candle_alerted),
    }

    new_alert_details = {
        "gapfill": [],
        "orb": [],
        "ma_trend": [],
        "cprbo": [],
        "supply_zone": [],
        "ppt": [],
        "inside_candle": [],
    }

    in_or = is_in_or_window()
    after_or = is_after_or_window()
    in_morning = is_in_morning_window()
    after_open = is_after_market_open()
    after_930 = is_after_930_ist()
    after_1000 = is_after_1000_ist()
    after_1030 = is_after_1030_ist()
    after_1300 = is_after_1300_ist()

    print(f"Scanning {len(symbols)} stocks (mock={MOCK_MODE})")
    print(f"  Windows: in_or={in_or}, after_or={after_or}, after_930={after_930}, after_1000={after_1000}, after_1030={after_1030}, after_1300={after_1300}")

    error_count = 0
    errors = {}

    for sym in symbols:
        try:
            if MOCK_MODE:
                q = get_mock_quote(sym["name"])
            else:
                q = get_upstox_quote(sym["upstox"], upstox_token)

            if sym["name"] not in daily_candles_cache:
                if MOCK_MODE:
                    daily_candles = get_mock_candles(sym["name"], days=20)
                else:
                    try:
                        daily_candles = get_upstox_daily_candles(sym["upstox"], upstox_token, days=20)
                    except Exception as e:
                        print(f"  {sym['name']}: daily candles failed - {e}")
                        daily_candles = None
                if daily_candles:
                    daily_candles_cache[sym["name"]] = daily_candles
            daily_candles = daily_candles_cache.get(sym["name"])

            if sym["name"] not in atr_cache and daily_candles:
                atr_value = calculate_atr(daily_candles)
                if atr_value:
                    atr_cache[sym["name"]] = atr_value
            atr = atr_cache.get(sym["name"])

            if sym["name"] not in cpr_cache:
                if MOCK_MODE:
                    cpr_cache[sym["name"]] = get_mock_yesterday_ohlc(sym["name"])
                else:
                    try:
                        cpr_cache[sym["name"]] = get_upstox_yesterday_ohlc(sym["upstox"], upstox_token)
                    except Exception as e:
                        print(f"  {sym['name']}: yesterday OHLC failed - {e}")

            yesterday_ohlc = cpr_cache.get(sym["name"])

            if in_or:
                cur = or_levels.get(sym["name"], {})
                cur_high = max(cur.get("high", 0), q["high"])
                existing_low = cur.get("low")
                cur_low = min(existing_low, q["low"]) if existing_low else q["low"]
                or_levels[sym["name"]] = {"high": cur_high, "low": cur_low}

            if in_morning:
                cur_m = morning_levels.get(sym["name"], {})
                m_high = max(cur_m.get("high", 0), q["high"])
                existing_m_low = cur_m.get("low")
                m_low = min(existing_m_low, q["low"]) if existing_m_low else q["low"]
                morning_levels[sym["name"]] = {"high": m_high, "low": m_low}

            if after_open and yesterday_ohlc:
                pivots = calculate_pivots(yesterday_ohlc)
                cur_pressure = pressure_state.get(sym["name"], {})
                pressure_state[sym["name"]] = update_pressure_state(cur_pressure, q["ltp"], pivots)

            # === Strategy 3: Gap Fill Rejection ===
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
                        new_alert_details["gapfill"].append(signal_to_dict(gfsignal))

            # === Strategy 4: ORB ===
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
                            new_alert_details["orb"].append(signal_to_dict(osignal))

            # === Strategy 5: MA Trend ===
            if sym["name"] not in ma_trend_alerted and after_1030:
                if MOCK_MODE:
                    intraday = get_mock_intraday_candles(sym["name"])
                else:
                    try:
                        intraday = get_upstox_intraday_candles(sym["upstox"], upstox_token, "30minute")
                    except Exception:
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
                            new_alert_details["ma_trend"].append(signal_to_dict(msignal))

            # === Strategy 6: CPRBO ===
            if sym["name"] not in cprbo_alerted and after_1300:
                m_data = morning_levels.get(sym["name"], {})
                if yesterday_ohlc and m_data.get("high") and m_data.get("low"):
                    csignal = analyze_cprbo(
                        symbol=sym["upstox"], name=sym["name"],
                        current_price=q["ltp"],
                        today_low=q["low"], today_high=q["high"],
                        morning_high=m_data["high"], morning_low=m_data["low"],
                        yesterday_ohlc=yesterday_ohlc,
                    )
                    if csignal:
                        print(f"  {sym['name']}: CPRBO {csignal.direction}")
                        if send_cprbo_alert(tg_token, tg_chat, csignal):
                            cprbo_alerted.add(sym["name"])
                            new_alert_details["cprbo"].append(signal_to_dict(csignal))

            # === Strategy 7: Supply Zone ===
            if sym["name"] not in supply_zone_alerted and after_1000 and daily_candles:
                szsignal = analyze_supply_zone(
                    symbol=sym["upstox"], name=sym["name"],
                    current_price=q["ltp"],
                    candles=daily_candles,
                )
                if szsignal:
                    print(f"  {sym['name']}: SUPPLY ZONE BREAKOUT")
                    if send_supply_zone_alert(tg_token, tg_chat, szsignal):
                        supply_zone_alerted.add(sym["name"])
                        new_alert_details["supply_zone"].append(signal_to_dict(szsignal))

            # === Strategy 8: PPT ===
            if sym["name"] not in ppt_alerted and yesterday_ohlc and atr:
                pstate = pressure_state.get(sym["name"], {})
                pptsignal = analyze_ppt(
                    symbol=sym["upstox"], name=sym["name"],
                    current_price=q["ltp"], open_price=q["open"],
                    today_high=q["high"], today_low=q["low"],
                    yesterday_ohlc=yesterday_ohlc,
                    pressure_state=pstate,
                    atr=atr,
                )
                if pptsignal:
                    print(f"  {sym['name']}: PPT {pptsignal.direction}")
                    if send_ppt_alert(tg_token, tg_chat, pptsignal):
                        ppt_alerted.add(sym["name"])
                        new_alert_details["ppt"].append(signal_to_dict(pptsignal))

            # === Strategy 9: Inside Candle Halt ===
            if sym["name"] not in inside_candle_alerted and after_930 and yesterday_ohlc and atr:
                icsignal = analyze_inside_candle(
                    symbol=sym["upstox"], name=sym["name"],
                    current_price=q["ltp"],
                    today_high=q["high"], today_low=q["low"],
                    yesterday_ohlc=yesterday_ohlc,
                    atr=atr,
                )
                if icsignal:
                    print(f"  {sym['name']}: INSIDE CANDLE {icsignal.direction}")
                    if send_inside_candle_alert(tg_token, tg_chat, icsignal):
                        inside_candle_alerted.add(sym["name"])
                        new_alert_details["inside_candle"].append(signal_to_dict(icsignal))

            atr_str = f"₹{atr}" if atr else "n/a"
            print(f"  {sym['name']}: scanned (ltp=₹{q['ltp']}, atr={atr_str})")

            time.sleep(0.4)
        except Exception as e:
            error_count += 1
            err_msg = str(e)
            errors[sym["name"]] = err_msg
            print(f"  {sym['name']}: ERROR - {err_msg}")

    with open(state_file, "w") as f:
        json.dump({
            "date": today,
            "gapfill_alerted": list(gapfill_alerted),
            "orb_alerted": list(orb_alerted),
            "ma_trend_alerted": list(ma_trend_alerted),
            "cprbo_alerted": list(cprbo_alerted),
            "supply_zone_alerted": list(supply_zone_alerted),
            "ppt_alerted": list(ppt_alerted),
            "inside_candle_alerted": list(inside_candle_alerted),
            "or_levels": or_levels,
            "morning_levels": morning_levels,
            "atr_cache": atr_cache,
            "cpr_cache": cpr_cache,
            "pressure_state": pressure_state,
        }, f)

    new_alerts = {
        "gapfill": len(gapfill_alerted) - initial_counts["gapfill"],
        "orb": len(orb_alerted) - initial_counts["orb"],
        "ma_trend": len(ma_trend_alerted) - initial_counts["ma_trend"],
        "cprbo": len(cprbo_alerted) - initial_counts["cprbo"],
        "supply_zone": len(supply_zone_alerted) - initial_counts["supply_zone"],
        "ppt": len(ppt_alerted) - initial_counts["ppt"],
        "inside_candle": len(inside_candle_alerted) - initial_counts["inside_candle"],
    }

    summary_data = {
        "total_scanned": len(symbols),
        "errors": error_count,
        "timestamp": datetime.now(IST).strftime("%H:%M IST"),
        "alerts_today": {
            "gapfill": list(gapfill_alerted),
            "orb": list(orb_alerted),
            "ma_trend": list(ma_trend_alerted),
            "cprbo": list(cprbo_alerted),
            "supply_zone": list(supply_zone_alerted),
            "ppt": list(ppt_alerted),
            "inside_candle": list(inside_candle_alerted),
        },
        "new_alerts_this_run": new_alerts,
    }

    now = datetime.now(IST)
    minutes = now.hour * 60 + now.minute
    summary_times = [9 * 60 + 30, 11 * 60 + 30, 13 * 60 + 30, 15 * 60 + 30]
    if any(stime <= minutes < stime + 5 for stime in summary_times):
        send_summary(tg_token, tg_chat, summary_data)

    if gmail_user and gmail_pwd and gmail_recipient:
        run_data = {
            "total_scanned": len(symbols),
            "error_count": error_count,
            "alerts_today": summary_data["alerts_today"],
            "new_alerts_this_run": new_alerts,
            "new_alert_details": new_alert_details,
            "errors": errors,
        }
        send_run_summary_email(gmail_user, gmail_pwd, gmail_recipient, run_data)
    else:
        print("Gmail credentials not configured; skipping email summary")

    print("Done.")


if __name__ == "__main__":
    main()
