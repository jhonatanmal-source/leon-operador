# ===================================
# DIRECTION ENGINE
# ===================================

def analisar_direcao():

    print("===================================")
    print("DIRECTION ENGINE")
    print("===================================")

    contexto = "BUY"

    print(f"Direção operacional atual: {contexto}")

    if contexto == "BUY":
        print("LEON buscando oportunidades de COMPRA...")
    else:
        print("LEON buscando oportunidades de VENDA...")