# ===================================
# SWING ENGINE
# ===================================

import csv
from pathlib import Path


ARQUIVO = Path(__file__).resolve().parent.parent / "data" / "candle_history.csv"


def analisar_swings():

    print()
    print("===================================")
    print("SWING ENGINE")
    print("===================================")

    candles = []

    try:
        with ARQUIVO.open("r", encoding="utf-8") as arquivo:
            leitor = csv.reader(arquivo, delimiter=";")

            for linha in leitor:
                if len(linha) < 6:
                    continue
                try:
                    float(linha[3])
                    float(linha[4])
                except ValueError:
                    continue
                candles.append(linha)

    except (OSError, csv.Error):
        print("Sem historico suficiente.")
        return None, None

    if len(candles) < 5:
        print("Poucos candles.")
        return None, None

    janela = candles[-20:]
    ultimo_topo = max(float(candle[3]) for candle in janela)
    ultimo_fundo = min(float(candle[4]) for candle in janela)

    print(f"TOPO : {ultimo_topo}")
    print(f"FUNDO: {ultimo_fundo}")

    return ultimo_topo, ultimo_fundo
