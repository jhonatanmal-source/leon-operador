import csv
import hashlib
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parent.parent
ORDER_MEMORY_FILE = ROOT_DIR / "data" / "mt5_order_memory.csv"


def _masked_login(login):
    text = str(login or "")
    if len(text) <= 4:
        return "****"
    return f"{'*' * (len(text) - 4)}{text[-4:]}"


def _account_fingerprint(account):
    if account is None:
        return "SEM_CONTA"
    identity = f"{account.login}|{account.server}|{account.trade_mode}"
    return hashlib.sha256(identity.encode("utf-8")).hexdigest()[:16]


def _position_type(mt5, value):
    if value == mt5.POSITION_TYPE_BUY:
        return "COMPRA"
    if value == mt5.POSITION_TYPE_SELL:
        return "VENDA"
    return str(value)


def _recent_leon_orders(limit=5):
    if not ORDER_MEMORY_FILE.exists():
        return []

    with ORDER_MEMORY_FILE.open("r", encoding="utf-8", newline="") as file:
        rows = list(csv.DictReader(file, delimiter=";"))

    return [
        {
            "data": row.get("data"),
            "pre_operation_id": row.get("pre_operation_id"),
            "direction": row.get("direcao"),
            "lot": row.get("lote"),
            "entry": row.get("entrada"),
            "stop": row.get("stop"),
            "target": row.get("tp"),
            "status": row.get("status"),
            "ticket": row.get("ticket"),
        }
        for row in rows[-limit:]
    ]


def get_mt5_monitor_status(symbol="XAUUSD"):
    try:
        import mt5linux_compat as mt5
    except ImportError:
        return {
            "connected": False,
            "error": "MT5_IMPORT_ERROR",
            "positions": [],
            "recent_orders": _recent_leon_orders(),
        }

    if not mt5.initialize():
        return {
            "connected": False,
            "error": "MT5_INITIALIZE_FAILED",
            "details": str(mt5.last_error()),
            "positions": [],
            "recent_orders": _recent_leon_orders(),
        }

    try:
        account = mt5.account_info()
        terminal = mt5.terminal_info()
        tick = mt5.symbol_info_tick(symbol)
        positions = mt5.positions_get(symbol=symbol) or []

        position_rows = [
            {
                "ticket": position.ticket,
                "direction": _position_type(mt5, position.type),
                "volume": position.volume,
                "entry": round(float(position.price_open), 2),
                "current": round(float(position.price_current), 2),
                "stop": round(float(position.sl), 2),
                "target": round(float(position.tp), 2),
                "profit": round(float(position.profit), 2),
                "comment": position.comment,
            }
            for position in positions
        ]

        return {
            "connected": bool(terminal and terminal.connected),
            "trade_allowed": bool(terminal and terminal.trade_allowed),
            "account": {
                "login": _masked_login(account.login) if account else "SEM CONTA",
                "fingerprint": _account_fingerprint(account),
                "server": account.server if account else "SEM DADOS",
                "mode": (
                    "DEMO"
                    if account
                    and account.trade_mode == mt5.ACCOUNT_TRADE_MODE_DEMO
                    else "REAL/OUTRO"
                ),
                "currency": account.currency if account else "SEM DADOS",
                "balance": round(float(account.balance), 2) if account else None,
                "equity": round(float(account.equity), 2) if account else None,
                "profit": round(float(account.profit), 2) if account else None,
                "margin_free": (
                    round(float(account.margin_free), 2) if account else None
                ),
            },
            "market": {
                "symbol": symbol,
                "bid": round(float(tick.bid), 2) if tick else None,
                "ask": round(float(tick.ask), 2) if tick else None,
                "spread": (
                    round(float(tick.ask - tick.bid), 2) if tick else None
                ),
            },
            "positions": position_rows,
            "position_count": len(position_rows),
            "open_profit": round(
                sum(position["profit"] for position in position_rows),
                2,
            ),
            "recent_orders": _recent_leon_orders(),
        }
    except Exception as error:
        return {
            "connected": False,
            "error": "MT5_MONITOR_FAILED",
            "details": str(error),
            "positions": [],
            "recent_orders": _recent_leon_orders(),
        }
    finally:
        mt5.shutdown()
