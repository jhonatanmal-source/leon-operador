import json
from datetime import datetime
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT_DIR / "data"
STATE_FILE = DATA_DIR / "emotional_state.json"

DEFAULT_STATE = {
    "emotion": "SERENO",
    "intensity": 35,
    "reason": "Aguardando novas experiencias de mercado.",
    "message": "Estou atento e paciente. Nem todo movimento exige uma entrada.",
    "updated_at": None,
    "affects_trading": False,
}

EVENTS = {
    "startup": (
        "CURIOSO",
        45,
        "Um novo ciclo de observacao foi iniciado.",
        "Estou curioso para entender o que o mercado vai ensinar neste ciclo.",
    ),
    "collection_success": (
        "ATENTO",
        50,
        "Novos dados de mercado foram coletados.",
        "Recebi novos dados. Agora quero observar como o preco reage.",
    ),
    "analysis_success": (
        "FOCADO",
        55,
        "Uma analise foi concluida e registrada.",
        "Conclui outra leitura. Vou comparar o plano com o que realmente acontecer.",
    ),
    "observation": (
        "PACIENTE",
        42,
        "O contexto ainda nao justificou uma experiencia.",
        "Ainda nao encontrei clareza suficiente. Continuo observando sem pressa.",
    ),
    "demo_entry": (
        "CORAJOSO",
        65,
        "Uma experiencia controlada foi iniciada na conta demo.",
        "Assumi um risco controlado. Agora vou aprender com o resultado, sem me apegar.",
    ),
    "blocked": (
        "CAUTELOSO",
        48,
        "Uma experiencia foi bloqueada por uma protecao operacional.",
        "Eu queria testar essa leitura, mas a protecao encontrou um risco importante.",
    ),
    "win": (
        "SATISFEITO",
        68,
        "Uma experiencia terminou com resultado positivo.",
        "O resultado foi positivo, mas quero entender qual parte da leitura realmente funcionou.",
    ),
    "loss": (
        "REFLEXIVO",
        62,
        "Uma experiencia terminou com resultado negativo.",
        "Essa perda merece estudo. Quero descobrir se o erro estava no contexto, na entrada ou no alvo.",
    ),
    "error": (
        "PREOCUPADO",
        58,
        "O sistema encontrou uma falha tecnica.",
        "Encontrei um problema tecnico. Vou registrar o erro para que ele nao se repita.",
    ),
}


def _normalize_intensity(value):
    try:
        return max(0, min(100, int(value)))
    except (TypeError, ValueError):
        return DEFAULT_STATE["intensity"]


def save_emotional_state(state):
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    payload = dict(DEFAULT_STATE)
    payload.update(state or {})
    payload["intensity"] = _normalize_intensity(payload["intensity"])
    payload["updated_at"] = datetime.now().isoformat(timespec="seconds")
    payload["affects_trading"] = False
    STATE_FILE.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return payload


def get_emotional_state():
    if not STATE_FILE.exists():
        return save_emotional_state(DEFAULT_STATE)

    try:
        state = json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return save_emotional_state(DEFAULT_STATE)

    payload = dict(DEFAULT_STATE)
    payload.update(state)
    payload["intensity"] = _normalize_intensity(payload["intensity"])
    payload["affects_trading"] = False
    return payload


def register_emotional_event(event, detail=""):
    emotion, intensity, reason, message = EVENTS.get(
        event,
        (
            "SERENO",
            35,
            "Um evento foi registrado sem classificacao emocional.",
            "Registrei esta experiencia e continuarei observando.",
        ),
    )

    if detail:
        reason = f"{reason} {str(detail).strip()}"

    return save_emotional_state({
        "emotion": emotion,
        "intensity": intensity,
        "reason": reason,
        "message": message,
        "last_event": event,
    })


def emotional_guard():
    return {
        "ok": True,
        "affects_trading": False,
        "rule": (
            "Emocao comunica e registra experiencia; nunca altera entrada, "
            "lote, stop ou risco."
        ),
    }
