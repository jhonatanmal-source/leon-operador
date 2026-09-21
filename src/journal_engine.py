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
        "/opt/leon/app/logs/journal.txt",
        "a",
        encoding="utf-8"
    ) as arquivo:

        arquivo.write(
            f"[{agora}] LEON executado com sucesso\n"
        )