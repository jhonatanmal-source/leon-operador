# ===================================
# SCREENSHOT ENGINE
# ===================================

from datetime import datetime
import os

PASTA = "/opt/leon/app/screenshots"

def registrar_screenshot():

    print()
    print("===================================")
    print("SCREENSHOT ENGINE")
    print("===================================")

    if not os.path.exists(PASTA):

        os.makedirs(PASTA)

    nome = datetime.now().strftime(
        "setup_%Y%m%d_%H%M%S.png"
    )

    caminho = os.path.join(
        PASTA,
        nome
    )

    print(f"ARQUIVO: {caminho}")

    print("PRONTO PARA CAPTURA")

    return caminho