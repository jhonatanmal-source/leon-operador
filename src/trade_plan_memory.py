# ===================================
# TRADE PLAN MEMORY
# ===================================

import os
from datetime import datetime

ARQUIVO = "C:/XAU_ELITE_AI/data/trade_plan_memory.csv"

def salvar_trade_plan(
    ativo,
    direcao,
    smc,
    elliott,
    brain_score,
    confianca
):

    if not os.path.exists(ARQUIVO):

        with open(
            ARQUIVO,
            "w",
            encoding="utf-8"
        ) as f:

            f.write(
                "data;ativo;direcao;smc;elliott;brain_score;confianca\n"
            )

    with open(
        ARQUIVO,
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
    