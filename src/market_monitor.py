# ===================================
# MARKET MONITOR
# ===================================

import time
import mt5linux_compat as mt5
import pandas as pd

from src.bos_engine import analisar_bos
from src.telegram_engine import enviar_mensagem


ultimo_bos = None


def monitorar():

    global ultimo_bos

    if not mt5.initialize():

        print(mt5.last_error())
        return

    print("LEON MONITOR ONLINE")

    while True:

        try:

            rates = mt5.copy_rates_from_pos(
                "XAUUSD",
                mt5.TIMEFRAME_M15,
                0,
                20
            )

            df = pd.DataFrame(rates)

            resultado = analisar_bos(df)

            if resultado != ultimo_bos:

                ultimo_bos = resultado

                mensagem = f"""
🚨 LEON ALERTA

Ativo: XAUUSD
Timeframe: M15

Estrutura:
{resultado}
"""

                enviar_mensagem(mensagem)

                print("Telegram enviado")

            time.sleep(60)

        except Exception as erro:

            print("Erro:", erro)

            time.sleep(10)


if __name__ == "__main__":

    monitorar()