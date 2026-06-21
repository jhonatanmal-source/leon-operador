import time

from market_reader import ler_preco_xau
from candle_reader import ler_candle_h1

print("===================================")
print("LEON NIGHT COLLECTOR")
print("===================================")

while True:

    try:

        ler_preco_xau()
        ler_candle_h1()

        print("Dados coletados com sucesso.")

    except Exception as erro:

        print(f"ERRO: {erro}")

    time.sleep(900)  # 15 minutos