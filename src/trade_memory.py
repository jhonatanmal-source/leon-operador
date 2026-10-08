from src.paths import BASE_DIR
from datetime import datetime

def salvar_memoria_trade(
    tendencia,
    momentum,
    score,
    sinal,
    qualidade,
    smc,
    elliott,
    confianca
):

    with open(
        f"{BASE_DIR.as_posix()}/data/trade_memory.csv",
        "a",
        encoding="utf-8"
    ) as arquivo:

        arquivo.write(
            f"{datetime.now()};"
            f"{tendencia};"
            f"{momentum};"
            f"{score};"
            f"{sinal};"
            f"{qualidade};"
            f"{smc};"
            f"{elliott};"
            f"{confianca}\n"
        )

    print("MEMÓRIA SALVA")