# ===================================
# MT5 ENGINE
# ===================================

import mt5_safe as mt5
from asset_detector import detectar_ativo


def conectar():

    if not mt5.initialize():

        print("Erro MT5:", mt5.last_error())
        return False

    return True


def obter_tick(simbolo=None):

    if simbolo is None:
        simbolo = detectar_ativo()

    mt5.symbol_select(simbolo, True)

    return mt5.symbol_info_tick(simbolo)


def desconectar():

    mt5.shutdown()
