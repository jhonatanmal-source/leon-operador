# ===================================
# LEARNING REPORT
# ===================================

import os

def gerar_relatorio_aprendizado():

    print("===================================")
    print("LEARNING REPORT")
    print("===================================")

    arquivos = {
        "Preços": "/opt/leon/app/data/price_history.csv",
        "Candles": "/opt/leon/app/data/candle_history.csv",
        "Sinais": "/opt/leon/app/data/signals.csv"
    }

    for nome, caminho in arquivos.items():

        if os.path.exists(caminho):

            with open(
                caminho,
                "r",
                encoding="utf-8"
            ) as arquivo:

                total = len(arquivo.readlines())

            print(f"{nome}: {total} registros")

        else:

            print(f"{nome}: arquivo não encontrado")