# ===================================
# COLLECTOR OPERATOR
# ===================================

from datetime import datetime

from candle_logger import registrar_candle
from error_logger import registrar_erro
from log_engine import registrar_log
from price_logger import registrar_preco


SIMBOLO_PADRAO = "XAUUSD"


def executar_coleta_manual(simbolo=SIMBOLO_PADRAO):

    try:
        import MetaTrader5 as mt5
    except ImportError as erro:
        registrar_erro(f"COLLECTOR | MetaTrader5 nao instalado: {erro}")
        return {
            "ok": False,
            "error": "MT5_IMPORT_ERROR",
            "details": str(erro),
        }

    if not mt5.initialize():
        erro = mt5.last_error()
        registrar_erro(f"COLLECTOR | falha ao inicializar MT5: {erro}")
        return {
            "ok": False,
            "error": "MT5_INITIALIZE_FAILED",
            "details": str(erro),
        }

    try:
        mt5.symbol_select(simbolo, True)

        tick = mt5.symbol_info_tick(simbolo)
        candle = _obter_candle_m15(mt5, simbolo)

        resultado = {
            "ok": True,
            "symbol": simbolo,
            "collected_at": datetime.now().isoformat(timespec="seconds"),
            "price": None,
            "candle": None,
        }

        if tick:
            registrar_preco(
                simbolo,
                tick.bid,
                tick.ask,
            )
            resultado["price"] = {
                "bid": tick.bid,
                "ask": tick.ask,
            }
        else:
            resultado["price_error"] = "NO_TICK_DATA"

        if candle is not None:
            registrar_candle(
                simbolo,
                candle["open"],
                candle["high"],
                candle["low"],
                candle["close"],
            )
            resultado["candle"] = {
                "open": float(candle["open"]),
                "high": float(candle["high"]),
                "low": float(candle["low"]),
                "close": float(candle["close"]),
            }
        else:
            resultado["candle_error"] = "NO_CANDLE_DATA"

        if not resultado["price"] and not resultado["candle"]:
            registrar_erro("COLLECTOR | MT5 sem tick e sem candle")
            return {
                "ok": False,
                "error": "MT5_NO_MARKET_DATA",
                "details": resultado,
            }

        registrar_log("COLLECTOR | coleta manual executada")
        return resultado

    except Exception as erro:
        registrar_erro(f"COLLECTOR | falha na coleta manual: {erro}")
        return {
            "ok": False,
            "error": "COLLECTOR_MANUAL_FAILED",
            "details": str(erro),
        }

    finally:
        mt5.shutdown()


def _obter_candle_m15(mt5, simbolo):

    candles = mt5.copy_rates_from_pos(
        simbolo,
        mt5.TIMEFRAME_M15,
        0,
        1,
    )

    if candles is None or len(candles) == 0:
        return None

    return candles[0]


if __name__ == "__main__":

    print(executar_coleta_manual())
