# ===================================
# LOG ENGINE
# ===================================

from datetime import datetime
from pathlib import Path

def registrar_log(mensagem):

    agora = datetime.now()
    linha = f"[{agora}] {mensagem}\n"
    caminhos = [
        Path("C:/XAU_ELITE_AI/logs/leon_log.txt"),
        Path("C:/XAU_ELITE_AI/logs/leon_log_fallback.txt"),
    ]

    for caminho in caminhos:
        try:
            caminho.parent.mkdir(parents=True, exist_ok=True)
            with caminho.open("a", encoding="utf-8") as arquivo:
                arquivo.write(linha)
            return True
        except PermissionError:
            continue

    return False
