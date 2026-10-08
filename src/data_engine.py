from src.paths import BASE_DIR
# ===================================
# DATA ENGINE
# ===================================

import json
from datetime import datetime

def salvar_execucao():

    dados = {
        "data": str(datetime.now()),
        "status": "ONLINE",
        "mercado": "XAUUSD",
        "versao": "0.1"
    }

    with open(
        f"{BASE_DIR.as_posix()}/data/leon_data.json",
        "a",
        encoding="utf-8"
    ) as arquivo:

        arquivo.write(json.dumps(dados))
        arquivo.write("\n")

    print("DADOS SALVOS")