# ===================================
# EVOLUTION REPORT
# ===================================

from datetime import datetime

def gerar_relatorio_evolucao():

    with open(
        "C:/XAU_ELITE_AI/reports/EVOLUTION_REPORT.txt",
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

    print("RELATÓRIO GERADO")