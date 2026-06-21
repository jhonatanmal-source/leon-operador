import configparser
import csv
import json
import os
from datetime import datetime
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parent.parent
CONFIG_FILE = ROOT_DIR / "config.ini"
SHADOW_FILE = ROOT_DIR / "data" / "shadow_trades.csv"
LAB_EVENT_FILE = ROOT_DIR / "data" / "lab_entry_events.json"
ALLOWED_MISSING_CONFIRMATIONS = {
    "FIBONACCI_ONDA_2_OU_4",
    "CAPTURA_LIQUIDEZ",
}


def _config():
    parser = configparser.ConfigParser()
    parser.read(CONFIG_FILE, encoding="utf-8")
    section = parser["EXECUTION"] if parser.has_section("EXECUTION") else {}

    return {
        "enabled": (
            str(section.get("demo_only", "true")).lower() == "true"
            and str(section.get("learning_lab_enabled", "false")).lower()
            == "true"
            and str(
                section.get(
                    "lab_shadow_evidence_enabled",
                    "false",
                )
            ).lower()
            == "true"
        ),
        "min_closed": int(section.get("lab_shadow_min_closed", 2)),
        "min_winrate": float(section.get("lab_shadow_min_winrate", 70)),
    }


def _read_shadow_rows():
    if not SHADOW_FILE.exists():
        return []

    try:
        with SHADOW_FILE.open("r", encoding="utf-8", newline="") as file:
            return list(csv.DictReader(file, delimiter=";"))
    except (OSError, csv.Error):
        return []


def shadow_evidence(rows=None):
    rows = rows if rows is not None else _read_shadow_rows()
    eligible = []

    for row in rows:
        if row.get("status") != "FECHADO":
            continue

        missing = {
            item.strip()
            for item in str(row.get("missing_confirmations") or "").split(",")
            if item.strip()
        }
        if missing and missing.issubset(ALLOWED_MISSING_CONFIRMATIONS):
            eligible.append(row)

    wins = sum(row.get("result") == "WIN_2R" for row in eligible)
    losses = sum(row.get("result") == "LOSS" for row in eligible)
    decided = wins + losses
    winrate = round(wins / decided * 100, 2) if decided else 0

    return {
        "closed": decided,
        "wins": wins,
        "losses": losses,
        "winrate": winrate,
    }


def _used_events():
    if not LAB_EVENT_FILE.exists():
        return {}

    try:
        return json.loads(LAB_EVENT_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def lab_event_available(signature):
    return bool(signature) and signature not in _used_events()


def mark_lab_event(signature):
    if not signature:
        return False

    events = _used_events()
    events[signature] = datetime.now().isoformat(timespec="seconds")
    LAB_EVENT_FILE.parent.mkdir(parents=True, exist_ok=True)
    temporary = LAB_EVENT_FILE.with_name(
        f".{LAB_EVENT_FILE.name}.{os.getpid()}.tmp"
    )

    try:
        temporary.write_text(
            json.dumps(events, indent=2, ensure_ascii=True),
            encoding="utf-8",
        )
        temporary.replace(LAB_EVENT_FILE)
    finally:
        try:
            temporary.unlink(missing_ok=True)
        except OSError:
            pass

    return True


def evaluate_lab_entry(
    smc_confirmed,
    top_down_confirmed,
    strict_confirmation,
    missing_confirmations,
    rows=None,
):
    config = _config()
    evidence = shadow_evidence(rows)
    missing = set(missing_confirmations)
    only_allowed_missing = (
        bool(missing)
        and missing.issubset(ALLOWED_MISSING_CONFIRMATIONS)
    )

    approved = (
        config["enabled"]
        and smc_confirmed
        and top_down_confirmed
        and not strict_confirmation
        and only_allowed_missing
        and evidence["closed"] >= config["min_closed"]
        and evidence["winrate"] >= config["min_winrate"]
    )

    return {
        "approved": approved,
        "mode": "LAB_SHADOW_EVIDENCE" if approved else "STRICT",
        "evidence": evidence,
        "requirements": {
            "min_closed": config["min_closed"],
            "min_winrate": config["min_winrate"],
        },
        "missing_confirmations": sorted(missing),
    }
