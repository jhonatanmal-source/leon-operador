# ===================================
# CANDLE READER
# ===================================

from src.candle_logger import registrar_candle

import mt5linux_compat as mt5

def ler_candle_m15():

    if not mt5.initialize():
        print("ERRO MT5")
        return

    simbolo = "Gold_Spot"

    mt5.symbol_select(simbolo, True)

    candles = mt5.copy_rates_from_pos(
        simbolo,
        mt5.TIMEFRAME_M15,
        0,
        1
    )

    if candles is not None and len(candles) > 0:

        candle = candles[0]

        print("===================================")
        print("CANDLE READER")
        print("===================================")

        print(f"Abertura: {candle['open']}")
        print(f"Máxima: {candle['high']}")
        print(f"Mínima: {candle['low']}")
        print(f"Fechamento: {candle['close']}")

    else:

        print("SEM CANDLES")

    mt5.shutdown()

    registrar_candle(
    simbolo,
    candle["open"],
    candle["high"],
    candle["low"],
    candle["close"]
)


def ler_candle_h1():
    return ler_candle_m15()
    
