# ===================================
# MARKET STATE ENGINE
# ===================================

def analisar_estado_mercado():

    print("===================================")
    print("MARKET STATE ENGINE")
    print("===================================")

    estado = "MANIPULATIVO"

    print(f"Estado atual do mercado: {estado}")

    if estado == "MANIPULATIVO":
        print("LEON aumentando proteção operacional...")
        print("Mercado com comportamento perigoso...")
    elif estado == "LIMPO":
        print("Mercado saudável para execução...")
    else:
        print("Mercado em observação...")