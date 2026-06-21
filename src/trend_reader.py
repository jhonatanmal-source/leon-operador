# ===================================
# TREND READER
# ===================================

import MetaTrader5 as mt5

def analisar_tendencia_real():

    if not mt5.initialize():

        print("ERRO MT5")
        return "LATERAL"

    simbolo = "XAUUSD"

    mt5.symbol_select(simbolo, True)

    candles = mt5.copy_rates_from_pos(
        simbolo,
        mt5.TIMEFRAME_M15,
        0,
        20
    )

    if candles is None or len(candles) < 20:

        mt5.shutdown()
        return "LATERAL"

    primeiro = candles[0]["close"]
    ultimo = candles[-1]["close"]

    print("===================================")
    print("TREND READER")
    print("===================================")

    if ultimo > primeiro:

        print("TENDÊNCIA: ALTA")
        resultado = "ALTA"

    elif ultimo < primeiro:

        print("TENDÊNCIA: BAIXA")
        resultado = "BAIXA"

    else:

        print("TENDÊNCIA: LATERAL")
        resultado = "LATERAL"

    print(f"Primeiro Fechamento: {primeiro}")
    print(f"Último Fechamento: {ultimo}")

    mt5.shutdown()

    return resultado
