# ===================================
# CHOCH ENGINE V2
# ===================================

def analisar_choch_v2(
    tendencia,
    bos
):

    print()
    print("===================================")
    print("CHOCH ENGINE V2")
    print("===================================")

    if tendencia == "ALTA" and bos == "BOS_BULLISH":

        resultado = "CHOCH_BULLISH"

    elif tendencia == "BAIXA" and bos == "BOS_BEARISH":

        resultado = "CHOCH_BEARISH"

    else:

        resultado = "SEM_CHOCH"

    print(f"CHOCH: {resultado}")

    return resultado