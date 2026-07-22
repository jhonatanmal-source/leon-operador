# ===================================
# SYSTEM WATCHDOG AGENT
# ===================================

import json
from datetime import datetime, timedelta
from pathlib import Path

from src.autonomy_guard import status_autonomia


ROOT_DIR = Path(__file__).resolve().parent.parent
LOGS_DIR = ROOT_DIR / "logs"
DATA_DIR = ROOT_DIR / "data"
OPERATOR_HEARTBEAT_FILE = DATA_DIR / "operator_heartbeat.json"


WATCH_FILES = [
    LOGS_DIR / "errors.txt",
    LOGS_DIR / "errors_fallback.txt",
    LOGS_DIR / "operator_runtime_error.log",
    LOGS_DIR / "panel_runtime_error.log",
]


CRITICAL_PATTERNS = [
    "Traceback",
    "MemoryError",
    "PermissionError",
    "UnicodeEncodeError",
    "OpenBLAS",
    "falha na analise",
    "TELEGRAM_CONNECTION_ERROR",
    "MT5_ORDER_EXCEPTION",
]


WARNING_PATTERNS = [
    "TELEGRAM | falha de conexao",
    "bloqueada por desvio",
    "RR real invalido",
    "INVALIDADA_GERENCIAMENTO",
    "status Telegram aguardando intervalo",
    "NO_CANDLE",
    "NO_TICK",
]


def _read_lines(path, limit=120):

    if not path.exists():
        return []

    try:
        lines = [
            line.strip().lstrip("\ufeff")
            for line in path.read_text(
                encoding="utf-8",
                errors="replace",
            ).splitlines()
            if line.strip().lstrip("\ufeff")
        ]
    except PermissionError as error:
        return [f"{datetime.now()} | WATCHDOG_PERMISSION_ERROR | {path}: {error}"]

    return lines[-limit:]


def _extract_datetime(line):

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


def _recent(line, hours):

    timestamp = _extract_datetime(line)

    if timestamp is None:
        return True

    return timestamp >= datetime.now() - timedelta(hours=hours)


def _classify(line):

    for pattern in CRITICAL_PATTERNS:
        if pattern.lower() in line.lower():
            return "CRITICO"

    for pattern in WARNING_PATTERNS:
        if pattern.lower() in line.lower():
            return "ATENCAO"

    return "INFO"


def _collect_events(hours=6):

    events = []
    cutoff = datetime.now() - timedelta(hours=hours)

    for path in WATCH_FILES:
        inherited_timestamp = None

        for line in _read_lines(path):
            timestamp = _extract_datetime(line)

            if timestamp is not None:
                inherited_timestamp = timestamp

            effective_timestamp = timestamp or inherited_timestamp

            if effective_timestamp is None:
                continue

            if effective_timestamp < cutoff:
                continue

            level = _classify(line)

            if level == "INFO":
                continue

            events.append(
                {
                    "level": level,
                    "source": path.name,
                    "message": line[-700:],
                    "timestamp": effective_timestamp.isoformat(),
                }
            )

    return events[-30:]


def _last_success(log_lines, marker):

    last = None

    for line in log_lines:
        if marker not in line:
            continue

        timestamp = _extract_datetime(line)

        if timestamp:
            last = timestamp

    return last


def _age_minutes(timestamp):

    if timestamp is None:
        return None

    return round((datetime.now() - timestamp).total_seconds() / 60, 1)


def _operator_heartbeat():

    if not OPERATOR_HEARTBEAT_FILE.exists():
        return {
            "status": "DESCONHECIDO",
            "updated_at": None,
            "age_minutes": None,
        }

    try:
        payload = json.loads(
            OPERATOR_HEARTBEAT_FILE.read_text(encoding="utf-8")
        )
        updated_at = datetime.fromisoformat(payload["updated_at"])
    except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError) as error:
        return {
            "status": "INVALIDO",
            "updated_at": None,
            "age_minutes": None,
            "error": str(error),
        }

    payload["age_minutes"] = _age_minutes(updated_at)
    return payload


def _status_from_events(events):

    if any(event["level"] == "CRITICO" for event in events):
        return "CRITICO"

    if any(event["level"] == "ATENCAO" for event in events):
        return "ATENCAO"

    return "OK"


