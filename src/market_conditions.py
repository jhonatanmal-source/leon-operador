# ===================================
# MARKET CONDITIONS
# ===================================

def analisar_condicoes():

    print("===================================")
    print("MARKET CONDITIONS")
    print("===================================")

    condicao = "VOLÁTIL"

    print(f"Condição atual do mercado: {condicao}")

    if condicao == "VOLÁTIL":
        print("LEON aumentando cautela operacional...")
    elif condicao == "LATERAL":
        print("Mercado lateralizado...")
    else:
        print("Mercado saudável para operações...")