# ===================================
# PRICE LOGGER
# ===================================

from datetime import datetime

def registrar_preco(simbolo, bid, ask):

    agora = datetime.now()

    with open(
        "C:/XAU_ELITE_AI/data/price_history.csv",
        "a",
        encoding="utf-8"
    ) as arquivo:

        arquivo.write(
            f"{agora};{simbolo};{bid};{ask}\n"
        )

    print("PREÇO REGISTRADO")