import configparser
import csv
import json
import subprocess
import sys
import threading
import time
from datetime import datetime, timedelta
from pathlib import Path

# Ensure project root is in sys.path so mt5_safe can be imported
_APP_DIR = Path(__file__).resolve().parent.parent  # /opt/leon/app
if str(_APP_DIR) not in sys.path:
    sys.path.insert(0, str(_APP_DIR))

from web_app.config import BASE_DIR
from web_app.database.db import get_connection


SRC_DIR = BASE_DIR / "src"
DATA_DIR = BASE_DIR / "data"
LOGS_DIR = BASE_DIR / "logs"
ROOT_CONFIG_FILE = BASE_DIR / "config.ini"

# Cache for _mt5_status to avoid expensive MT5 initialize/shutdown on every health check
_mt5_cache = {"result": None, "timestamp": 0.0}
_MT5_CACHE_TTL = 30  # seconds
_mt5_cache_lock = threading.Lock()


def _ensure_src_path():
    if str(SRC_DIR) not in sys.path:
        sys.path.insert(0, str(SRC_DIR))


def _read_config():
    config = configparser.ConfigParser()
    config.read(ROOT_CONFIG_FILE, encoding="utf-8")
    return config


def _process_running(fragment):
    try:
        import psutil

        for proc in psutil.process_iter(["cmdline"]):
            try:
                cmdline = proc.info.get("cmdline")
                if cmdline and fragment in " ".join(cmdline):
                    return True
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        return False
    except ImportError:
        pass

    try:
        result = subprocess.run(
            ["pgrep", "-f", fragment],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=10,
        )
        return bool(result.stdout.strip())
    except (OSError, subprocess.SubprocessError):
        return False


def _read_last_csv(path):
    if not path.exists():
        return None
    with path.open("r", encoding="utf-8", errors="replace", newline="") as file:
        rows = list(csv.DictReader(file, delimiter=";"))
    return rows[-1] if rows else None


def _shadow_summary():
    path = DATA_DIR / "shadow_trades.csv"
    if not path.exists():
        return {"total": 0, "open": 0, "wins": 0, "losses": 0}
    with path.open("r", encoding="utf-8", errors="replace", newline="") as file:
        rows = list(csv.DictReader(file, delimiter=";"))
    return {
        "total": len(rows),
        "open": sum(row.get("status") == "ABERTO" for row in rows),
        "wins": sum(str(row.get("result", "")).startswith("WIN") for row in rows),
        "losses": sum(row.get("result") == "LOSS" for row in rows),
    }


def _shadow_trades_list():
    """Retorna lista detalhada de todas as shadow trades."""
    path = DATA_DIR / "shadow_trades.csv"
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8", errors="replace", newline="") as file:
        rows = list(csv.DictReader(file, delimiter=";"))
    trades = []
    for row in rows:
        trades.append({
            "id": row.get("id", "-"),
            "opened_at": row.get("opened_at", "-"),
            "closed_at": row.get("closed_at", "-") or "Em aberto",
            "symbol": row.get("symbol", "-"),
            "direction": row.get("direction", "-"),
            "entry": row.get("entry", "-"),
            "stop": row.get("stop", "-"),
            "target": row.get("target", "-"),
            "status": row.get("status", "-"),
            "result": row.get("result", "-"),
            "missing_confirmations": row.get("missing_confirmations", ""),
        })
    return trades


def _latest_entry_block():
    path = LOGS_DIR / "leon_log.txt"
    if not path.exists():
        return "Sem diagnóstico."
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    for line in reversed(lines[-800:]):
        marker = "OPERATOR | diagnostico de entrada:"
        if marker in line:
            return line.split(marker, 1)[1].strip()
    return "Sem bloqueio registrado."


def _tail_text(path, limit=2500):
    if not path.exists():
        return ""
    text = path.read_text(encoding="utf-8", errors="replace").strip()
    if len(text) <= limit:
        return text
    return text[-limit:]


