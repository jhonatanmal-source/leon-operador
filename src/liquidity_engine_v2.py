# ===================================
# LIQUIDITY ENGINE V2
# ===================================

def analisar_liquidez_v2(
    topo,
    fundo
):

    print()
    print("===================================")
    print("LIQUIDITY ENGINE")
    print("===================================")

    compra = topo
    venda = fundo

    print(f"BUY SIDE LIQUIDITY : {compra}")
    print(f"SELL SIDE LIQUIDITY: {venda}")

    return compra, venda