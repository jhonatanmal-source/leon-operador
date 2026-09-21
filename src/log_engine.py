from datetime import datetime, timezone
from pathlib import Path
from typing import Any

LOG_PATHS: list[Path] = []
AGENT_HEALTH_FILE: Path | None = None

ROOT_DIR = Path(__file__).resolve().parent.parent
DEFAULT_LOG_DIR = ROOT_DIR / "logs"

_agent_states: dict[str, dict[str, Any]] = {}
_last_events: dict[str, dict[str, Any]] = {}


def registrar_log(mensagem):
    agora = datetime.now()
    linha = f"[{agora}] {mensagem}\n"
    caminhos = LOG_PATHS if LOG_PATHS else [
        DEFAULT_LOG_DIR / "leon_log.txt",
    ]

    for caminho in caminhos:
        try:
            caminho.parent.mkdir(parents=True, exist_ok=True)
            with caminho.open("a", encoding="utf-8") as arquivo:
                arquivo.write(linha)
            return True
        except PermissionError:
            continue

    return False


def registrar_evento_agente(
    agent: str,
    *,
    cycle_id: str = "",
    analysis_id: str = "",
    pre_operation_id: str = "",
    symbol: str = "",
    decision: str = "",
    state: str = "",
    error: str = "",
    reason: str = "",
    input_status: str = "",
    output_status: str = "",
) -> dict[str, Any]:
    now = datetime.now(timezone.utc)
    event_key = f"{agent}:{input_status}:{output_status}:{decision}:{reason}:{state}"

    last = _last_events.get(agent)
    if last and last["_key"] == event_key:
        return {"ok": True, "deduplicated": True}

    if agent not in _agent_states:
        _agent_states[agent] = {
            "state": "INIT",
            "error_count": 0,
            "last_error": None,
            "last_event": None,
        }

    event = {
        "_key": event_key,
        "timestamp": now.isoformat(),
        "agent": agent,
        "cycle_id": cycle_id,
        "analysis_id": analysis_id,
        "pre_operation_id": pre_operation_id,
        "symbol": symbol,
        "decision": decision,
        "state": state,
        "error": error,
        "reason": reason,
        "input_status": input_status,
        "output_status": output_status,
    }

    _last_events[agent] = event

    state_data = _agent_states[agent]
    if error:
        state_data["error_count"] += 1
        state_data["last_error"] = error
    state_data["state"] = state or state_data["state"]
    state_data["last_event"] = now.isoformat()

    line = f"AGENT_EVENT | agent={agent} cycle_id={cycle_id} analysis_id={analysis_id} pre_operation_id={pre_operation_id} symbol={symbol} decision={decision} state={state} error={error}\n"
    for path in LOG_PATHS:
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("a", encoding="utf-8") as f:
                f.write(line)
        except OSError:
            continue

    if AGENT_HEALTH_FILE:
        try:
            import json
            AGENT_HEALTH_FILE.parent.mkdir(parents=True, exist_ok=True)
            health = obter_saude_agentes()
            AGENT_HEALTH_FILE.write_text(
                json.dumps(health, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except OSError:
            pass

    return {"ok": True}


def obter_saude_agentes() -> dict[str, Any]:
    return {"agents": dict(_agent_states)}


def _salvar_saude_agentes(payload: dict[str, Any]) -> None:
    if AGENT_HEALTH_FILE:
        import json
        AGENT_HEALTH_FILE.parent.mkdir(parents=True, exist_ok=True)
        AGENT_HEALTH_FILE.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
