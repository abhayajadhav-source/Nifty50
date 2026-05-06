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
