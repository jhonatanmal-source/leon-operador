import MetaTrader5 as mt5

from candle_engine import obter_candles


if mt5.initialize():

    df = obter_candles()

    print("\n===================================")
    print("LEON CANDLE TEST")
    print("===================================\n")

    print(df.tail())

    mt5.shutdown()

else:

    print(mt5.last_error())