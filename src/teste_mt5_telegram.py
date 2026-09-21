from mt5_engine import conectar
from mt5_engine import obter_tick
from mt5_engine import desconectar

from telegram_engine import enviar_mensagem


if conectar():

    tick = obter_tick("XAUUSD")

    mensagem = f"""
🚀 LEON XAU ELITE AI

📈 XAUUSD AO VIVO

Bid: {tick.bid}
Ask: {tick.ask}

Spread: {round(tick.ask - tick.bid, 2)}

✅ MT5 Conectado
✅ Telegram Conectado
"""

    resultado = enviar_mensagem(mensagem)

    print(resultado)

    desconectar()

else:

    print("Falha ao conectar MT5")