# ===================================
# BOS ENGINE
# ===================================

def analisar_bos(df):

    print()
    print("===================================")
    print("BOS ENGINE")
    print("===================================")

    ultimo = df.iloc[-1]
    anterior = df.iloc[-2]

    if ultimo["high"] > anterior["high"]:

        resultado = "📈 ALTA"

    elif ultimo["low"] < anterior["low"]:

        resultado = "📉 BAIXA"

    else:

        resultado = "⏸ MERCADO LATERAL"

    print(f"BOS: {resultado}")

    return resultado