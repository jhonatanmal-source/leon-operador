import csv
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parent.parent
PRE_OPERATION_FILE = ROOT_DIR / "data" / "pre_operation_trades.csv"
ORDER_MEMORY_FILE = ROOT_DIR / "data" / "mt5_order_memory.csv"


def avaliar_setup(tendencia):
    direcao = (
        "COMPRA"
        if tendencia == "ALTA"
        else "VENDA"
        if tendencia == "BAIXA"
        else None
    )

    if direcao is None or not PRE_OPERATION_FILE.exists():
        return "CONFIANCA BAIXA"

    executed_ids = set()
    if ORDER_MEMORY_FILE.exists():
        with ORDER_MEMORY_FILE.open("r", encoding="utf-8", newline="") as file:
            for row in csv.DictReader(file, delimiter=";"):
                if row.get("status") == "ENVIADA":
                    executed_ids.add(row.get("pre_operation_id"))

    resultados = []
    with PRE_OPERATION_FILE.open("r", encoding="utf-8", newline="") as file:
        for row in csv.DictReader(file, delimiter=";"):
            if row.get("id") not in executed_ids:
                continue
            if row.get("direcao") != direcao:
                continue
            result = row.get("resultado") or ""
            if result == "LOSS" or result.startswith("WIN"):
                resultados.append(result)

    total = len(resultados)
    wins = sum(1 for result in resultados if result.startswith("WIN"))
    winrate = (wins / total) * 100 if total else 0

    print()
    print("===================================")
    print("SETUP REPUTATION")
    print("===================================")
    print(f"SETUP: {tendencia}")
    print(f"RESULTADOS REAIS: {total}")
    print(f"WIN RATE REAL: {winrate:.2f}%")

    if winrate >= 70 and total >= 10:
        return "CONFIANCA ALTA"
    if winrate >= 50 and total >= 6:
        return "CONFIANCA MEDIA"
    return "CONFIANCA BAIXA"
