from src.paths import BASE_DIR
# ===================================
# JOURNAL ENGINE
# ===================================

from datetime import datetime

def registrar_journal():

    print("===================================")
    print("JOURNAL ENGINE")
    print("===================================")

    print("LEON registrando observações...")
    print("Salvando contexto do mercado...")
    print("Armazenando aprendizado diário...")

    agora = datetime.now()

    with open(
        f"{BASE_DIR.as_posix()}/logs/journal.txt",
        "a",
        encoding="utf-8"
    ) as arquivo:

        arquivo.write(
            f"[{agora}] LEON executado com sucesso\n"
        )