def _extract_log_datetime(line):
    text = line.strip()
    if text.startswith("[") and "]" in text:
        text = text.split("]", 1)[0].lstrip("[")
    elif " | " in text:
        text = text.split(" | ", 1)[0]
    else:
        return None

    try:
        return datetime.fromisoformat(text)
    except ValueError:
        return None


def _last_success(marker):
    path = LOGS_DIR / "leon_log.txt"
    if not path.exists():
        return None

    last = None
    for line in path.read_text(
        encoding="utf-8",
        errors="replace",
    ).splitlines()[-1000:]:
        if marker not in line:
            continue
        timestamp = _extract_log_datetime(line)
        if timestamp:
            last = timestamp
    return last


def _active_errors(hours=6, limit=3500):
    path = LOGS_DIR / "errors.txt"
    if not path.exists():
        return "Sem erros ativos."

    last_analysis = _last_success("OPERATOR | analise programada executada")
    last_telegram = _last_success("OPERATOR | status Telegram enviado")
    cutoff = datetime.now() - timedelta(hours=hours)
    active = []
    inherited_timestamp = None

    for line in path.read_text(
        encoding="utf-8",
        errors="replace",
    ).splitlines():
        timestamp = _extract_log_datetime(line)
        if timestamp:
            inherited_timestamp = timestamp
        effective_timestamp = timestamp or inherited_timestamp
        if effective_timestamp is None or effective_timestamp < cutoff:
            continue
        if (
            last_analysis
            and effective_timestamp <= last_analysis
            and "falha na analise" in line.lower()
        ):
            continue
        if (
            last_telegram
            and effective_timestamp <= last_telegram
            and "telegram" in line.lower()
        ):
            continue
        active.append(line)

    if not active:
        return "Sem erros ativos. Historico preservado em logs/archive."

    return "\n".join(active)[-limit:]


