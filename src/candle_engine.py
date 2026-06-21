# ===================================
# CANDLE ENGINE
# ===================================

import MetaTrader5 as mt5
import pandas as pd


def obter_candles(
    simbolo="XAUUSD",
    timeframe=mt5.TIMEFRAME_M15,
    quantidade=100
):

    rates = mt5.copy_rates_from_pos(
        simbolo,
        timeframe,
        0,
        quantidade
    )

    if rates is None:
        return None

    df = pd.DataFrame(rates)

    df["time"] = pd.to_datetime(
        df["time"],
        unit="s"
    )

    return df