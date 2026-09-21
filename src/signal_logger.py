# ===================================
# SIGNAL LOGGER
# ===================================

import csv
from datetime import datetime
from pathlib import Path


DATA_DIR = Path(__file__).resolve().parents[1] / "data"
FIELDS = ["timestamp", "tendencia", "momentum", "score", "sinal"]


def _signals_file():
    return DATA_DIR / "signals.csv"


def _ensure_header():
    """Create file with header if it doesn't exist or is empty."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    signals_file = _signals_file()
    if signals_file.exists() and signals_file.stat().st_size > 0:
        return
    with signals_file.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f, delimiter=";")
        writer.writerow(FIELDS)


def registrar_sinal(tendencia, momentum, score, sinal):
    _ensure_header()
    signals_file = _signals_file()
    with signals_file.open("a", encoding="utf-8", newline="") as f:
        writer = csv.writer(f, delimiter=";")
        writer.writerow([datetime.now().isoformat(timespec="seconds"), tendencia, momentum, score, sinal])
    print("SINAL REGISTRADO")
