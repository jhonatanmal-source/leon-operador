from src.paths import BASE_DIR
# ===================================
# LEARNING REPORT
# ===================================

import os

def gerar_relatorio_aprendizado():

    print("===================================")
    print("LEARNING REPORT")
    print("===================================")

    arquivos = {
        "Preços": f"{BASE_DIR.as_posix()}/data/price_history.csv",
        "Candles": f"{BASE_DIR.as_posix()}/data/candle_history.csv",
        "Sinais": f"{BASE_DIR.as_posix()}/data/signals.csv"
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