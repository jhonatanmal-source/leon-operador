# ===================================
# CONFIDENCE ENGINE
# ===================================

def calcular_confianca(
    brain_score
):

    if brain_score >= 90:

        return "MUITO ALTA"

    elif brain_score >= 70:

        return "ALTA"

    elif brain_score >= 50:

        return "MÉDIA"

    else:

        return "BAIXA"