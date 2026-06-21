# ===================================
# ELLIOTT STUDY ENGINE
# ===================================


def _candles(market_data):

    if not isinstance(market_data, dict):
        return []

    candles = market_data.get("candles") or []

    return candles if isinstance(candles, list) else []


def validate_impulse_points(points, direction):

    if not isinstance(points, (list, tuple)) or len(points) != 6:
        return {
            "valid": False,
            "reason": "IMPULSE_REQUIRES_SIX_PIVOTS",
        }

    try:
        p0, p1, p2, p3, p4, p5 = [float(point) for point in points]
    except (TypeError, ValueError):
        return {
            "valid": False,
            "reason": "INVALID_IMPULSE_POINTS",
        }

    if direction == "ALTA":
        checks = {
            "wave_2_preserves_origin": p2 > p0,
            "wave_3_breaks_wave_1": p3 > p1,
            "wave_4_no_overlap": p4 > p1,
            "wave_5_directional": p5 > p4,
        }
        lengths = [p1 - p0, p3 - p2, p5 - p4]
    elif direction == "BAIXA":
        checks = {
            "wave_2_preserves_origin": p2 < p0,
            "wave_3_breaks_wave_1": p3 < p1,
            "wave_4_no_overlap": p4 < p1,
            "wave_5_directional": p5 < p4,
        }
        lengths = [p0 - p1, p2 - p3, p4 - p5]
    else:
        return {
            "valid": False,
            "reason": "INVALID_IMPULSE_DIRECTION",
        }

    checks["wave_3_not_shortest"] = lengths[1] >= min(lengths[0], lengths[2])
    failed = [name for name, passed in checks.items() if not passed]

    return {
        "valid": not failed,
        "reason": "VALID_IMPULSE" if not failed else "IMPULSE_RULE_FAILED",
        "checks": checks,
        "failed": failed,
        "motive_lengths": lengths,
    }


def score_elliott_smc_confluence(context):

    score = 0
    reasons = []

    if context.get("wave_rules_valid"):
        score += 25
    else:
        reasons.append("CONTAGEM_SEM_REGRAS_VALIDAS")

    if context.get("invalidation_defined"):
        score += 15
    else:
        reasons.append("SEM_NIVEL_DE_INVALIDACAO")

    if context.get("alternative_count"):
        score += 10

    if context.get("smc_confirmed"):
        score += 30
    else:
        reasons.append("SMC_NAO_CONFIRMADO")

    if context.get("m15_confirmed"):
        score += 20
    else:
        reasons.append("M15_NAO_CONFIRMADO")

    approved = score >= 80 and not reasons
    return {
        "approved": approved,
        "score": score,
        "reasons": reasons,
        "policy": "ELLIOTT_CONTEXT_ONLY" if not approved else "CONFLUENCE_CONFIRMED",
    }


def estimate_wave_context(market_data):

    candles = _candles(market_data)

    if len(candles) < 5:
        return {
            "ok": False,
            "message": "Sem clareza de onda",
            "warning": "Nunca afirmar onda com certeza sem confirmação",
        }

    first_close = candles[0].get("close")
    last_close = candles[-1].get("close")

    if first_close is None or last_close is None:
        return {
            "ok": False,
            "message": "Sem clareza de onda",
            "warning": "Nunca afirmar onda com certeza sem confirmação",
        }

    if abs(last_close - first_close) > 0:
        return {
            "ok": True,
            "message": "Possível contexto impulsivo",
            "warning": "Contexto provável, não confirmação absoluta.",
        }

    return {
        "ok": True,
        "message": "Sem clareza de onda",
        "warning": "Nunca afirmar onda com certeza sem confirmação",
    }


def study_impulse(market_data):

    context = estimate_wave_context(market_data)

    if not context["ok"]:
        return context

    return {
        "ok": True,
        "message": "Possível contexto impulsivo",
        "rules": [
            "Observar se há deslocamento forte.",
            "Onda 3 provável precisa de força e continuação.",
            "Evitar compra/venda após movimento já esticado sem pullback.",
        ],
    }


def study_abc_correction(market_data):

    candles = _candles(market_data)

    if len(candles) < 6:
        return {
            "ok": False,
            "message": "Sem clareza de onda",
            "warning": "Aguardando mais candles para possível correção ABC.",
        }

    return {
        "ok": True,
        "message": "Possível correção ABC",
        "warning": "ABC deve ser validado próximo de zonas SMC, não isoladamente.",
    }


def study_elliott_context(market_data):

    return {
        "wave_context": estimate_wave_context(market_data),
        "impulse": study_impulse(market_data),
        "abc_correction": study_abc_correction(market_data),
        "core_warning": "Nunca afirmar onda com certeza sem confirmação",
    }
