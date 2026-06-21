# ===================================
# ALERT ENGINE
# ===================================

def gerar_alerta(
    status_setup,
    confianca,
    direcao
):

    print()
    print("===================================")
    print("ALERT ENGINE")
    print("===================================")

    if (
        status_setup == "SETUP PREMIUM"
        and confianca == "MUITO ALTA"
    ):

        alerta = True

        print("🚨 ALERTA GERADO")

    else:

        alerta = False

        print("ALERTA BLOQUEADO")

    print(f"DIREÇÃO: {direcao}")

    return alerta