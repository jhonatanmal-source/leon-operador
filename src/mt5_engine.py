# ===================================
# MT5 ENGINE
# ===================================

import MetaTrader5 as mt5


def conectar():

    if not mt5.initialize():

        print("❌ Erro MT5:", mt5.last_error())
        return False

    return True


def obter_tick(simbolo="XAUUSD"):

    mt5.symbol_select(simbolo, True)

    return mt5.symbol_info_tick(simbolo)


def desconectar():

    mt5.shutdown()