# ===================================
# SIGNAL ENGINE
# ===================================

def gerar_sinal(score):

    print("===================================")
    print("SIGNAL ENGINE")
    print("===================================")

    if score >= 80:

        sinal = "POSSÍVEL SETUP"

    elif score >= 50:

        sinal = "OBSERVAR"

    else:

        sinal = "SEM OPERAÇÃO"

    print(f"SINAL: {sinal}")

    return sinal