# ===================================
# SIGNAL LOGGER
# ===================================

from datetime import datetime
from pathlib import Path


DATA_DIR = Path(__file__).resolve().parents[1] / "data"

def registrar_sinal(
    tendencia,
    momentum,
    score,
    sinal
):

    agora = datetime.now()
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    with open(
        DATA_DIR / "signals.csv",
        "a",
        encoding="utf-8"
    ) as arquivo:

        arquivo.write(
            f"{agora};{tendencia};{momentum};{score};{sinal}\n"
        )

    print("SINAL REGISTRADO")