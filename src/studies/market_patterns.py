# ===================================
# MARKET PATTERNS
# ===================================

from collections import Counter

def analisar_padroes():

    arquivo = "C:/XAU_ELITE_AI/data/trade_memory.csv"

    ranking = Counter()

    try:

        with open(
            arquivo,
            "r",
            encoding="utf-8"
        ) as f:

            for linha in f:

                partes = linha.strip().split(";")

                if len(partes) < 6:
                    continue

                setup = f"{partes[1]} + {partes[2]}"

                ranking[setup] += 1

        print()
        print("===================================")
        print("MARKET PATTERNS")
        print("===================================")

        for setup, qtd in ranking.most_common():

            print(f"{setup}: {qtd}")

    except Exception as erro:

        print(f"ERRO: {erro}")# ===================================
# MARKET PATTERNS
# ===================================

from collections import Counter

def analisar_padroes():

    arquivo = "C:/XAU_ELITE_AI/data/trade_memory.csv"

    ranking = Counter()

    try:

        with open(
            arquivo,
            "r",
            encoding="utf-8"
        ) as f:

            for linha in f:

                partes = linha.strip().split(";")

                if len(partes) < 6:
                    continue

                setup = f"{partes[1]} + {partes[2]}"

                ranking[setup] += 1

        print()
        print("===================================")
        print("MARKET PATTERNS")
        print("===================================")

        for setup, qtd in ranking.most_common():

            print(f"{setup}: {qtd}")

    except Exception as erro:

        print(f"ERRO: {erro}")