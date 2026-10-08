from src.paths import BASE_DIR
from datetime import datetime
from pathlib import Path

def registrar_erro(erro):

    linha = f"{datetime.now()} | {erro}\n"
    caminhos = [
        Path(f"{BASE_DIR.as_posix()}/logs/errors.txt"),
        Path(f"{BASE_DIR.as_posix()}/logs/errors_fallback.txt"),
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
