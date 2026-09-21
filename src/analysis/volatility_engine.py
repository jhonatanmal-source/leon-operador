# ===================================
# VOLATILITY ENGINE
# ===================================

def analisar_volatilidade():

    print("===================================")
    print("VOLATILITY ENGINE")
    print("===================================")

    volatilidade = "ALTA"

    print(f"Volatilidade atual: {volatilidade}")

    if volatilidade == "ALTA":
        print("LEON aumentando cautela...")
        print("Stops podem precisar de ajuste...")
    elif volatilidade == "BAIXA":
        print("Mercado mais lento...")
    else:
        print("Volatilidade saudável para operação...")