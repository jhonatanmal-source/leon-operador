from src.paths import BASE_DIR
# ===================================
# BOOT COUNTER
# ===================================

import os

ARQUIVO = f"{BASE_DIR.as_posix()}/data/boot_count.txt"

def contar_inicializacao():

    if not os.path.exists(ARQUIVO):

        with open(ARQUIVO, "w") as f:
            f.write("0")

    with open(ARQUIVO, "r") as f:
        contador = int(f.read())

    contador += 1

    with open(ARQUIVO, "w") as f:
        f.write(str(contador))

    print(f"LEON iniciado {contador} vezes")