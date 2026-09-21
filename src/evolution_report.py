# ===================================
# EVOLUTION REPORT
# ===================================

from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
REPORTS_DIR = BASE_DIR / "reports"

def gerar_relatorio_evolucao():
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    caminho = REPORTS_DIR / "EVOLUTION_REPORT.txt"

    with open(
        caminho,
        "w",
        encoding="utf-8"
    ) as arquivo:

        arquivo.write(
            "===================================\n"
        )

        arquivo.write(
            "LEON EVOLUTION REPORT\n"
        )

        arquivo.write(
            "===================================\n\n"
        )

        arquivo.write(
            f"DATA: {datetime.now()}\n\n"
        )

        arquivo.write(
            "STATUS: ESTUDO NOTURNO EXECUTADO\n"
        )

    print(f"RELATÓRIO GERADO: {caminho}")