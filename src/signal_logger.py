# ===================================
# SIGNAL LOGGER
# ===================================

from datetime import datetime

def registrar_sinal(
    tendencia,
    momentum,
    score,
    sinal
):

    agora = datetime.now()

    with open(
        "C:/XAU_ELITE_AI/data/signals.csv",
        "a",
        encoding="utf-8"
    ) as arquivo:

        arquivo.write(
            f"{agora};{tendencia};{momentum};{score};{sinal}\n"
        )

    print("SINAL REGISTRADO")