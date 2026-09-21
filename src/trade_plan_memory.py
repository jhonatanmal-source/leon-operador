# ===================================
# TRADE PLAN MEMORY
# ===================================

import os
from datetime import datetime
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parents[1] / "data"
ARQUIVO = DATA_DIR / "trade_plan_memory.csv"

def salvar_trade_plan(
    ativo,
    direcao,
    smc,
    elliott,
    brain_score,
    confianca
):

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    arquivo = DATA_DIR / ARQUIVO.name

    if not os.path.exists(arquivo):

        with open(
            arquivo,
            "w",
            encoding="utf-8"
        ) as f:

            f.write(
                "data;ativo;direcao;smc;elliott;brain_score;confianca\n"
            )

    with open(
        arquivo,
        "a",
        encoding="utf-8"
    ) as f:

        f.write(
            f"{datetime.now()};"
            f"{ativo};"
            f"{direcao};"
            f"{smc};"
            f"{elliott};"
            f"{brain_score};"
            f"{confianca}\n"
        )

    print("TRADE PLAN SALVO")
    