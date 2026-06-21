def analisar_fvg(
    tendencia,
    momentum
):

    if tendencia == "ALTA" and momentum == "COMPRADOR":
        return "FVG_BULLISH"

    elif tendencia == "BAIXA" and momentum == "VENDEDOR":
        return "FVG_BEARISH"

    return "SEM_FVG"