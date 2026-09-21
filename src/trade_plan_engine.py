# ===================================
# TRADE PLAN ENGINE
# ===================================

def gerar_trade_plan(
    ativo,
    direcao,
    confianca,
    smc,
    elliott,
    brain_score
):

    print()
    print("===================================")
    print("TRADE PLAN")
    print("===================================")

    print(f"ATIVO      : {ativo}")
    print(f"DIREÇÃO    : {direcao}")
    print(f"CONFIANÇA  : {confianca}")
    print(f"SMC        : {smc}")
    print(f"ELLIOTT    : {elliott}")
    print(f"BRAIN SCORE: {brain_score}")

    print()
    print("JUSTIFICATIVA")

    print(f"✓ {smc}")
    print(f"✓ {elliott}")
    print(f"✓ Confiança {confianca}")
    print(f"✓ Brain Score {brain_score}")

    return True