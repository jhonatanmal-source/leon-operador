from asset_detector import detectar_ativo
from datetime import datetime


def _rates_to_candles(rates):
    if rates is None:
        return []

    candles = []
    for rate in rates:
        candles.append({
            "time": datetime.fromtimestamp(int(rate["time"])).isoformat(),
            "open": float(rate["open"]),
            "high": float(rate["high"]),
            "low": float(rate["low"]),
            "close": float(rate["close"]),
        })
    return candles


def load_execution_candles(
    symbol="XAUUSD",
    m15_count=160,
    m5_count=180,
    h1_count=240,
    h4_count=180,
):
    try:
        import mt5_safe as mt5
    except ImportError:
        return {"ok": False, "error": "MT5_IMPORT_ERROR"}

    initialized_here = False
    try:
        if not mt5.initialize():
            return {
                "ok": False,
                "error": "MT5_INITIALIZE_FAILED",
                "details": str(mt5.last_error()),
            }
        initialized_here = True
        mt5.symbol_select(symbol, True)

        m15 = _rates_to_candles(
            mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_M15, 0, m15_count)
        )
        m5 = _rates_to_candles(
            mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_M5, 0, m5_count)
        )
        h1 = _rates_to_candles(
            mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_H1, 0, h1_count)
        )
        h4 = _rates_to_candles(
            mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_H4, 0, h4_count)
        )

        if len(m15) < 20 or len(m5) < 20 or len(h1) < 20 or len(h4) < 20:
            return {
                "ok": False,
                "error": "INSUFFICIENT_EXECUTION_CANDLES",
                "m15": len(m15),
                "m5": len(m5),
                "h1": len(h1),
                "h4": len(h4),
            }

        return {
            "ok": True,
            "m15": m15,
            "m5": m5,
            "h1": h1,
            "h4": h4,
        }
    except Exception as error:
        return {
            "ok": False,
            "error": "MT5_EXECUTION_CANDLES_FAILED",
            "details": str(error),
        }
    finally:
        if initialized_here:
            mt5.shutdown()


def _micro_trigger(candles, direction):
    """Gatilho M5 de RETESTE/SWEEP+RECLAIM (anti viés comprar topo / vender fundo).

    A confirmacao NAO pode ocorrer por rompimento de estrutura (structure_break).
    Para COMPRA: exige varredura de liquidez abaixo do low recente (sweep),
    fechamento acima do low varrido (reclaim) e corpo favoravel, sem romper o
    high recente (nao perseguir o preco para cima).
    Para VENDA: espelho — sweep acima do high recente, reclaim abaixo, sem
    romper o low recente.

    Retorna o mesmo contrato de antes (confirmed, structure_break, reaction,
    displacement, trigger_price, trigger_time, reason) e adiciona campos de
    observabilidade (sweep, reclaim, swing_low, swing_high) sem quebrar
    consumidores existentes.
    """
    closed = candles[:-1] if len(candles) > 1 else candles
    if len(closed) < 5:
        return {"confirmed": False, "reason": "M5_SEM_CANDLES_FECHADOS"}

    current = closed[-1]
    recent = closed[-5:-1]
    swing_high = max(candle["high"] for candle in recent)
    swing_low = min(candle["low"] for candle in recent)
    body = abs(current["close"] - current["open"])
    range_size = current["high"] - current["low"]
    displacement = range_size > 0 and body / range_size >= 0.55

    if direction == "COMPRA":
        swept = current["low"] < swing_low
        reclaimed = current["close"] > swing_low
        reaction = reclaimed and current["close"] > current["open"]
        structure_break = current["close"] > swing_high
    else:
        swept = current["high"] > swing_high
        reclaimed = current["close"] < swing_high
        reaction = reclaimed and current["close"] < current["open"]
        structure_break = current["close"] < swing_low

    confirmed = swept and reaction and displacement and not structure_break
    return {
        "confirmed": confirmed,
        "structure_break": structure_break,
        "reaction": reaction,
        "displacement": displacement,
        "sweep": swept,
        "reclaim": reclaimed,
        "swing_low": swing_low,
        "swing_high": swing_high,
        "trigger_price": current["close"],
        "trigger_time": current["time"],
        "reason": "M5_RETESTE_SWEEP_RECLAIM_CONFIRMADO" if confirmed else "M5_AGUARDANDO_RETESTE",
    }


def refine_m15_m5(direction, symbol="XAUUSD"):
    market = load_execution_candles(symbol)
    if not market.get("ok"):
        return market

    trigger = _micro_trigger(market["m5"], direction)
    return {
        "ok": True,
        "m15": market["m15"],
        "m5": market["m5"],
        "trigger": trigger,
    }
