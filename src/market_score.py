def calcular_market_score(tendencia):
    print("===================================")
    print("MARKET SCORE")
    print("===================================")

    score = 100 if tendencia in ["ALTA", "BAIXA"] else 50

    print(f"SCORE: {score}")
    return score
