# ===================================
# MOMENTUM READER
# ===================================

import mt5linux_compat as mt5

def analisar_momentum():

    if not mt5.initialize():
        print("ERRO MT5")
        return "NEUTRO"

    simbolo = "Gold_Spot"

    mt5.symbol_select(simbolo, True)

    candles = mt5.copy_rates_from_pos(
        simbolo,
        mt5.TIMEFRAME_M15,
        0,
        10
    )

    if candles is not None:

        primeiro = candles[0]["close"]
        ultimo = candles[-1]["close"]

        diferenca = ultimo - primeiro

        print("===================================")
        print("MOMENTUM READER")
        print("===================================")

        print(f"Movimento: {diferenca:.2f}")

        if diferenca > 0:
            print("Momentum Comprador")
            resultado = "COMPRADOR"

        elif diferenca < 0:
            print("Momentum Vendedor")
            resultado = "VENDEDOR"

        else:
            print("Momentum Neutro")
            resultado = "NEUTRO"

    else:

        resultado = "NEUTRO"

    mt5.shutdown()

    return resultado
