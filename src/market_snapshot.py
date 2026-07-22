# ===================================
# MARKET SNAPSHOT
# ===================================

import json
from datetime import datetime
import mt5linux_compat as mt5

def salvar_snapshot():

    if not mt5.initialize():
        print("ERRO MT5")
        return

    simbolo = "Gold_Spot"

    mt5.symbol_select(simbolo, True)

    tick = mt5.symbol_info_tick(simbolo)

    if tick:

        snapshot = {
            "data": str(datetime.now()),
            "simbolo": simbolo,
            "bid": tick.bid,
            "ask": tick.ask
        }

        with open(
            "C:/XAU_ELITE_AI/data/market_snapshot.json",
            "w",
            encoding="utf-8"
        ) as arquivo:

            json.dump(
                snapshot,
                arquivo,
                indent=4
            )

        print("SNAPSHOT SALVO")

    mt5.shutdown()