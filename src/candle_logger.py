# ===================================
# CANDLE LOGGER
# ===================================

from datetime import datetime

def registrar_candle(
    simbolo,
    abertura,
    maxima,
    minima,
    fechamento
):

    agora = datetime.now()

    with open(
        "C:/XAU_ELITE_AI/data/candle_history.csv",
        "a",
        encoding="utf-8"
    ) as arquivo:

        arquivo.write(
            f"{agora};{simbolo};{abertura};{maxima};{minima};{fechamento}\n"
        )

    print("CANDLE REGISTRADO")