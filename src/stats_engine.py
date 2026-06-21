# ===================================
# STATS ENGINE
# ===================================

import os

def mostrar_estatisticas():

    print("===================================")
    print("STATS ENGINE")
    print("===================================")

    arquivo = "C:/XAU_ELITE_AI/data/leon_data.json"

    if os.path.exists(arquivo):

        with open(
            arquivo,
            "r",
            encoding="utf-8"
        ) as f:

            linhas = f.readlines()

        print(f"Execuções registradas: {len(linhas)}")

    else:

        print("Nenhum dado encontrado.")