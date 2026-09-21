# ===================================
# CONFIDENCE ENGINE
# ===================================

import json
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parent.parent
RECOMMENDATIONS_FILE = ROOT_DIR / "data" / "confidence_recommendations.json"


def _load_recommendations():
    if not RECOMMENDATIONS_FILE.exists():
        return []
    try:
        return json.loads(RECOMMENDATIONS_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []


def _net_adjustments():
    """Aggregate applied recommendations into net adjustment per dimension=value."""
    recs = _load_recommendations()
    adj = {}
    for rec in recs:
        if not rec.get("applied_automatically"):
            continue
        key = f"{rec['dimension']}={rec['value']}"
        adj[key] = adj.get(key, 0) + rec.get("suggested_adjustment", 0)
    return adj


def calcular_confianca(brain_score):

    if brain_score >= 90:

        return "MUITO ALTA"

    elif brain_score >= 70:

        return "ALTA"

    elif brain_score >= 50:

        return "MÉDIA"

    else:

        return "BAIXA"


def calcular_confianca_ajustada(brain_score, **contexto):
    """
    Aplica ajustes de confiança acumulados do batch review.

    Uso:
        confianca = calcular_confianca_ajustada(
            brain_score,
            direcao="COMPRA",
            smc="NEUTRO",
            elliott="ONDA 5 CONCLUIDA",
            setup="SETUP FRACO",
        )
    """
    ajustes = _net_adjustments()
    net = 0

    for dim, val in sorted(contexto.items()):
        if val is not None:
            key = f"{dim}={val}"
            net += ajustes.get(key, 0)

    if net != 0:
        brain_score_ajustado = max(0, min(100, brain_score + net))
    else:
        brain_score_ajustado = brain_score

    return brain_score_ajustado, calcular_confianca(brain_score_ajustado)