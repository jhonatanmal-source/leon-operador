# ===================================
# CONFIDENCE RANK
# ===================================

import os

ARQUIVO = "C:/XAU_ELITE_AI/data/trade_memory.csv"

def analisar_confianca():

    print()
    print("===================================")
    print("CONFIDENCE RANK")
    print("===================================")

    if not os.path.exists(ARQUIVO):

        print("Sem histórico.")
        return

    total = {
        "MUITO ALTA": 0,
        "ALTA": 0,
        "MÉDIA": 0,
        "BAIXA": 0
    }

    with open(
        ARQUIVO,
        "r",
        encoding="utf-8"
    ) as arquivo:

        for linha in arquivo:

            partes = linha.strip().split(";")

            if len(partes) >= 9:

                confianca = partes[8]

                if confianca in total:

                    total[confianca] += 1

    for nivel, qtd in total.items():

        print(f"{nivel}: {qtd}")