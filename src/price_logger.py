# ===================================
# PRICE LOGGER
# ===================================

from datetime import datetime
from pathlib import Path


DATA_DIR = Path(__file__).resolve().parents[1] / "data"

def registrar_preco(simbolo, bid, ask):

    agora = datetime.now()
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    with open(
        DATA_DIR / "price_history.csv",
        "a",
        encoding="utf-8"
    ) as arquivo:

        arquivo.write(
            f"{agora};{simbolo};{bid};{ask}\n"
        )

    print("PREÇO REGISTRADO")