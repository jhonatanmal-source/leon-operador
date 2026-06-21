VALID_DIRECTIONS = {"ALTA", "BAIXA"}


def _trade_bias(direction):
    if direction == "COMPRA":
        return "ALTA"
    if direction == "VENDA":
        return "BAIXA"
    return None


def evaluate_timeframe_policy(top_down, trade_direction):
    candidate = _trade_bias(trade_direction)
    macro = top_down.get("macro_semanal")
    h4 = top_down.get("h4_bias")
    h1 = top_down.get("h1_contexto")
    m15 = top_down.get("m15_gatilho")
    tactical = [h4, h1, m15]
    tactical_aligned = (
        candidate in VALID_DIRECTIONS
        and all(reading == candidate for reading in tactical)
    )

    if tactical_aligned and macro == candidate:
        return {
            "approved": True,
            "mode": "TENDENCIA",
            "risk_factor": 1.0,
            "reason": "MACRO_E_TIMEFRAMES_ALINHADOS",
        }

    if (
        tactical_aligned
        and macro in VALID_DIRECTIONS
        and macro != candidate
    ):
        return {
            "approved": True,
            "mode": "CORRECAO",
            "risk_factor": 0.5,
            "reason": "H4_H1_M15_CONFIRMAM_CORRECAO_DO_MACRO",
        }

    return {
        "approved": False,
        "mode": "BLOQUEADO",
        "risk_factor": 0,
        "reason": "H4_H1_M15_SEM_ALINHAMENTO_TATICO",
    }
