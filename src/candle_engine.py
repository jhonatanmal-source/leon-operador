# ===================================
# CANDLE ENGINE
# ===================================

import mt5linux_compat as mt5
import pandas as pd


def obter_candles(
    simbolo="Gold_Spot",
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