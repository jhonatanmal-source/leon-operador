# ===================================
# ENTRY ENGINE V2
# ===================================

def definir_entrada(
    tendencia,
    momentum,
    choch=None,
    elliott=None
):

    print()
    print("===================================")
    print("ENTRY ENGINE")
    print("===================================")

    if (
        tendencia == "ALTA"
        and momentum == "COMPRADOR"
    ):

        direcao = "COMPRA"

    elif (
        tendencia == "BAIXA"
        and momentum == "VENDEDOR"
    ):

        direcao = "VENDA"

    else:

        direcao = "AGUARDAR"

    print(f"DIREÇÃO : {direcao}")

    if choch is not None:
        print(f"CHOCH    : {choch}")

    if elliott is not None:
        print(f"ELLIOTT  : {elliott}")

    return direcao