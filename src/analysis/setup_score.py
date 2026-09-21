# ===================================
# SETUP SCORE
# ===================================

def calcular_setup_score():

    print("===================================")
    print("SETUP SCORE")
    print("===================================")

    score = 92

    print(f"Qualidade do setup: {score}%")

    if score >= 90:
        print("SETUP A+ IDENTIFICADO")
    elif score >= 70:
        print("Setup aceitável...")
    else:
        print("Setup abaixo da qualidade mínima...")