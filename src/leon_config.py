# ===================================
# LEON CONFIG
# ===================================

import configparser
from src.paths import BASE_DIR

_config = configparser.ConfigParser()
_config.read(BASE_DIR / "config.ini", encoding="utf-8")
MARKET = _config.get("OPERATOR", "market_symbol", fallback="Gold_Spot")

TIMEFRAME_MAIN = "M15"
TIMEFRAME_CONTEXT = "H4"
TIMEFRAME_BIAS = "D1"

MAX_TRADES_DAY = 0

MIN_SETUP_SCORE = 90

TELEGRAM_ENABLED = False

SHADOW_TRADE_ENABLED = True

JOURNAL_ENABLED = True

MEMORY_CONTEXT_ENABLED = True

MEMORY_SHADOW_MODE = True

VERSION = "0.2"
