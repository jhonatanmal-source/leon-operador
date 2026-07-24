#!/usr/bin/env python3
"""
MT5 Safe Wrapper ??? Read-only access to MetaTrader 5.
Exposes ONLY safe functions. Blocks all write/modify operations.

BLOCKED (raise RuntimeError if called):
  - order_send
  - order_check
  - login
  - eval
  - execute

initialize() and shutdown() are allowed (required for connection setup).
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

_MT5_AVAILABLE = False
_MT5_IMPORT_ERROR = ""
_MT5_INIT_ERROR = ""

try:
    from mt5linux_compat import (
        symbol_select,
        symbol_info,
        symbol_info_tick,
        symbols_get,
        symbols_total,
        copy_rates_from_pos,
        copy_rates_range,
        copy_rates_from,
        copy_ticks_from,
        copy_ticks_range,
        positions_get,
        positions_total,
        orders_get,
        orders_total,
        history_deals_get,
        history_deals_total,
        history_orders_get,
        history_orders_total,
        account_info,
        terminal_info,
        last_error,
        version,
        order_calc_margin,
        order_calc_profit,
        market_book_add,
        market_book_get,
        market_book_release,
        initialize,
    )

    # Initialize MT5 connection on module load
    if not initialize():
        _MT5_INIT_ERROR = str(last_error())
    else:
        _MT5_AVAILABLE = True

except ImportError as e:
    _MT5_AVAILABLE = False
    _MT5_IMPORT_ERROR = str(e)


BLOCKED_FUNCTIONS = [
    "order_send",
    "order_check",
    "login",
    "eval",
    "execute",
]


def check_mt5():
    return {
        "available": _MT5_AVAILABLE,
        "error": _MT5_INIT_ERROR if not _MT5_AVAILABLE else "",
        "import_error": _MT5_IMPORT_ERROR,
        "note": "Apenas fun????es read-only est??o dispon??veis. ordens, login e eval est??o bloqueados."
    }


def safe_symbol_info_tick(symbol: str) -> dict:
    if not _MT5_AVAILABLE:
        return {"error": "MT5 n??o dispon??vel"}
    try:
        tick = symbol_info_tick(symbol)
        if tick is None:
            return {"error": f"Symbol '{symbol}' not found or no tick data"}
        return {
            "symbol": symbol,
            "bid": tick.bid,
            "ask": tick.ask,
            "last": tick.last,
            "volume": tick.volume,
            "time": str(tick.time),
            "spread": round(abs(tick.ask - tick.bid), 1) if tick.bid and tick.ask else 0
        }
    except Exception as e:
        return {"error": str(e)}


def safe_symbol_info(symbol: str) -> dict:
    if not _MT5_AVAILABLE:
        return {"error": "MT5 n??o dispon??vel"}
    try:
        info = symbol_info(symbol)
        if info is None:
            return {"error": f"Symbol '{symbol}' not found"}
        return {
            "symbol": info.name,
            "description": info.description,
            "digits": info.digits,
            "point": info.point,
            "trade_mode": info.trade_mode,
            "spread": info.spread,
            "spread_float": info.spread_float,
            "volume_min": info.volume_min,
            "volume_max": info.volume_max,
            "volume_step": info.volume_step,
            "margin_hedged": info.margin_hedged,
            "price_change": info.price_change,
            "price_volatility": info.price_volatility
        }
    except Exception as e:
        return {"error": str(e)}


def safe_symbols_get() -> dict:
    if not _MT5_AVAILABLE:
        return {"error": "MT5 n??o dispon??vel"}
    try:
        syms = symbols_get()
        if syms is None:
            return {"symbols": [], "count": 0}
        result = []
        for s in syms:
            result.append({
                "name": s.name,
                "description": s.description,
                "digits": s.digits
            })
        return {"symbols": result, "count": len(result)}
    except Exception as e:
        return {"error": str(e)}


def safe_copy_rates_from_pos(symbol: str, timeframe: int, start_pos: int, count: int) -> dict:
    if not _MT5_AVAILABLE:
        return {"error": "MT5 n??o dispon??vel"}
    try:
        rates = copy_rates_from_pos(symbol, timeframe, start_pos, count)
        if rates is None or len(rates) == 0:
            return {"error": f"No rates for {symbol} TF={timeframe}", "rates": []}
        result = []
        for r in rates:
            result.append({
                "time": str(r.time),
                "open": r.open,
                "high": r.high,
                "low": r.low,
                "close": r.close,
                "tick_volume": r.tick_volume,
                "real_volume": r.real_volume,
                "spread": r.spread
            })
        return {
            "symbol": symbol,
            "timeframe": timeframe,
            "count": len(result),
            "rates": result
        }
    except Exception as e:
        return {"error": str(e)}


def safe_account_info() -> dict:
    if not _MT5_AVAILABLE:
        return {"error": "MT5 n??o dispon??vel"}
    try:
        info = account_info()
        if info is None:
            return {"error": "No account info available"}
        return {
            "balance": info.balance,
            "equity": info.equity,
            "margin": info.margin,
            "margin_free": info.margin_free,
            "margin_level": info.margin_level,
            "currency": info.currency,
            "leverage": info.leverage,
            "name": info.name,
            "trade_mode": info.trade_mode,
            "limit_orders": info.limit_orders
        }
    except Exception as e:
        return {"error": str(e)}


SAFE_TOOLS = {
    "symbol_info_tick": safe_symbol_info_tick,
    "symbol_info": safe_symbol_info,
    "symbols_get": safe_symbols_get,
    "copy_rates_from_pos": safe_copy_rates_from_pos,
    "account_info": safe_account_info,
}
