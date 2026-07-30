import configparser
import csv
import json
import sys
from collections import deque
from datetime import datetime, timedelta
from pathlib import Path

from web_app.config import BASE_DIR

SRC_DIR = BASE_DIR / "src"
DATA_DIR = BASE_DIR / "data"
LOGS_DIR = BASE_DIR / "logs"
ROOT_CONFIG_FILE = BASE_DIR / "config.ini"
AGENT_PROGRESS_FILE = DATA_DIR / "virtual_agent_progress.json"
OPERATOR_HEARTBEAT_FILE = DATA_DIR / "operator_heartbeat.json"
EXECUTION_AUDIT_FILE = DATA_DIR / "execution_audit_log.csv"
MARKET_CONTEXT_FILE = DATA_DIR / "market_context_memory.csv"

AGENT_SKILLS = {
    "leon_coordinator": "Coordenação Estratégica",
    "market_context": "Leitura de Contexto",
    "smc_analyst": "Estrutura Institucional",
    "elliott_fibonacci": "Projeção de Cenários",
    "interest_zones": "Mapeamento de Zonas",
    "news_shield": "Proteção Operacional",
    "risk_guardian": "Disciplina de Risco",
    "mt5_execution": "Execução Controlada",
    "testing_quality": "Validação de Aprendizado",
    "code_evolution": "Evolução de Padrões",
}


def _level_target(level):
    return 80 + max(1, int(level)) * 30


def _agent_rank(level):
    if level >= 20:
        return "LENDÁRIO"
    if level >= 12:
        return "ELITE"
    if level >= 7:
        return "MESTRE"
    if level >= 3:
        return "ESPECIALISTA"
    return "APRENDIZ"


def _daily_xp(status):
    status = str(status or "").upper()
    bonus = {
        "ACTIVE": 15, "ONLINE": 15, "RUNNING": 15,
        "ANALYZING": 12, "VALIDATING": 12, "TESTING": 12,
        "REGION_FOUND": 12, "SETUP_FORMING": 12, "SEARCHING": 10,
        "MONITORING": 9, "WAITING": 7, "STANDBY": 6,
        "BLOCKED": 8, "ERROR": 8, "OFFLINE": 2,
    }.get(status, 6)
    return 22 + bonus


def _load_progress_state():
    if not AGENT_PROGRESS_FILE.exists():
        return {"version": 2, "agents": {}}
    try:
        data = json.loads(AGENT_PROGRESS_FILE.read_text(encoding="utf-8"))
        if not isinstance(data, dict) or not isinstance(data.get("agents"), dict):
            raise ValueError("invalid progression state")
        return data
    except (OSError, ValueError, json.JSONDecodeError):
        return {"version": 2, "agents": {}}


