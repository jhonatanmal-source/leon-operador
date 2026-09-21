# ===================================
# BRAIN EVOLUTION ENGINE
# ===================================

import os
import csv
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
ARQUIVO = BASE_DIR / "data" / "brain_memory.csv"


def evoluir_cerebro():

    print()
    print("===================================")
    print("BRAIN EVOLUTION")
    print("===================================")

    if not os.path.exists(ARQUIVO):

        print("Nenhuma memória encontrada.")
        return

    total = 0
    acertos = 0

    with open(
        ARQUIVO,
        "r",
        encoding="utf-8"
    ) as arquivo:

        leitor = csv.DictReader(
            arquivo,
            delimiter=";"
        )

        for linha in leitor:

            total += 1

            if linha["resultado"] == "ACERTO":

                acertos += 1

    if total == 0:

        print("Sem dados suficientes.")
        return

    winrate = (acertos / total) * 100

    print(f"TRADES ANALISADOS : {total}")
    print(f"WIN RATE GLOBAL   : {winrate:.2f}%")

    print()

    if winrate >= 90:

        print("STATUS: CÉREBRO MUITO FORTE")

    elif winrate >= 80:

        print("STATUS: CÉREBRO FORTE")

    elif winrate >= 70:

        print("STATUS: CÉREBRO ESTÁVEL")

    else:

        print("STATUS: NECESSITA EVOLUÇÃO")