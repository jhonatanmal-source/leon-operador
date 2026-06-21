# ===================================
# TELEGRAM CONFIG
# ===================================

import configparser
import os
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parent.parent
CONFIG_FILE = ROOT_DIR / "config.ini"
ENV_FILE = ROOT_DIR / ".env"


def _load_env_file():
    values = {}
    if not ENV_FILE.exists():
        return values

    for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
        if not line or line.lstrip().startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip()
    return values


def _carregar_config_ini():
    config = configparser.ConfigParser()
    config.read(CONFIG_FILE, encoding="utf-8")

    if config.has_section("TELEGRAM"):
        return config["TELEGRAM"]

    return {}


_telegram_config = _carregar_config_ini()
_env_values = _load_env_file()

TOKEN = (
    os.getenv("LEON_TELEGRAM_TOKEN")
    or os.getenv("TELEGRAM_TOKEN")
    or _env_values.get("LEON_TELEGRAM_TOKEN", "")
    or _env_values.get("TELEGRAM_TOKEN", "")
    or _telegram_config.get("token", "")
).strip()

CHAT_ID = (
    os.getenv("LEON_TELEGRAM_CHAT_ID")
    or os.getenv("TELEGRAM_CHAT_ID")
    or _env_values.get("LEON_TELEGRAM_CHAT_ID", "")
    or _env_values.get("TELEGRAM_CHAT_ID", "")
    or _telegram_config.get("chat_id", "")
).strip()

TELEGRAM_ENABLED = (
    os.getenv("LEON_TELEGRAM_ENABLED")
    or os.getenv("TELEGRAM_ENABLED")
    or _env_values.get("LEON_TELEGRAM_ENABLED", "")
    or _env_values.get("TELEGRAM_ENABLED", "")
    or _telegram_config.get("enabled", "false")
).lower() == "true"
TELEGRAM_TIMEOUT = int(_telegram_config.get("timeout", "10"))
TELEGRAM_DEDUPE_SECONDS = int(_telegram_config.get("dedupe_seconds", "10"))
