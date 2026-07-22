# ===================================
# STARTUP CHECK
# ===================================

import os

def verificar_estrutura():

    print("===================================")
    print("STARTUP CHECK")
    print("===================================")

    pastas = [
        "/opt/leon/app/logs",
        "/opt/leon/app/data",
        "/opt/leon/app/reports",
        "/opt/leon/app/backups"
    ]

    for pasta in pastas:

        if os.path.exists(pasta):
            print(f"OK -> {pasta}")
        else:
            print(f"ERRO -> {pasta}")