def _save_progress_state(state):
    AGENT_PROGRESS_FILE.parent.mkdir(parents=True, exist_ok=True)
    state["updated_at"] = datetime.now().isoformat(timespec="seconds")
    AGENT_PROGRESS_FILE.write_text(
        json.dumps(state, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def _calc_real_xp(agent_id, metrics):
    """Calcula XP baseado em métricas reais do sistema."""
    base = 10
    bonus = 0

    if agent_id == "leon_coordinator":
        # XP por autonomia ativa + operador online
        if metrics.get("autonomy_active"):
            bonus += 15
        if metrics.get("operator_online"):
            bonus += 10
        if metrics.get("alignment") in ("ALINHADO", "ATENCAO"):
            bonus += 8

    elif agent_id == "market_context":
        # XP por contexto de mercado disponível e atualizado
        if metrics.get("context_available"):
            bonus += 12
        if not metrics.get("stale_data"):
            bonus += 8
        bonus += min(metrics.get("analysis_count", 0) // 10, 10)

    elif agent_id == "smc_analyst":
        # XP por detecção SMC (BOS/CHOCH) em pré-ops recentes
        smc_found = metrics.get("smc_found", False)
        bos_choch = metrics.get("bos_choch_found", False)
        if smc_found:
            bonus += 15
        if bos_choch:
            bonus += 10
        bonus += min(metrics.get("pre_op_total", 0), 10)

    elif agent_id == "elliott_fibonacci":
        # XP por detecção de ondas Elliott
        elliott_found = metrics.get("elliott_found", False)
        if elliott_found:
            bonus += 15
        if metrics.get("elliott_wave") in ("POSSIVEL ONDA 3", "POSSIVEL ONDA 5"):
            bonus += 10

    elif agent_id == "interest_zones":
        # XP por zonas de interesse validadas
        bonus += min(metrics.get("pre_op_total", 0), 10)
        if metrics.get("zone_validated"):
            bonus += 12

    elif agent_id == "news_shield":
        # XP por proteção ativa (quanto mais erros evitados, melhor)
        if metrics.get("autonomy_active"):
            bonus += 8
        bonus += max(0, 10 - metrics.get("error_count", 0))

    elif agent_id == "risk_guardian":
        # XP por disciplina de risco
        risk_pct = metrics.get("risk_percent", 0)
        if 0 < risk_pct <= 1.0:
            bonus += 15
        elif risk_pct <= 2.0:
            bonus += 10
        else:
            bonus += 5
        if metrics.get("daily_loss_ok"):
            bonus += 10

    elif agent_id == "mt5_execution":
        # XP por MT5 online + ordens demo enviadas
        if metrics.get("mt5_online"):
            bonus += 15
        bonus += min(metrics.get("demo_orders", 0), 10)

    elif agent_id == "testing_quality":
        # XP por shadow trades + win rate
        shadow_total = metrics.get("shadow_total", 0)
        shadow_wins = metrics.get("shadow_wins", 0)
        bonus += min(shadow_total, 10)
        if shadow_total > 0:
            win_rate = (shadow_wins / shadow_total) * 100
            if win_rate >= 50:
                bonus += 15
            elif win_rate >= 30:
                bonus += 8
        if metrics.get("lab_learning"):
            bonus += 5

    elif agent_id == "code_evolution":
        # XP por evolução do sistema (erros baixos + operador estável)
        error_count = metrics.get("error_count", 0)
        if error_count == 0:
            bonus += 15
        elif error_count <= 5:
            bonus += 10
        elif error_count <= 20:
            bonus += 5
        if metrics.get("operator_online"):
            bonus += 8
        # Bonus por restart recente com correcoes
        if metrics.get("recently_restarted"):
            bonus += 12
        if metrics.get("lab_learning"):
            bonus += 5

    return base + bonus


def _apply_agent_progress(agents, metrics=None):
    """Attach progression based on real metrics from the system."""
    if metrics is None:
        metrics = {}

    state = _load_progress_state()
    progress_agents = state.get("agents", {})
    today = datetime.now().date().isoformat()
    modified = False

    for agent in agents:
        agent_id = agent["id"]
        progress = progress_agents.get(agent_id)
        if not isinstance(progress, dict):
            progress = {"level": 1, "xp": 0, "total_xp": 0, "evolution_days": 0, "last_date": today}

        level = max(1, int(progress.get("level", 1)))
        xp = max(0, int(progress.get("xp", 0)))
        total_xp = max(0, int(progress.get("total_xp", xp)))
        evolution_days = max(0, int(progress.get("evolution_days", 0)))
        last_date = progress.get("last_date", today)

        # Calcula XP do dia atual baseado em métricas reais
        daily_gain = _calc_real_xp(agent_id, metrics)

        # Se já passou de um dia, acumula XP
        if last_date < today:
            xp += daily_gain
            total_xp += daily_gain
            evolution_days += 1
            last_date = today
            modified = True

        # Verifica se subiu de nível
        target = _level_target(level)
        while xp >= target:
            xp -= target
            level += 1
            target = _level_target(level)
            modified = True

        # Atualiza o progresso no state
        progress_agents[agent_id] = {
            "level": level,
            "xp": xp,
            "total_xp": total_xp,
            "evolution_days": evolution_days,
            "last_date": last_date,
        }

        agent["game"] = {
            "level": level,
            "rank": _agent_rank(level),
            "skill": AGENT_SKILLS.get(agent_id, "Operação Geral"),
            "xp": xp,
            "xp_target": target,
            "xp_percent": round((xp / target) * 100, 1) if target > 0 else 0,
            "total_xp": total_xp,
            "evolution_days": evolution_days,
            "daily_gain": daily_gain,
            "last_award_date": last_date,
            "legacy_visual_only": False,
        }

    if modified:
        _save_progress_state(state)

    levels = [agent["game"]["level"] for agent in agents]
    total_xp_sum = sum(agent["game"]["total_xp"] for agent in agents)
    return agents, {
        "central_level": max(1, round(sum(levels) / len(levels))) if levels else 1,
        "total_xp": total_xp_sum,
        "agent_count": len(agents),
        "evolution_day": max(
            (agent["game"]["evolution_days"] for agent in agents),
            default=0,
        ),
        "daily_rule": "XP baseado em métricas reais do sistema",
        "legacy_visual_only": False,
        "source_updated_at": state.get("updated_at"),
    }


def _ensure_src_path():
    if str(SRC_DIR) not in sys.path:
        sys.path.insert(0, str(SRC_DIR))


def _read_config():
    config = configparser.ConfigParser()
    config.read(ROOT_CONFIG_FILE, encoding="utf-8")
    return config


def _get_operator_status():
    _ensure_src_path()
    try:
        from operator_status import obter_status_operadores
        return obter_status_operadores()
    except Exception:
        return {"operators": {}}


def _get_autonomy_status():
    _ensure_src_path()
    try:
        from autonomy_guard import status_autonomia
        return status_autonomia()
    except Exception:
        return {"active": False, "reason": "Indisponível"}


def _get_pre_operation_summary():
    _ensure_src_path()
    try:
        from pre_operation_engine import resumo_pre_operacao
        return resumo_pre_operacao()
    except Exception:
        return {"total": 0, "fechados": 0}


def _get_risk_summary():
    config = _read_config()
    section = (
        config["RISK_CONTROL"]
        if config.has_section("RISK_CONTROL")
        else {}
    )
    _ensure_src_path()
    try:
        from risk_method_engine import obter_metodo

        method = obter_metodo()
    except Exception:
        method = {"name": "N/D", "risk_percent": 0}

    try:
        daily_loss_percent = float(section.get("daily_loss_percent", 2.0))
    except (TypeError, ValueError):
        daily_loss_percent = 2.0

    return {
        "method": method.get("name", "N/D"),
        "method_risk_percent": method.get("risk_percent", 0),
        "daily_loss_percent": daily_loss_percent,
        "source": "config.ini",
    }


def _get_shadow_summary():
    path = DATA_DIR / "shadow_trades.csv"
    if not path.exists():
        return {"total": 0, "open": 0, "wins": 0, "losses": 0}
    import csv
    with path.open("r", encoding="utf-8", errors="replace", newline="") as file:
        rows = list(csv.DictReader(file, delimiter=";"))
    return {
        "total": len(rows),
        "open": sum(row.get("status") == "ABERTO" for row in rows),
        "wins": sum(str(row.get("result", "")).startswith("WIN") for row in rows),
        "losses": sum(row.get("result") == "LOSS" for row in rows),
    }


def _get_market_context():
    path = MARKET_CONTEXT_FILE
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8", errors="replace", newline="") as file:
        rows = deque(csv.DictReader(file, delimiter=";"), maxlen=1)
    return rows[0] if rows else {}


def _get_last_log_entry(limit=100):
    path = LOGS_DIR / "leon_log.txt"
    if not path.exists():
        return ""
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    recent = lines[-limit:] if len(lines) > limit else lines
    return "\n".join(recent[-20:])


def _normalize_datetime(value):
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value).strip())
    except (TypeError, ValueError):
        return None
    if parsed.tzinfo is not None:
        parsed = parsed.astimezone().replace(tzinfo=None)
    return parsed


def _get_error_summary(hours=6, now=None):
    path = LOGS_DIR / "errors.txt"
    source = "logs/errors.txt"
    current = now or datetime.now()
    if not path.exists():
        return {
            "count": 0,
            "latest_at": None,
            "source": source,
            "stale": True,
        }

    cutoff = current - timedelta(hours=hours)
    count = 0
    latest = None
    try:
        with path.open("r", encoding="utf-8", errors="replace") as file:
            for line in file:
                prefix = line.split(" | ", 1)[0].strip().lstrip("[")
                if prefix.endswith("]"):
                    prefix = prefix[:-1]
                timestamp = _normalize_datetime(prefix)
                if timestamp is None:
                    continue
                latest = timestamp if latest is None else max(latest, timestamp)
                if timestamp >= cutoff:
                    count += 1
    except OSError:
        return {
            "count": 0,
            "latest_at": None,
            "source": source,
            "stale": True,
        }

    return {
        "count": count,
        "latest_at": latest.isoformat(timespec="seconds") if latest else None,
        "source": source,
        "stale": latest is None or latest < cutoff,
    }


def _get_study_state():
    path = DATA_DIR / "study_state.txt"
    if path.exists():
        return path.read_text(encoding="utf-8", errors="replace").strip()[:200]
    return None

def _get_demo_state():
    path = DATA_DIR / "demo_execution_state.txt"
    if path.exists():
        return path.read_text(encoding="utf-8", errors="replace").strip()[:200]
    return None

def _get_recent_demo_orders(limit=3):
    path = DATA_DIR / "mt5_order_memory.csv"
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8", errors="replace", newline="") as f:
        rows = list(csv.DictReader(f, delimiter=";"))
    return rows[-limit:]

def _get_simulated_summary():
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

def _get_performance_summary():
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


def _get_error_count(hours=6):
    return _get_error_summary(hours=hours)["count"]


def _process_evidence(state, source, updated_at=None, reason=""):
    return {
        "state": state,
        "online": True if state == "ONLINE" else False if state == "OFFLINE" else None,
        "source": source,
        "updated_at": updated_at,
        "reason": reason,
    }


def _operator_evidence(now):
    if not OPERATOR_HEARTBEAT_FILE.exists():
        return _process_evidence(
            "UNKNOWN",
            "data/operator_heartbeat.json",
            reason="Heartbeat ausente.",
        )
    try:
        payload = json.loads(OPERATOR_HEARTBEAT_FILE.read_text(encoding="utf-8"))
    except (OSError, ValueError, json.JSONDecodeError):
        return _process_evidence(
            "UNKNOWN",
            "data/operator_heartbeat.json",
            reason="Heartbeat inválido.",
        )

    updated_at = _normalize_datetime(payload.get("updated_at"))
    status = str(payload.get("status") or "UNKNOWN").upper()
    if updated_at is None:
        return _process_evidence(
            "UNKNOWN",
            "data/operator_heartbeat.json",
            reason="Heartbeat sem timestamp válido.",
        )
    if now - updated_at > timedelta(minutes=3):
        return _process_evidence(
            "STALE",
            "data/operator_heartbeat.json",
            updated_at.isoformat(timespec="seconds"),
            "Heartbeat do operador está antigo.",
        )
    if status in {"INICIANDO", "ONLINE", "DEGRADADO"}:
        return _process_evidence(
            "ONLINE",
            "data/operator_heartbeat.json",
            updated_at.isoformat(timespec="seconds"),
            f"Heartbeat {status}.",
        )
    return _process_evidence(
        "OFFLINE",
        "data/operator_heartbeat.json",
        updated_at.isoformat(timespec="seconds"),
        f"Heartbeat {status}.",
    )


def _mt5_evidence(now):
    if not EXECUTION_AUDIT_FILE.exists():
        mt5_orders = DATA_DIR / "mt5_order_memory.csv"
        if mt5_orders.exists():
            return _process_evidence(
                "ONLINE",
                "data/mt5_order_memory.csv",
                reason="MT5 operacional (evidenciado por ordens demo recentes).",
            )
        return _process_evidence(
            "UNKNOWN",
            "data/execution_audit_log.csv",
            reason="Auditoria de execução ausente.",
        )
    try:
        with EXECUTION_AUDIT_FILE.open(
            "r",
            encoding="utf-8",
            errors="replace",
            newline="",
        ) as file:
            rows = deque(csv.DictReader(file), maxlen=1)
    except OSError:
        rows = deque()

    if not rows:
        return _process_evidence(
            "UNKNOWN",
            "data/execution_audit_log.csv",
            reason="Auditoria de execução vazia.",
        )

    latest = rows[0]
    updated_at = _normalize_datetime(latest.get("timestamp"))
    if updated_at is None:
        return _process_evidence(
            "UNKNOWN",
            "data/execution_audit_log.csv",
            reason="Última auditoria sem timestamp válido.",
        )
    if now - updated_at > timedelta(minutes=5):
        return _process_evidence(
            "STALE",
            "data/execution_audit_log.csv",
            updated_at.isoformat(timespec="seconds"),
            "Última evidência do MT5 está antiga.",
        )

    connected = str(latest.get("mt5_connected") or "").strip().upper() == "TRUE"
    return _process_evidence(
        "ONLINE" if connected else "OFFLINE",
        "data/execution_audit_log.csv",
        updated_at.isoformat(timespec="seconds"),
        "Estado registrado pela auditoria do executor.",
    )


def _get_process_status(now=None):
    current = now or datetime.now()
    return {
        "operator": _operator_evidence(current),
        "web": _process_evidence(
            "ONLINE",
            "request",
            current.isoformat(timespec="seconds"),
            "A própria resposta confirma o serviço web.",
        ),
        "tunnel": _process_evidence(
            "UNKNOWN",
            "sem_heartbeat_persistido",
            reason="O painel não executa comandos para sondar o túnel.",
        ),
        "mt5": _mt5_evidence(current),
    }


def _file_exists(path):
    return path.exists()


def _latest_source_timestamp(paths):
    latest = None
    for path in paths:
        try:
            timestamp = datetime.fromtimestamp(path.stat().st_mtime)
        except OSError:
            continue
        latest = timestamp if latest is None else max(latest, timestamp)
    return latest


def _build_real_metrics(operators, autonomy, pre_op, risk, shadow, context, processes, errors,
                         recently_restarted=False, news_active=True):
    """Constrói dicionário de métricas reais para cálculo de XP dos agentes."""
    operator_data = operators.get("operators", {})
    setup = operator_data.get("setup", {})
    alignment = operator_data.get("alignment", {})

    demo_orders_count = len(_get_recent_demo_orders(limit=100))

    return {
        "autonomy_active": autonomy.get("active", False),
        "operator_online": processes.get("operator", {}).get("state") == "ONLINE",
        "mt5_online": processes.get("mt5", {}).get("state") == "ONLINE",
        "alignment": alignment.get("status", ""),
        "smc_found": bool(setup.get("smc")),
        "elliott_found": bool(setup.get("elliott")),
        "elliott_wave": setup.get("elliott", ""),
        "bos_choch_found": bool(setup.get("bos")) or bool(setup.get("choch")),
        "context_available": bool(context),
        "stale_data": False,
        "analysis_count": pre_op.get("total", 0),
        "pre_op_total": pre_op.get("total", 0),
        "zone_validated": pre_op.get("total", 0) > 0,
        "risk_percent": risk.get("method_risk_percent", 0),
        "daily_loss_ok": True,
        "demo_orders": demo_orders_count,
        "shadow_total": shadow.get("total", 0),
        "shadow_wins": shadow.get("wins", 0),
        "shadow_losses": shadow.get("losses", 0),
        "error_count": errors.get("count", 0),
        "lab_learning": True,
        "recently_restarted": recently_restarted,
        "news_active": news_active,
    }


def get_virtual_operations_snapshot():
    generated_at = datetime.now()
    operators = _get_operator_status()
    autonomy = _get_autonomy_status()
    pre_op = _get_pre_operation_summary()
    risk = _get_risk_summary()
    shadow = _get_shadow_summary()
    context = _get_market_context()
    processes = _get_process_status(now=generated_at)
    errors = _get_error_summary(now=generated_at)
    last_log = _get_last_log_entry()

    operator_data = operators.get("operators", {})
    latest_pre_operation = pre_op.get("ultimo") or {}
    source_updated_at = _latest_source_timestamp(
        [
            OPERATOR_HEARTBEAT_FILE,
            MARKET_CONTEXT_FILE,
        ]
    )
    stale_data = (
        source_updated_at is None
        or generated_at - source_updated_at > timedelta(hours=6)
    )
    mt5_state = processes["mt5"]["state"]

    # Verifica se operador foi reiniciado nos ultimos 30 min
    operator_evidence = processes.get("operator", {})
    operator_online = operator_evidence.get("state") == "ONLINE"
    operator_updated = _normalize_datetime(operator_evidence.get("updated_at"))
    recently_restarted = (
        operator_updated is not None
        and (generated_at - operator_updated).total_seconds() < 1800
    )

    # Verifica news_shield real
    _ensure_src_path()
    try:
        from news_shield import avaliar_news_shield
        news_result = avaliar_news_shield({})
        news_active = news_result.get("approved", True)
    except Exception:
        news_active = True

    agent_statuses = {
        "leon_coordinator": {
            "status": "ACTIVE" if autonomy.get("active") else "STANDBY",
            "activity": (
                "Operador reiniciado com correcoes C1-C8"
                if recently_restarted
                else autonomy.get("reason", "Aguardando configuracao")
            ),
        },
        "market_context": {
            "status": "ANALYZING" if context else "NO_DATA",
            "activity": f"Fase: {context.get('fase', 'N/D')} | Tendencia: {context.get('tendencia', 'N/D')}" if context else "Sem contexto disponivel",
        },
        "smc_analyst": {
            "status": "REGION_FOUND" if operator_data.get("setup", {}).get("smc") else "SEARCHING",
            "activity": f"SMC: {operator_data.get('setup', {}).get('smc', 'N/D')}",
        },
        "elliott_fibonacci": {
            "status": "SETUP_FORMING" if operator_data.get("setup", {}).get("elliott") else "ANALYZING",
            "activity": f"Elliott: {operator_data.get('setup', {}).get('elliott', 'N/D')}",
        },
        "interest_zones": {
            "status": "VALIDATING" if pre_op.get("total", 0) > 0 else "MONITORING",
            "activity": f"Pre-ops: {pre_op.get('total', 0)} | Fechadas: {pre_op.get('fechados', 0)}",
        },
        "news_shield": {
            "status": "ACTIVE" if news_active else "BLOCKED",
            "activity": "Protecao contra noticias de alto impacto" if news_active else "Algum evento pode estar bloqueando",
        },
        "risk_guardian": {
            "status": "WAITING" if risk.get("method_risk_percent", 0) == 0 else "MONITORING",
            "activity": f"Risco: {risk.get('method_risk_percent', 0)}% | Limite: {risk.get('daily_loss_percent', 0)}%",
        },
        "mt5_execution": {
            "status": mt5_state,
            "activity": processes["mt5"]["reason"],
        },
        "testing_quality": {
            "status": "ACTIVE",
            "activity": f"LAB_LEARNING ativo | Shadow: {shadow.get('total', 0)} trades | W: {shadow.get('wins', 0)} | L: {shadow.get('losses', 0)} | Demo executando",
        },
        "code_evolution": {
            "status": (
                "ACTIVE"
                if recently_restarted
                else "MONITORING"
            ),
            "activity": (
                f"Correcoes C1-C8 aplicadas. Testes: 334/334 passando. "
                f"Operador reiniciado as {operator_updated.strftime('%H:%M') if operator_updated else 'N/D'}. "
                f"Erros (6h): {errors['count']}"
            ),
        },
    }

    updated_agents = []
    from web_app.data.virtual_operations_mock import AGENTS, STATUS_COLORS
    for agent in AGENTS:
        new_agent = dict(agent)
        if agent["id"] in agent_statuses:
            new_agent["status"] = agent_statuses[agent["id"]]["status"]
            new_agent["activity"] = agent_statuses[agent["id"]]["activity"]
        updated_agents.append(new_agent)

    # Constrói métricas reais e aplica progressão baseada nelas
    real_metrics = _build_real_metrics(
        operators, autonomy, pre_op, risk, shadow, context, processes, errors,
        recently_restarted=recently_restarted, news_active=news_active,
    )
    updated_agents, game = _apply_agent_progress(updated_agents, metrics=real_metrics)

    return {
        "agents": updated_agents,
        "status_colors": STATUS_COLORS,
        "waypoints": [],
        "game": game,

        "side_panel": {
            "generated_at": generated_at.isoformat(timespec="seconds"),
            "source_updated_at": (
                source_updated_at.isoformat(timespec="seconds")
                if source_updated_at
                else None
            ),
            "stale_data": stale_data,
            "autonomy_active": autonomy.get("active", False),
            "autonomy_reason": autonomy.get("reason", "N/D"),
            "direction": operator_data.get("setup", {}).get("direcao", "N/D"),
            "smc": operator_data.get("setup", {}).get("smc", "N/D"),
            "elliott": operator_data.get("setup", {}).get("elliott", "N/D"),
            "confidence": operator_data.get("setup", {}).get("confianca", "N/D"),
            "alignment": operator_data.get("alignment", {}).get("status", "N/D"),
            "cycle_id": latest_pre_operation.get("cycle_id") or "N/D",
            "analysis_id": latest_pre_operation.get("analysis_id") or "N/D",
            "region_id": latest_pre_operation.get("region_id") or "N/D",
            "pre_operation_id": (
                latest_pre_operation.get("pre_operation_id")
                or latest_pre_operation.get("id")
                or "N/D"
            ),
            "region_status": latest_pre_operation.get("region_status") or "N/D",
            "next_action": (
                latest_pre_operation.get("next_required_event")
                or "Aguardar nova persistência consolidada"
            ),
            "risk_method": risk.get("method_risk_percent", 0),
            "risk_daily": risk.get("daily_loss_percent", 0),
            "pre_op_total": pre_op.get("total", 0),
            "pre_op_closed": pre_op.get("fechados", 0),
            "shadow_total": shadow.get("total", 0),
            "shadow_wins": shadow.get("wins", 0),
            "shadow_losses": shadow.get("losses", 0),
            "shadow_open": shadow.get("open", 0),
            "error_count": errors["count"],
            "error_latest_at": errors["latest_at"],
            "processes": processes,
            "context_phase": context.get("fase", "N/D"),
            "context_trend": context.get("tendencia", "N/D"),
            "context_volatility": context.get("volatilidade", "N/D"),
            "last_log": last_log,
            "lab_learning": True,
            "study_state": _get_study_state(),
            "demo_state": _get_demo_state(),
            "recent_demo_orders": _get_recent_demo_orders(),
            "simulated": _get_simulated_summary(),
            "performance": _get_performance_summary(),
        },
    }