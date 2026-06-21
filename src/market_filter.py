# ===================================
# MARKET FILTER
# ===================================

def validar_cenario(
    tendencia,
    momentum
):

    if tendencia == "LATERAL":
        return False

    if momentum == "NEUTRO":
        return False

    return True