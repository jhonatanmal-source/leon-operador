# ===================================
# OPERATIONAL STUDY ENGINE
# ===================================

from datetime import datetime

from study_engine import get_study_by_topic, register_study_note


def load_operational_rules():

    return {
        "setup_a_plus": get_study_by_topic("Setup A+"),
        "checklist": get_study_by_topic("Checklist de Entrada"),
        "common_errors": get_study_by_topic("Erros Comuns"),
        "operational_rules": get_study_by_topic("Regras Operacionais"),
    }


def validate_setup_a_plus(context):

    direction = context.get("direction")
    expected_bos = (
        "BOS_BULLISH"
        if direction == "COMPRA"
        else "BOS_BEARISH"
        if direction == "VENDA"
        else None
    )
    expected_choch = (
        "CHOCH_BULLISH"
        if direction == "COMPRA"
        else "CHOCH_BEARISH"
        if direction == "VENDA"
        else None
    )
    expected_fvg = (
        "FVG_BULLISH"
        if direction == "COMPRA"
        else "FVG_BEARISH"
        if direction == "VENDA"
        else None
    )

    checks = {
        "direcao_clara": direction in ["COMPRA", "VENDA"],
        "tendencia_momentum_alinhados": context.get("trend") == context.get("momentum"),
        "liquidez_identificada": context.get("liquidity_event") in [
            "SWEEP_CONFIRMADO",
            "LIQUIDEZ_CAPTURADA",
        ],
        "estrutura_m15_confirmada": (
            context.get("bos") == expected_bos
            and context.get("choch") == expected_choch
        ),
        "fvg_do_deslocamento": context.get("fvg") == expected_fvg,
        "poi_qualificado": float(context.get("poi_score", 0)) >= 70,
        "top_down_alinhado": context.get("top_down") == "ALINHADO",
        "sessao_permitida": context.get("session") in [
            "LONDRES",
            "NY_ABERTURA",
            "NY_TARDE",
        ],
        "rr_minimo": float(context.get("rr", 0)) >= 2,
        "sem_noticia_alto_impacto": not bool(context.get("high_impact_news")),
        "nao_lateral": context.get("market_state") != "LATERAL",
    }

    approved = all(checks.values())

    return {
        "approved": approved,
        "classification": "SETUP A+" if approved else "SETUP EM ESTUDO",
        "checks": checks,
        "score": score_operational_context(context),
    }


def generate_entry_checklist(context):

    validation = validate_setup_a_plus(context)

    return {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "items": validation["checks"],
        "approved": validation["approved"],
        "classification": validation["classification"],
    }


def register_common_error(error, context):

    note = {
        "error": error,
        "context": context,
        "created_at": datetime.now().isoformat(timespec="seconds"),
    }

    return register_study_note("Erros Comuns", note)


def score_operational_context(context):

    score = 0

    if context.get("direction") in ["COMPRA", "VENDA"]:
        score += 15

    if context.get("trend") == context.get("momentum"):
        score += 20

    if context.get("liquidity_event") in [
        "SWEEP_CONFIRMADO",
        "LIQUIDEZ_CAPTURADA",
    ]:
        score += 15

    direction = context.get("direction")
    bullish_structure = (
        direction == "COMPRA"
        and context.get("bos") == "BOS_BULLISH"
        and context.get("choch") == "CHOCH_BULLISH"
        and context.get("fvg") == "FVG_BULLISH"
    )
    bearish_structure = (
        direction == "VENDA"
        and context.get("bos") == "BOS_BEARISH"
        and context.get("choch") == "CHOCH_BEARISH"
        and context.get("fvg") == "FVG_BEARISH"
    )

    if bullish_structure or bearish_structure:
        score += 25

    if float(context.get("poi_score", 0)) >= 70:
        score += 15

    if context.get("top_down") == "ALINHADO":
        score += 10

    if context.get("session") not in ["LONDRES", "NY_ABERTURA", "NY_TARDE"]:
        score -= 20

    if float(context.get("rr", 0)) >= 3:
        score += 15
    elif float(context.get("rr", 0)) >= 2:
        score += 10

    if context.get("high_impact_news"):
        score -= 25

    if context.get("market_state") == "LATERAL":
        score -= 25

    return max(0, min(100, score))
