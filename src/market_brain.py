# ===================================
# MARKET BRAIN
# ===================================

def analisar_cenario(
    tendencia,
    momentum
):

    print("===================================")
    print("MARKET BRAIN")
    print("===================================")

    print(f"Tendência: {tendencia}")
    print(f"Momentum: {momentum}")

    if tendencia == "ALTA" and momentum == "COMPRADOR":

        print("OPINIÃO:")
        print("Cenário favorável para compras.")

    elif tendencia == "BAIXA" and momentum == "VENDEDOR":

        print("OPINIÃO:")
        print("Cenário favorável para vendas.")

    else:

        print("OPINIÃO:")
        print("Mercado sem alinhamento.")