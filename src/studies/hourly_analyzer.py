# ===================================
# HOURLY ANALYZER
# ===================================

from collections import Counter

def analisar_horarios():

    arquivo = "C:/XAU_ELITE_AI/data/trade_memory.csv"

    horas = Counter()

    try:

        with open(
            arquivo,
            "r",
            encoding="utf-8"
        ) as f:

            for linha in f:

                partes = linha.split(";")

                hora = partes[0][11:13]

                horas[hora] += 1

        print()
        print("===================================")
        print("HOURLY ANALYZER")
        print("===================================")

        for hora, qtd in sorted(horas.items()):

            print(f"{hora}h : {qtd}")

    except Exception as erro:

        print(f"ERRO: {erro}")