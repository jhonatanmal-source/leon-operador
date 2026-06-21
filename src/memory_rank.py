# ===================================
# MEMORY RANK
# ===================================

import os

def analisar_rank():

    arquivo = "C:/XAU_ELITE_AI/data/trade_memory.csv"

    if not os.path.exists(arquivo):

        print("MEMÓRIA NÃO ENCONTRADA")
        return

    cenarios = {}

    with open(
        arquivo,
        "r",
        encoding="utf-8"
    ) as f:

        for linha in f:

            partes = linha.strip().split(";")

            if len(partes) < 6:
                continue

            tendencia = partes[1]
            momentum = partes[2]

            chave = f"{tendencia} + {momentum}"

            cenarios[chave] = cenarios.get(chave, 0) + 1

    print()
    print("===================================")
    print("MEMORY RANK")
    print("===================================")

    ranking = sorted(
        cenarios.items(),
        key=lambda x: x[1],
        reverse=True
    )

    for setup, total in ranking:

        print(f"{setup}: {total}")