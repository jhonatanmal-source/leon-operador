# ===================================
# SETUP VALIDATOR V2
# ===================================

def validar_setup(
    choch,
    bos,
    smc,
    elliott,
    confianca
):

    print()
    print("===================================")
    print("SETUP VALIDATOR")
    print("===================================")

    pontos = 0

    print("Validando contexto...")
    print("Validando direção...")
    print("Validando liquidez...")
    print("Validando CHOCH...")
    print("Validando FVG...")
    print("Validando gerenciamento de risco...")

    if choch in ["CHOCH_BULLISH", "CHOCH_BEARISH"]:
        pontos += 1

    if bos in ["BOS_BULLISH", "BOS_BEARISH"]:
        pontos += 1

    if smc in ["BULLISH", "BEARISH"]:
        pontos += 1

    if elliott in ["ONDA 3", "ONDA 5"]:
        pontos += 1

    if confianca == "MUITO ALTA":
        pontos += 1

    alinhado = (
        (smc == "BULLISH" and bos == "BOS_BULLISH" and choch == "CHOCH_BULLISH")
        or
        (smc == "BEARISH" and bos == "BOS_BEARISH" and choch == "CHOCH_BEARISH")
    )

    if not alinhado:
        pontos = min(pontos, 2)

    print()
    print(f"PONTUAÇÃO: {pontos}/5")

    if pontos == 5:

        status = "SETUP PREMIUM"

    elif pontos >= 4:

        status = "SETUP A+"

    elif pontos >= 3:

        status = "SETUP MODERADO"

    else:

        status = "SETUP FRACO"

    print("===================================")
    print(status)
    print("===================================")

    return status
