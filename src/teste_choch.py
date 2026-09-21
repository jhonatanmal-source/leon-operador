# ===================================
# CHOCH ENGINE
# ===================================

def analisar_choch(
    tendencia,
    bos_atual
):

    if (
        tendencia == "ALTA"
        and
        bos_atual == "BOS_BEARISH"
    ):

        return "CHOCH_BEARISH"

    elif (
        tendencia == "BAIXA"
        and
        bos_atual == "BOS_BULLISH"
    ):

        return "CHOCH_BULLISH"

    return "SEM_CHOCH"