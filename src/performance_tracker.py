# ===================================
# PERFORMANCE TRACKER
# ===================================

import os

ARQUIVO = "C:/XAU_ELITE_AI/data/performance.csv"

def registrar_performance(resultado):

    if not os.path.exists(ARQUIVO):

        with open(ARQUIVO, "w", encoding="utf-8") as f:
            f.write("resultado\n")

    with open(ARQUIVO, "a", encoding="utf-8") as f:
        f.write(f"{resultado}\n")

    print("PERFORMANCE REGISTRADA")