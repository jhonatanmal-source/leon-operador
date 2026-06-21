# ===================================
# LEON NIGHT LEARNING V2
# ===================================

import time
from datetime import datetime

from market_reader import ler_preco_xau
from candle_reader import ler_candle_h1

from memory_analyzer import analisar_memoria
from memory_rank import analisar_rank

from brain_analyzer import analisar_brain
from brain_evolution import evoluir_cerebro

print()
print("===================================")
print("LEON NIGHT LEARNING V2")
print("===================================")

ciclos = 40

for ciclo in range(ciclos):

    print()
    print("===================================")
    print(f"CICLO #{ciclo+1}")
    print(datetime.now())
    print("===================================")

    # ===================================
    # COLETA NOVOS DADOS
    # ===================================

    ler_preco_xau()

    ler_candle_h1()

    # ===================================
    # ESTUDO
    # ===================================

    analisar_memoria()

    analisar_rank()

    analisar_brain()

    evoluir_cerebro()

    print()
    print("PRÓXIMA COLETA EM 15 MINUTOS...")
    print()

    time.sleep(900)

print()
print("===================================")
print("ESTUDO NOTURNO FINALIZADO")
print("===================================")