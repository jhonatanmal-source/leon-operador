# ===================================
# SMC STUDY ENGINE
# ===================================


def _candles(market_data):

    if not isinstance(market_data, dict):
        return []

    candles = market_data.get("candles") or []

    return candles if isinstance(candles, list) else []


def _insufficient(message):

    return {
        "ok": False,
        "message": message,
        "status": "aguardando_dados",
    }


def study_liquidity(market_data):

    candles = _candles(market_data)

    if len(candles) < 5:
        return _insufficient("Dados insuficientes para validar liquidez.")

    highs = [c.get("high") for c in candles[-5:] if c.get("high") is not None]
    lows = [c.get("low") for c in candles[-5:] if c.get("low") is not None]

    return {
        "ok": True,
        "message": "Estudo de liquidez registrado.",
        "previous_high": max(highs) if highs else None,
        "previous_low": min(lows) if lows else None,
        "what_to_watch": "Aguardar varredura e reação antes de considerar entrada.",
    }


def study_bos(market_data):

    candles = _candles(market_data)

    if len(candles) < 3:
        return _insufficient("Estudo registrado, aguardando mais candles para BOS.")

    last = candles[-1]
    previous = candles[-2]

    if last.get("high", 0) > previous.get("high", 0):
        bos = "possivel_bos_bullish"
    elif last.get("low", 0) < previous.get("low", 0):
        bos = "possivel_bos_bearish"
    else:
        bos = "sem_bos_claro"

    return {
        "ok": True,
        "message": "BOS estudado com cautela.",
        "context": bos,
        "warning": "BOS precisa de candle forte e contexto, não é entrada isolada.",
    }


def study_choch(market_data):

    candles = _candles(market_data)

    if len(candles) < 4:
        return _insufficient("Estudo registrado, aguardando mais candles para CHOCH.")

    return {
        "ok": True,
        "message": "CHOCH deve ser tratado como possível mudança de caráter.",
        "context": "Nunca afirmar reversão sem liquidez, FVG ou OB.",
    }


def study_fvg(market_data):

    candles = _candles(market_data)

    if len(candles) < 3:
        return _insufficient("Estudo registrado, aguardando mais candles para FVG.")

    return {
        "ok": True,
        "message": "FVG estudado como zona de interesse.",
        "context": "Validar se houve deslocamento forte antes de usar o FVG.",
    }


def study_order_block(market_data):

    candles = _candles(market_data)

    if len(candles) < 5:
        return _insufficient("Estudo registrado, aguardando mais candles para Order Block.")

    return {
        "ok": True,
        "message": "Order Block deve estar ligado a deslocamento, BOS/CHOCH ou liquidez.",
        "context": "OB sem reação ou muito antigo deve ter peso menor.",
    }


def analyze_smc_context(market_data):

    return {
        "liquidity": study_liquidity(market_data),
        "bos": study_bos(market_data),
        "choch": study_choch(market_data),
        "fvg": study_fvg(market_data),
        "order_block": study_order_block(market_data),
    }
