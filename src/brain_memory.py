# ===================================
# BRAIN MEMORY
# ===================================

import os

ARQUIVO = "/opt/leon/app/data/brain_memory.csv"

def registrar_brain(
    brain_score,
    confianca,
    resultado
):

    if not os.path.exists(ARQUIVO):

        with open(ARQUIVO, "w", encoding="utf-8") as f:

            f.write(
                "brain_score;confianca;resultado\n"
            )

    with open(
        ARQUIVO,
        "a",
        encoding="utf-8"
    ) as f:

        f.write(
            f"{brain_score};"
            f"{confianca};"
            f"{resultado}\n"
        )

    print("BRAIN MEMORY SALVA")