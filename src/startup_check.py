# ===================================
# STARTUP CHECK
# ===================================

import os

def verificar_estrutura():

    print("===================================")
    print("STARTUP CHECK")
    print("===================================")

    pastas = [
        "C:/XAU_ELITE_AI/logs",
        "C:/XAU_ELITE_AI/data",
        "C:/XAU_ELITE_AI/reports",
        "C:/XAU_ELITE_AI/backups"
    ]

    for pasta in pastas:

        if os.path.exists(pasta):
            print(f"OK -> {pasta}")
        else:
            print(f"ERRO -> {pasta}")