from src.paths import BASE_DIR
# ===================================
# PERFORMANCE TRACKER
# ===================================

import os

ARQUIVO = f"{BASE_DIR.as_posix()}/data/performance.csv"

def registrar_performance(resultado):

    if not os.path.exists(ARQUIVO):

        with open(ARQUIVO, "w", encoding="utf-8") as f:
            f.write("resultado\n")

    with open(ARQUIVO, "a", encoding="utf-8") as f:
        f.write(f"{resultado}\n")

    print("PERFORMANCE REGISTRADA")