# ===================================
# CONFIRMATION ENGINE
# ===================================

def confirmar_setup(
    choch,
    fvg,
    liquidez
):

    if (
        choch == "CHOCH_BULLISH"
        and fvg == "FVG_BULLISH"
        and liquidez == "LIQUIDEZ_FORTE"
    ):

        return "BULLISH"

    elif (
        choch == "CHOCH_BEARISH"
        and fvg == "FVG_BEARISH"
        and liquidez == "LIQUIDEZ_FORTE"
    ):

        return "BEARISH"

    else:

        return "NEUTRO"