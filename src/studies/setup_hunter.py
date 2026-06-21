# ===================================
# SETUP HUNTER
# ===================================

from collections import Counter

def cacar_setups():

    arquivo = "C:/XAU_ELITE_AI/data/trade_memory.csv"

    setups = Counter()

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

                setups[setup] += 1

        print()
        print("===================================")
        print("SETUP HUNTER")
        print("===================================")

        for setup, qtd in setups.most_common():

            print(f"{setup}: {qtd}")

    except Exception as erro:

        print(f"ERRO: {erro}")