# mt5_candles.py

import MetaTrader5 as mt5
import pandas as pd

if mt5.initialize():

    rates = mt5.copy_rates_from_pos(
        "XAUUSD",
        mt5.TIMEFRAME_M15,
        0,
        100
    )

    df = pd.DataFrame(rates)

    print(df.tail())

    mt5.shutdown()