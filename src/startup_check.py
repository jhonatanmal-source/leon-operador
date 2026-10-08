from src.paths import BASE_DIR
# ===================================
# STARTUP CHECK
# ===================================

import os

def verificar_estrutura():

    print("===================================")
    print("STARTUP CHECK")
    print("===================================")

    pastas = [
        f"{BASE_DIR.as_posix()}/logs",
        f"{BASE_DIR.as_posix()}/data",
        f"{BASE_DIR.as_posix()}/reports",
        f"{BASE_DIR.as_posix()}/backups"
    ]

    for pasta in pastas:

        if os.path.exists(pasta):
            print(f"OK -> {pasta}")
        else:
            print(f"ERRO -> {pasta}")