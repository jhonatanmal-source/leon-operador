# ===================================
# DASHBOARD REPORT
# ===================================

import os

def mostrar_dashboard():

    print()
    print("===================================")
    print("LEON DASHBOARD")
    print("===================================")

    arquivos = [
        "price_history.csv",
        "candle_history.csv",
        "signals.csv"
    ]

    for arquivo in arquivos:

        caminho = f"/opt/leon/app/data/{arquivo}"

        if os.path.exists(caminho):

            with open(caminho,"r",encoding="utf-8") as f:

                total = len(f.readlines())

            print(f"{arquivo}: {total} registros")

    print("===================================")