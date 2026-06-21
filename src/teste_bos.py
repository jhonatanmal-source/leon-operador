import MetaTrader5 as mt5
import pandas as pd

from bos_engine import analisar_bos
from telegram_engine import enviar_mensagem

if not mt5.initialize():

    print(mt5.last_error())

else:

    rates = mt5.copy_rates_from_pos(
        "XAUUSD",
        mt5.TIMEFRAME_M15,
        0,
        20
    )

    df = pd.DataFrame(rates)

    resultado = analisar_bos(df)

    if resultado != "SEM_BOS":

        mensagem = f"""
🚨 LEON ALERTA

Ativo: XAUUSD
Timeframe: M15

Estrutura:
{resultado}
"""

        enviar_mensagem(mensagem)

    mt5.shutdown()