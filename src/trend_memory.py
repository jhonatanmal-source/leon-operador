# ===================================
# TREND MEMORY
# ===================================

from collections import Counter

def analisar_tendencias():

    arquivo = "C:/XAU_ELITE_AI/data/trade_memory.csv"

    tendencias = Counter()

    try:

        with open(
            arquivo,
            "r",
            encoding="utf-8"
        ) as f:

            for linha in f:

                partes = linha.split(";")

                tendencias[partes[1]] += 1

        print()
        print("===================================")
        print("TREND MEMORY")
        print("===================================")

        for tendencia, qtd in tendencias.items():

            print(f"{tendencia}: {qtd}")

    except:

        print("SEM HISTÓRICO")