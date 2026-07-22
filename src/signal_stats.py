# ===================================
# SIGNAL STATS
# ===================================

import os

def analisar_sinais():

    arquivo = "/opt/leon/app/data/signals.csv"

    if not os.path.exists(arquivo):

        print("Nenhum sinal encontrado.")
        return

    compras = 0
    vendas = 0
    observar = 0

    with open(
        arquivo,
        "r",
        encoding="utf-8"
    ) as f:

        linhas = f.readlines()

        for linha in linhas:

            if "COMPRA" in linha:
                compras += 1

            if "VENDA" in linha:
                vendas += 1

            if "OBSERVAR" in linha:
                observar += 1

    print("===================================")
    print("SIGNAL STATS")
    print("===================================")

    print(f"Compras : {compras}")
    print(f"Vendas  : {vendas}")
    print(f"Observar: {observar}")