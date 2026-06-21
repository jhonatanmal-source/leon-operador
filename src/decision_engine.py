# ===================================
# DECISION ENGINE
# ===================================

def tomar_decisao():

    print("===================================")
    print("DECISION ENGINE")
    print("===================================")

    decisao = "AGUARDAR"

    print(f"Decisão operacional: {decisao}")

    if decisao == "COMPRAR":
        print("LEON autorizou operação de COMPRA...")
    elif decisao == "VENDER":
        print("LEON autorizou operação de VENDA...")
    else:
        print("LEON decidiu aguardar melhor contexto...")