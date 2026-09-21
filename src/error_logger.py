from datetime import datetime
from pathlib import Path

def registrar_erro(erro):

    linha = f"{datetime.now()} | {erro}\n"
    caminhos = [
        Path("/opt/leon/app/logs/errors.txt"),
        Path("/opt/leon/app/logs/errors_fallback.txt"),
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
