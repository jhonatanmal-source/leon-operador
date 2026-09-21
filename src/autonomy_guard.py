# ===================================
# AUTONOMY GUARD
# ===================================

import configparser
import json
from datetime import datetime, timedelta
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parent.parent
CONFIG_FILE = ROOT_DIR / "config.ini"
DATA_DIR = ROOT_DIR / "data"
AUTONOMY_FILE = DATA_DIR / "autonomy_state.json"


def _carregar_config():

    config = configparser.ConfigParser()
    config.read(CONFIG_FILE, encoding="utf-8")

    if not config.has_section("AUTONOMY"):
        return {
            "enabled": False,
            "max_minutes": 60,
            "scope": "learning_only",
        }

    autonomia = config["AUTONOMY"]

    return {
        "enabled": autonomia.get("enabled", "false").lower() == "true",
        "max_minutes": autonomia.getint("max_minutes", fallback=60),
        "scope": autonomia.get("scope", "learning_only"),
    }


def _salvar_estado(estado):

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    AUTONOMY_FILE.write_text(
        json.dumps(estado, indent=2),
        encoding="utf-8",
    )


def _ler_estado():

    if not AUTONOMY_FILE.exists():
        return {}

    try:
        return json.loads(AUTONOMY_FILE.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def conceder_autonomia(minutos):

    config = _carregar_config()

    if minutos <= 0:
        return {
            "ok": False,
            "error": "AUTONOMY_INVALID_MINUTES",
        }

    if minutos > config["max_minutes"]:
        return {
            "ok": False,
            "error": "AUTONOMY_LIMIT_EXCEEDED",
            "max_minutes": config["max_minutes"],
        }

    agora = datetime.now()
    expira_em = agora + timedelta(minutes=minutos)

    estado = {
        "enabled": True,
        "scope": config["scope"],
        "started_at": agora.isoformat(timespec="seconds"),
        "expires_at": expira_em.isoformat(timespec="seconds"),
        "minutes": minutos,
    }

    _salvar_estado(estado)

    return {
        "ok": True,
        "scope": estado["scope"],
        "expires_at": estado["expires_at"],
    }


def revogar_autonomia():

    estado = _ler_estado()
    estado["enabled"] = False
    estado["revoked_at"] = datetime.now().isoformat(timespec="seconds")
    _salvar_estado(estado)

    return {
        "ok": True,
        "status": "AUTONOMY_REVOKED",
    }


def status_autonomia():

    config = _carregar_config()
    estado = _ler_estado()

    if not config["enabled"]:
        return {
            "active": False,
            "reason": "AUTONOMY_DISABLED_IN_CONFIG",
            "scope": config["scope"],
        }

    if not estado.get("enabled"):
        return {
            "active": False,
            "reason": "AUTONOMY_NOT_GRANTED",
            "scope": config["scope"],
        }

    expires_at = estado.get("expires_at")

    if not expires_at:
        return {
            "active": False,
            "reason": "AUTONOMY_EXPIRATION_MISSING",
            "scope": config["scope"],
        }

    try:
        expira_em = datetime.fromisoformat(expires_at)
    except ValueError:
        return {
            "active": False,
            "reason": "AUTONOMY_EXPIRATION_INVALID",
            "scope": config["scope"],
        }

    agora = datetime.now()

    if agora >= expira_em:
        return {
            "active": False,
            "reason": "AUTONOMY_EXPIRED",
            "scope": estado.get("scope", config["scope"]),
            "expires_at": expires_at,
        }

    restante = int((expira_em - agora).total_seconds())

    return {
        "active": True,
        "reason": "AUTONOMY_ACTIVE",
        "scope": estado.get("scope", config["scope"]),
        "expires_at": expires_at,
        "remaining_seconds": restante,
    }