def analisar_sistema():

    log_lines = _read_lines(LOGS_DIR / "leon_log.txt", limit=400)
    last_analysis = _last_success(log_lines, "OPERATOR | analise programada executada")
    last_collection = _last_success(log_lines, "OPERATOR | coleta programada executada")
    last_telegram = _last_success(log_lines, "OPERATOR | status Telegram enviado")
    events = _collect_events()
    heartbeat = _operator_heartbeat()
    autonomy = status_autonomia()

    if last_telegram:
        events = [
            event
            for event in events
            if not (
                "telegram" in event["message"].lower()
                and datetime.fromisoformat(event["timestamp"]) <= last_telegram
            )
        ]

    if last_analysis:
        resolved_sources = set()

        for path in WATCH_FILES:
            if not path.exists():
                continue

            modified_at = datetime.fromtimestamp(path.stat().st_mtime)

            if modified_at < last_analysis:
                resolved_sources.add(path.name)

        events = [
            event
            for event in events
            if event["source"] not in resolved_sources
        ]

    checks = {
        "analise_minutos": _age_minutes(last_analysis),
        "coleta_minutos": _age_minutes(last_collection),
        "telegram_minutos": _age_minutes(last_telegram),
        "operator_heartbeat_minutos": heartbeat.get("age_minutes"),
    }

    heartbeat_status = heartbeat.get("status")
    heartbeat_age = heartbeat.get("age_minutes")
    if heartbeat_status == "INVALIDO":
        events.append(
            {
                "level": "ATENCAO",
                "source": "watchdog",
                "message": "Heartbeat do operador esta invalido.",
            }
        )
    elif (
        heartbeat_status in {
            "ONLINE",
            "INICIANDO",
            "DEGRADADO",
            "OBSERVACAO",
            "PAUSA_MERCADO",
        }
        and (heartbeat_age is None or heartbeat_age > 3)
    ):
        events.append(
            {
                "level": "CRITICO",
                "source": "watchdog",
                "message": (
                    "Operador sem sinal de vida recente por mais de 3 minutos."
                ),
            }
        )
    elif heartbeat_status == "DEGRADADO":
        events.append(
            {
                "level": "ATENCAO",
                "source": "watchdog",
                "message": (
                    "Operador online, mas uma ou mais tarefas falharam "
                    "no ultimo ciclo."
                ),
            }
        )

    operator_expected_online = autonomy.get("active")
    operator_reports_online = heartbeat_status in {
        "ONLINE",
        "INICIANDO",
        "DEGRADADO",
        "OBSERVACAO",
        "PAUSA_MERCADO",
    }
    operator_can_produce_analysis = heartbeat_status in {
        "ONLINE",
        "INICIANDO",
        "DEGRADADO",
        "OBSERVACAO",
    }

    if operator_expected_online and not operator_reports_online:
        events.append(
            {
                "level": "CRITICO",
                "source": "watchdog",
                "message": (
                    "Autonomia ativa, mas o Operador Leon esta parado."
                ),
            }
        )
    elif not operator_expected_online and heartbeat_status == "ENCERRADO":
        events.append(
            {
                "level": "ATENCAO",
                "source": "watchdog",
                "message": (
                    "Operador encerrado com seguranca porque a autonomia terminou."
                ),
            }
        )

    if (
        operator_can_produce_analysis
        and (
            checks["analise_minutos"] is None
            or checks["analise_minutos"] > 45
        )
    ):
        events.append(
            {
                "level": "ATENCAO",
                "source": "watchdog",
                "message": "Analise automatica sem sucesso recente acima de 45 minutos.",
            }
        )

    if (
        operator_can_produce_analysis
        and (
            checks["coleta_minutos"] is None
            or checks["coleta_minutos"] > 45
        )
    ):
        events.append(
            {
                "level": "ATENCAO",
                "source": "watchdog",
                "message": "Coleta automatica sem sucesso recente acima de 45 minutos.",
            }
        )

    status = _status_from_events(events)

    return {
        "name": "Agente Watchdog",
        "status": status,
        "summary": _summary(status, events),
        "checks": checks,
        "operator_heartbeat": heartbeat,
        "autonomy": autonomy,
        "events": events[-12:],
        "telegram_notify": False,
        "updated_at": datetime.now().isoformat(timespec="seconds"),
    }


def _summary(status, events):

    if status == "OK":
        return "Nenhum erro critico recente detectado."

    critical = sum(1 for event in events if event["level"] == "CRITICO")
    warning = sum(1 for event in events if event["level"] == "ATENCAO")

    return f"{critical} critico(s), {warning} atencao(oes) no painel."
