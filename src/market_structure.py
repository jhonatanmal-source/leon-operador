# ===================================
# MARKET STRUCTURE
# ===================================

def analisar_estrutura(
    tendencia
):

    print()
    print("===================================")
    print("MARKET STRUCTURE")
    print("===================================")

    if tendencia == "ALTA":

        estrutura = "HH + HL"

    elif tendencia == "BAIXA":

        estrutura = "LH + LL"

    else:

        estrutura = "LATERAL"

    print(f"ESTRUTURA: {estrutura}")

    return estrutura