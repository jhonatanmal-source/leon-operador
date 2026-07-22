import json
import time
from datetime import datetime, timezone
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parent.parent
STATE_FILE = ROOT_DIR / "data" / "market_session_state.json"


def _utc_now():
    return datetime.now(timezone.utc)


def _read_state(path=STATE_FILE):
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        return {}


def _write_state(payload, path=STATE_FILE):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_text(
        json.dumps(payload, indent=2, ensure_ascii=True),
        encoding="utf-8",
    )
    temporary.replace(path)


def inspect_broker_session(
    symbol="XAUUSD",
    stale_tick_seconds=180,
    now=None,
    mt5_module=None,
):
    now = now or _utc_now()

    try:
        if mt5_module is None:
            import mt5linux_compat as mt5_module
    except ImportError as error:
        return {
            "open": False,
            "status": "MT5_UNAVAILABLE",
            "reason": str(error),
            "checked_at": now.isoformat(),
            "symbol": symbol,
        }

    if not mt5_module.initialize():
        return {
            "open": False,
            "status": "MT5_DISCONNECTED",
            "reason": str(mt5_module.last_error()),
            "checked_at": now.isoformat(),
            "symbol": symbol,
        }

    try:
        terminal = mt5_module.terminal_info()
        account = mt5_module.account_info()
        mt5_module.symbol_select(symbol, True)
        symbol_info = mt5_module.symbol_info(symbol)
        tick = mt5_module.symbol_info_tick(symbol)

        if terminal is None or not terminal.connected:
            status = "MT5_DISCONNECTED"
            reason = "Terminal MT5 sem conexao com a corretora."
            tick_age = None
        elif symbol_info is None:
            status = "SYMBOL_UNAVAILABLE"
            reason = f"Simbolo {symbol} indisponivel na corretora."
            tick_age = None
        elif symbol_info.trade_mode == mt5_module.SYMBOL_TRADE_MODE_DISABLED:
            status = "BROKER_SYMBOL_DISABLED"
            reason = f"Negociacao de {symbol} desabilitada pela corretora."
            tick_age = None
        elif tick is None or not getattr(tick, "time", 0):
            status = "NO_BROKER_TICK"
            reason = "Corretora ainda nao forneceu tick para o simbolo."
            tick_age = None
        else:
            tick_age = max(0, int(now.timestamp() - tick.time))
            if tick_age > stale_tick_seconds:
                weekend = now.astimezone().weekday() >= 5
                status = "WEEKEND_CLOSED" if weekend else "DAILY_MARKET_PAUSE"
                reason = (
                    "Mercado fechado no fim de semana conforme a corretora."
                    if weekend
                    else "Pausa diaria ou fechamento temporario da corretora."
                )
            elif account is None or not account.trade_allowed:
                status = "BROKER_TRADING_BLOCKED"
                reason = "Conta conectada, mas a corretora bloqueou negociacao."
            else:
                status = "MARKET_OPEN"
                reason = "Tick recente e negociacao liberada pela corretora."

        return {
            "open": status == "MARKET_OPEN",
            "status": status,
            "reason": reason,
            "checked_at": now.isoformat(),
            "symbol": symbol,
            "broker": getattr(account, "server", None),
            "tick_age_seconds": tick_age,
            "last_tick_at": (
                datetime.fromtimestamp(tick.time, timezone.utc).isoformat()
                if tick is not None and getattr(tick, "time", 0)
                else None
            ),
        }
    finally:
        mt5_module.shutdown()


def register_session_status(session, path=STATE_FILE):
    previous = _read_state(path)
    now_text = session["checked_at"]
    changed = previous.get("status") != session["status"]

    payload = dict(session)
    payload["status_changed"] = changed
    payload["previous_status"] = previous.get("status")
    payload["closed_since"] = previous.get("closed_since")
    payload["maintenance_done"] = previous.get("maintenance_done", False)

    if session["open"]:
        payload["opened_at"] = (
            now_text if not previous.get("open") else previous.get("opened_at")
        )
        payload["closed_since"] = None
        payload["maintenance_done"] = False
    else:
        payload["opened_at"] = previous.get("opened_at")
        if previous.get("open") or not previous.get("closed_since"):
            payload["closed_since"] = now_text
            payload["maintenance_done"] = False

    _write_state(payload, path)
    return payload


def maintenance_is_due(session_state, delay_seconds=120, now=None):
    if session_state.get("open") or session_state.get("maintenance_done"):
        return False
    closed_since = session_state.get("closed_since")
    if not closed_since:
        return False
    try:
        closed_at = datetime.fromisoformat(closed_since)
    except ValueError:
        return False
    now = now or _utc_now()
    return (now - closed_at).total_seconds() >= delay_seconds


def restart_mt5_connection(
    symbol="XAUUSD",
    attempts=3,
    wait_seconds=2,
    mt5_module=None,
):
    try:
        if mt5_module is None:
            import mt5linux_compat as mt5_module
    except ImportError as error:
        return {"ok": False, "error": "MT5_IMPORT_ERROR", "details": str(error)}

    last_error = None
    for _ in range(max(1, attempts)):
        mt5_module.shutdown()
        time.sleep(max(0, wait_seconds))
        if mt5_module.initialize():
            mt5_module.symbol_select(symbol, True)
            terminal = mt5_module.terminal_info()
            connected = terminal is not None and terminal.connected
            mt5_module.shutdown()
            if connected:
                return {"ok": True, "symbol": symbol}
        last_error = mt5_module.last_error()

    mt5_module.shutdown()
    return {
        "ok": False,
        "error": "MT5_RESTART_FAILED",
        "details": str(last_error),
    }


def mark_maintenance_done(result, path=STATE_FILE):
    state = _read_state(path)
    state["maintenance_done"] = True
    state["maintenance_at"] = _utc_now().isoformat()
    state["maintenance_result"] = result
    _write_state(state, path)
    return state
