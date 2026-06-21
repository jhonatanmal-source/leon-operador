# ===================================
# MARKET READER
# ===================================

import MetaTrader5 as mt5
from price_logger import registrar_preco

def ler_preco_xau():

    if not mt5.initialize():

        print("ERRO MT5")
        return

    simbolo = "XAUUSD"

    mt5.symbol_select(simbolo, True)

    tick = mt5.symbol_info_tick(simbolo)

    if tick:

        print("===================================")
        print("MARKET READER")
        print("===================================")

        print(f"SIMBOLO: {simbolo}")
        print(f"BID: {tick.bid}")
        print(f"ASK: {tick.ask}")

        registrar_preco(
            simbolo,
            tick.bid,
            tick.ask
        )

    else:

        print("SEM DADOS")

    mt5.shutdown()