def _recent_access_logs(page=1, per_page=20):
    per_page = max(1, min(per_page, 100))
    offset = (page - 1) * per_page
    with get_connection() as connection:
        total = connection.execute(
            "SELECT COUNT(*) as count FROM access_logs"
        ).fetchone()["count"]
        rows = connection.execute(
            """
            SELECT created_at, username, ip_address, route, action
            FROM access_logs
            ORDER BY id DESC
            LIMIT ? OFFSET ?
            """,
            (per_page, offset),
        ).fetchall()
    return {
        "rows": rows,
        "total": total,
        "page": page,
        "per_page": per_page,
        "total_pages": max(1, (total + per_page - 1) // per_page),
    }



def _study_state():
    path = DATA_DIR / "study_state.txt"
    if path.exists():
        return path.read_text(encoding="utf-8", errors="replace").strip()[:200]
    return None

def _demo_state():
    path = DATA_DIR / "demo_execution_state.txt"
    if path.exists():
        return path.read_text(encoding="utf-8", errors="replace").strip()[:200]
    return None

def _recent_demo_orders(limit=5):
    path = DATA_DIR / "mt5_order_memory.csv"
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8", errors="replace", newline="") as f:
        rows = list(csv.DictReader(f, delimiter=";"))
    return rows[-limit:]

def _simulated_summary():
    path = DATA_DIR / "simulated_entries.csv"
    if not path.exists():
        return {"total": 0, "wins": 0, "losses": 0}
    with path.open("r", encoding="utf-8", errors="replace", newline="") as f:
        rows = list(csv.DictReader(f, delimiter=";"))
    return {
        "total": len(rows),
        "wins": sum(1 for r in rows if str(r.get("resultado", "")).startswith("WIN")),
        "losses": sum(1 for r in rows if r.get("resultado") == "LOSS"),
    }

def _performance_summary():
    path = DATA_DIR / "performance.csv"
    if not path.exists():
        return {"total": 0, "wins": 0, "losses": 0}
    with path.open("r", encoding="utf-8", errors="replace", newline="") as f:
        rows = list(csv.DictReader(f, delimiter=";"))
    return {
        "total": len(rows),
        "wins": sum(1 for r in rows if str(r.get("resultado", "")).startswith("WIN")),
        "losses": sum(1 for r in rows if r.get("resultado") == "LOSS"),
    }



def _mt5_status():
    # Try cache first — avoid expensive MT5 initialize/shutdown on every call
    with _mt5_cache_lock:
        if _mt5_cache["result"] is not None and (
            time.monotonic() - _mt5_cache["timestamp"]
        ) < _MT5_CACHE_TTL:
            return _mt5_cache["result"]

    # Cache miss — compute fresh status (may involve MT5 init/shutdown)
    try:
        import mt5_safe as mt5
    except ImportError:
        result = {
            "status": "INDISPONÍVEL",
            "connected": False,
            "trade_allowed": False,
            "account_mode": "SEM MÓDULO",
        }
        with _mt5_cache_lock:
            _mt5_cache["result"] = result
            _mt5_cache["timestamp"] = time.monotonic()
        return result

    if not mt5.initialize():
        result = {
            "status": "ERRO",
            "connected": False,
            "trade_allowed": False,
            "account_mode": "DESCONHECIDO",
        }
        with _mt5_cache_lock:
            _mt5_cache["result"] = result
            _mt5_cache["timestamp"] = time.monotonic()
        return result

    try:
        account = mt5.account_info()
        terminal = mt5.terminal_info()
        if account is None or terminal is None:
            result = {
                "status": "ERRO",
                "connected": False,
                "trade_allowed": False,
                "account_mode": "DESCONHECIDO",
            }
        else:
            demo_mode = account.trade_mode == mt5.ACCOUNT_TRADE_MODE_DEMO
            connected = bool(terminal.connected)
            trade_allowed = bool(
                terminal.trade_allowed and not terminal.tradeapi_disabled
            )
            result = {
                "status": "OK" if connected and trade_allowed and demo_mode else "ATENÇÃO",
                "connected": connected,
                "trade_allowed": trade_allowed,
                "account_mode": "DEMO" if demo_mode else "NÃO DEMO",
                "balance": round(float(account.balance), 2),
                "equity": round(float(account.equity), 2),
                "open_profit": round(float(account.profit), 2),
            }
    finally:
        mt5.shutdown()

    # Store in cache for subsequent requests (TTL = 30s)
    with _mt5_cache_lock:
        _mt5_cache["result"] = result
        _mt5_cache["timestamp"] = time.monotonic()

    return result


def _remote_status():
    log_path = LOGS_DIR / "cloudflared_runtime_error.log"
    remote_url = None
    if log_path.exists():
        for line in reversed(
            log_path.read_text(encoding="utf-8", errors="replace").splitlines()
        ):
            if "https://" in line and ".trycloudflare.com" in line:
                start = line.find("https://")
                end = line.find(" ", start)
                remote_url = line[start:] if end == -1 else line[start:end]
                break
    return {
        "web_running": _process_running("web_app\\app.py"),
        "tunnel_running": _process_running("cloudflared.exe"),
        "legacy_panel_running": _process_running("src\\leon_panel.py"),
        "operator_running": _process_running("src\\leon_operator.py"),
        "remote_url": remote_url,
    }


def build_system_health():
    _ensure_src_path()

    from news_shield import avaliar_news_shield
    from operation_readiness import avaliar_prontidao_operacional
    from operator_status import obter_status_operadores
    from pre_operation_engine import resumo_pre_operacao
    from risk_control_agent import avaliar_limite_perda_diaria, resumo_risco
    from system_watchdog_agent import analisar_sistema

    operators = obter_status_operadores()
    sanitized_operators = {
        key: value
        for key, value in operators["operators"].items()
        if key != "telegram"
    }
    readiness = avaliar_prontidao_operacional()
    watchdog = analisar_sistema()
    pre_operations = resumo_pre_operacao()
    risk = resumo_risco()
    daily_loss = avaliar_limite_perda_diaria()
    news = avaliar_news_shield()
    mt5 = _mt5_status()
    remote = _remote_status()
    last_context = _read_last_csv(DATA_DIR / "market_context_memory.csv")
    shadow = _shadow_summary()

    overall = "OK"
    if watchdog.get("status") == "CRITICO" or mt5["status"] == "ERRO":
        overall = "CRÍTICO"
    elif (
        watchdog.get("status") == "ATENCAO"
        or operators["operators"]["collector"].get("status") != "OK"
        or mt5["status"] != "OK"
    ):
        overall = "ATENÇÃO"

    return {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "overall": overall,
        "processes": {
            "operator": remote["operator_running"],
            "legacy_panel": remote["legacy_panel_running"],
            "web_collab": remote["web_running"],
            "cloudflare_tunnel": remote["tunnel_running"],
        },
        "remote": remote,
        "mt5": mt5,
        "operators": sanitized_operators,
        "readiness": readiness,
        "watchdog": watchdog,
        "pre_operations": pre_operations,
        "shadow": shadow,
        "risk": risk,
        "daily_loss": daily_loss,
        "news": news,
        "last_context": last_context or {},
        "entry_block": _latest_entry_block(),
    }


def build_leon_panel_context(access_logs_page=1, access_logs_per_page=20):
    _ensure_src_path()

    from autonomy_guard import status_autonomia
    from market_context_agent import revisar_contextos
    from mt5_monitor import get_mt5_monitor_status
    from operation_batch_review import latest_batch_status
    from operator_council import avaliar_conselho_operadores
    from operator_status import obter_status_operadores
    from pre_operation_engine import resumo_pre_operacao
    from risk_control_agent import calcular_plano_risco, resumo_risco
    from risk_method_engine import desempenho_por_metodo
    from top_down_agent import ultima_leitura_top_down

    health = build_system_health()
    config = _read_config()
    pre_operation = resumo_pre_operacao()
    latest_pre_operation = pre_operation.get("ultimo") or {}
    risk_plan = None
    if latest_pre_operation.get("status") == "ABERTO":
        risk_plan = calcular_plano_risco(latest_pre_operation)

    return {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "autonomy": status_autonomia(),
        "operator_status": obter_status_operadores(),
        "pre_operation": pre_operation,
        "readiness": health["readiness"],
        "council": avaliar_conselho_operadores(),
        "risk_control": resumo_risco(),
        "risk_plan": risk_plan,
        "risk_methods": desempenho_por_metodo(),
        "top_down": ultima_leitura_top_down(),
        "market_context": revisar_contextos(),
        "mt5_monitor": get_mt5_monitor_status(),
        "watchdog": health["watchdog"],
        "batch_learning": latest_batch_status(),
        "telegram": {
            "enabled": config.get("TELEGRAM", "enabled", fallback="false"),
            "has_token": bool(config.get("TELEGRAM", "token", fallback="").strip()),
            "has_chat_id": bool(config.get("TELEGRAM", "chat_id", fallback="").strip()),
        },
        "mode": {
            "study_scope": config.get("AUTONOMY", "scope", fallback="learning_only"),
            "demo_execution": config.get(
                "OPERATOR",
                "demo_execution_enabled",
                fallback="false",
            ),
            "real_blocked": config.get("EXECUTION", "demo_only", fallback="true"),
            "mt5_enabled": config.get("MT5", "enabled", fallback="false"),
        },
        "collaboration": {
            "enabled": config.get("COLLABORATION", "enabled", fallback="false"),
            "scope": config.get("COLLABORATION", "scope", fallback="study_only"),
        },
        "daily_learning_state": _tail_text(DATA_DIR / "daily_learning_state.txt", 120),
        "daily_learning_report": _tail_text(
            BASE_DIR / "reports" / "daily_learning_report.txt",
            4000,
        ),
        "logs": _tail_text(LOGS_DIR / "leon_log.txt", 3500),
        "errors": _active_errors(),
        "remote": health["remote"],
        "processes": health["processes"],
        "system_health": health,
        "shadow": _shadow_summary(),
        "shadow_trades": _shadow_trades_list(),
        "recent_access_logs": _recent_access_logs(access_logs_page, access_logs_per_page),
        "study": _study_state(),
        "demo": _demo_state(),
        "recent_orders": _recent_demo_orders(),
        "simulated": _simulated_summary(),
        "performance": _performance_summary(),
    }
