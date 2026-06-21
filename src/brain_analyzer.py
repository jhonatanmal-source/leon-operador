# ===================================
# BRAIN ANALYZER
# ===================================

import os
import csv

ARQUIVO = "C:/XAU_ELITE_AI/data/brain_memory.csv"


def analisar_brain():

    print()
    print("===================================")
    print("BRAIN ANALYZER")
    print("===================================")

    if not os.path.exists(ARQUIVO):

        print("Nenhuma memória cerebral encontrada.")
        return

    total = 0

    alta_acertos = 0
    alta_erros = 0

    muito_alta_acertos = 0
    muito_alta_erros = 0

    with open(
        ARQUIVO,
        "r",
        encoding="utf-8"
    ) as arquivo:

        leitor = csv.DictReader(
            arquivo,
            delimiter=";"
        )

        for linha in leitor:

            total += 1

            confianca = linha["confianca"]
            resultado = linha["resultado"]

            if confianca == "MUITO ALTA":

                if resultado == "ACERTO":
                    muito_alta_acertos += 1
                else:
                    muito_alta_erros += 1

            elif confianca == "ALTA":

                if resultado == "ACERTO":
                    alta_acertos += 1
                else:
                    alta_erros += 1

    print(f"TOTAL REGISTROS : {total}")

    print()
    print("MUITO ALTA")

    total_ma = muito_alta_acertos + muito_alta_erros

    if total_ma > 0:

        winrate = (
            muito_alta_acertos /
            total_ma
        ) * 100

        print(f"ACERTOS : {muito_alta_acertos}")
        print(f"ERROS   : {muito_alta_erros}")
        print(f"WINRATE : {winrate:.2f}%")

    print()
    print("ALTA")

    total_a = alta_acertos + alta_erros

    if total_a > 0:

        winrate = (
            alta_acertos /
            total_a
        ) * 100

        print(f"ACERTOS : {alta_acertos}")
        print(f"ERROS   : {alta_erros}")
        print(f"WINRATE : {winrate:.2f}%")