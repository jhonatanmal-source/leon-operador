def analisar_cerebro(
    tendencia,
    smc,
    elliott,
    score,
    qualidade,
    reputacao,
):
    print()
    print("===================================")
    print("LEON BRAIN")
    print("===================================")

    pontos = 0

    if score >= 80:
        pontos += 25

    if qualidade == "A+":
        pontos += 25

    reputacao_normalizada = str(reputacao or "").upper()
    if reputacao_normalizada in {
        "CONFIANCA ALTA",
        "CONFIANÇA ALTA",
        "CONFIANÃ‡A ALTA",
    }:
        pontos += 25
    elif reputacao_normalizada in {
        "CONFIANCA MEDIA",
        "CONFIANÇA MÉDIA",
        "CONFIANÃ‡A MÃ‰DIA",
    }:
        pontos += 15

    if smc in ["BULLISH", "BEARISH"]:
        pontos += 15
    elif smc == "MODERADO":
        pontos += 8

    if elliott in ["ONDA 3", "ONDA 5"]:
        pontos += 10

    if reputacao_normalizada in {
        "CONFIANCA BAIXA",
        "CONFIANÇA BAIXA",
        "CONFIANÃ‡A BAIXA",
    }:
        pontos = min(pontos, 60)

    print(f"BRAIN SCORE: {pontos}")
    return pontos
