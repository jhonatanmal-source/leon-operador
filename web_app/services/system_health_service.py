import configparser
import configparser
import csv
import json
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path

from web_app.config import BASE_DIR
from web_app.database.db import get_connection


SRC_DIR = BASE_DIR / "src"
DATA_DIR = BASE_DIR / "data"
LOGS_DIR = BASE_DIR / "logs"
ROOT_CONFIG_FILE = BASE_DIR / "config.ini"


def _ensure_src_path():
    if str(SRC_DIR) not in sys.path:
        sys.path.insert(0, str(SRC_DIR))


def _read_config():
    config = configparser.ConfigParser()
    config.read(ROOT_CONFIG_FILE, encoding="utf-8")
    return config


def _process_running(fragment):
    try:
        result = subprocess.run(
            [
                "powershell",
                "-NoProfile",
                "-Command",
                (
                    "Get-CimInstance Win32_Process | "
                    f"Where-Object {{ $_.CommandLine -like '*{fragment}*' }} | "
                    "Select-Object -First 1 -ExpandProperty ProcessId"
                ),
            ],
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


def _recent_access_logs(limit=12):
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT created_at, username, ip_address, route, action
            FROM access_logs
            ORDER BY id DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    return rows


def _mt5_status():
    try:
        import mt5linux_compat as mt5
    except ImportError:
        return {
            "status": "INDISPONÍVEL",
            "connected": False,
            "trade_allowed": False,
            "account_mode": "SEM MÓDULO",
        }

    if not mt5.initialize():
        return {
            "status": "ERRO",
            "connected": False,
            "trade_allowed": False,
            "account_mode": "DESCONHECIDO",
        }

    try:
        account = mt5.account_info()
        terminal = mt5.terminal_info()
        if account is None or terminal is None:
            return {
                "status": "ERRO",
                "connected": False,
                "trade_allowed": False,
                "account_mode": "DESCONHECIDO",
            }
        demo_mode = account.trade_mode == mt5.ACCOUNT_TRADE_MODE_DEMO
        connected = bool(terminal.connected)
        trade_allowed = bool(
            terminal.trade_allowed and not terminal.tradeapi_disabled
        )
        return {
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


def build_leon_panel_context():
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
        "recent_access_logs": _recent_access_logs(),
    }
