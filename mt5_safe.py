#!/usr/bin/env python3
"""
MT5 Safe Module — Drop-in replacement for 'import mt5linux_compat as mt5'.

Provides safe read-only access to MetaTrader 5 by proxying ALL functions
from mt5linux_compat EXCEPT the blocked dangerous ones, which raise RuntimeError.

BLOCKED (raise RuntimeError if accessed):
  - order_send     → sending orders
  - order_check    → checking order parameters
  - login          → changing account
  - eval           → executing arbitrary MT5 expressions
  - execute        → executing custom commands

Usage as drop-in replacement:
    import mt5_safe as mt5   # safe proxy (same API, dangerous calls blocked)

    mt5.initialize()             # OK
    mt5.symbol_info_tick(...)    # OK
    mt5.account_info()           # OK
    mt5.order_send(...)          # RuntimeError! BLOCKED

Also exports safe wrapper functions (dict-based returns) for MCP layer:
    from mt5_safe import safe_symbol_info_tick, safe_account_info, ...

SAFETY: This is a FIRST LINE OF DEFENSE. Code that legitimately needs
order_send (like mt5_order_executor) imports mt5linux_compat DIRECTLY
and MUST pass through all operational guards before calling it.

Design: Python 3.7+ module __getattr__ for transparent proxy.
"""

import sys as _sys
import types as _types

# Import the real module as fallback.
# __getattr__ looks up sys.modules dynamically so that test patches work.
import mt5linux_compat as _real_mt5

# ── Blocked functions ──────────────────────────────────────────
# These raise RuntimeError if accessed via mt5_safe.
_BLOCKED = frozenset({
    "order_send",
    "order_check",
    "login",
    "eval",
    "execute",
})

# ── MT5 connection state (lazy, set only when initialize is called) ──
_MT5_AVAILABLE: bool = False
_MT5_INIT_ERROR: str = ""
_MT5_IMPORT_ERROR: str = ""


def _resolve_mt5():
    """Resolve the mt5linux_compat module dynamically.

    Checks sys.modules first (allows test patching), falls back to
    the import-time reference.
    """
    return _sys.modules.get("mt5linux_compat", _real_mt5)


def __getattr__(name: str):
    """Proxy any attribute to the real mt5linux_compat module.

    Blocked functions raise RuntimeError. Private attributes raise
    AttributeError. Everything else is forwarded transparently.
    """
    if name in _BLOCKED:
        raise RuntimeError(
            f"MT5_SAFE_BLOCKED: '{name}' is not allowed via mt5_safe.\n"
            f"  This is a safety measure to prevent accidental order execution.\n"
            f"  If you need '{name}', import mt5linux_compat directly and\n"
            f"  ensure all operational guards (SMC, risk, news, autonomy)\n"
            f"  have passed before calling it."
        )
    if name.startswith("_"):
        raise AttributeError(f"module 'mt5_safe' has no attribute {name!r}")
    target = _resolve_mt5()
    if not hasattr(target, name):
        raise AttributeError(
            f"module 'mt5_safe' has no attribute {name!r} "
            f"(mt5linux_compat also has no such attribute)"
        )
    return getattr(target, name)


def __dir__() -> list[str]:
    """List available attributes (excluding blocked ones)."""
    return [
        name for name in dir(_real_mt5)
        if not name.startswith("_") and name not in _BLOCKED
    ] + [
        "safe_symbol_info_tick",
        "safe_symbol_info",
        "safe_symbols_get",
        "safe_copy_rates_from_pos",
        "safe_account_info",
        "check_mt5",
    ]


# ═══════════════════════════════════════════════════════════════
# Safe wrapper functions (return dicts, for MCP/orchestration)
# ═══════════════════════════════════════════════════════════════

def check_mt5() -> dict:
    """Check MT5 availability status."""
    return {
        "available": _MT5_AVAILABLE,
        "error": _MT5_INIT_ERROR if not _MT5_AVAILABLE else "",
        "import_error": _MT5_IMPORT_ERROR,
        "note": "Read-only functions only. Orders, login and eval are blocked.",
    }


def safe_symbol_info_tick(symbol: str) -> dict:
    """Get current tick data as a dict (safe)."""
    if not _MT5_AVAILABLE:
        return {"error": "MT5 not available"}
    try:
        tick = _real_mt5.symbol_info_tick(symbol)
        if tick is None:
            return {"error": f"Symbol '{symbol}' not found or no tick data"}
        return {
            "symbol": symbol,
            "bid": tick.bid,
            "ask": tick.ask,
            "last": tick.last,
            "volume": tick.volume,
            "time": str(tick.time),
            "spread": round(abs(tick.ask - tick.bid), 1) if tick.bid and tick.ask else 0,
        }
    except Exception as e:
        return {"error": str(e)}


def safe_symbol_info(symbol: str) -> dict:
    """Get symbol info as a dict (safe)."""
    if not _MT5_AVAILABLE:
        return {"error": "MT5 not available"}
    try:
        info = _real_mt5.symbol_info(symbol)
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
            "price_volatility": info.price_volatility,
        }
    except Exception as e:
        return {"error": str(e)}


def safe_symbols_get() -> dict:
    """Get all symbols as dict list (safe)."""
    if not _MT5_AVAILABLE:
        return {"error": "MT5 not available"}
    try:
        syms = _real_mt5.symbols_get()
        if syms is None:
            return {"symbols": [], "count": 0}
        result = [
            {"name": s.name, "description": s.description, "digits": s.digits}
            for s in syms
        ]
        return {"symbols": result, "count": len(result)}
    except Exception as e:
        return {"error": str(e)}


def safe_copy_rates_from_pos(
    symbol: str, timeframe: int, start_pos: int, count: int
) -> dict:
    """Copy historical rates as dict list (safe)."""
    if not _MT5_AVAILABLE:
        return {"error": "MT5 not available"}
    try:
        rates = _real_mt5.copy_rates_from_pos(symbol, timeframe, start_pos, count)
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
                "spread": r.spread,
            })
        return {"symbol": symbol, "timeframe": timeframe, "count": len(result), "rates": result}
    except Exception as e:
        return {"error": str(e)}


def safe_account_info() -> dict:
    """Get account info as a dict (safe, read-only)."""
    if not _MT5_AVAILABLE:
        return {"error": "MT5 not available"}
    try:
        info = _real_mt5.account_info()
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
            "limit_orders": info.limit_orders,
        }
    except Exception as e:
        return {"error": str(e)}


# ── Safe tools registry (for MCP dynamic dispatch) ─────────────
SAFE_TOOLS = {
    "symbol_info_tick": safe_symbol_info_tick,
    "symbol_info": safe_symbol_info,
    "symbols_get": safe_symbols_get,
    "copy_rates_from_pos": safe_copy_rates_from_pos,
    "account_info": safe_account_info,
}
