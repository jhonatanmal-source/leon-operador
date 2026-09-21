# ===================================
# MEMORY ANALYZER
# ===================================

import os

ARQUIVO = "../data/performance.csv"

def analisar_memoria():

    if not os.path.exists(ARQUIVO):

        print("MEMÓRIA NÃO ENCONTRADA")
        return

    with open(ARQUIVO, "r") as f:

        linhas = f.readlines()[1:]

    total = len(linhas)

    acertos = sum(
        1 for linha in linhas
        if "ACERTO" in linha
    )

    erros = total - acertos

    print()
    print("===================================")
    print("MEMORY ANALYZER")
    print("===================================")

    print(f"Total Trades : {total}")
    print(f"Acertos      : {acertos}")
    print(f"Erros        : {erros}")

    if total > 0:

        winrate = (acertos / total) * 100

        print(f"Win Rate     : {winrate:.2f}%")