# ===================================
# DAILY REPORT
# ===================================

from datetime import datetime

def gerar_relatorio_diario():

    agora = datetime.now()

    with open(
        "/opt/leon/app/reports/daily_report.txt",
        "a",
        encoding="utf-8"
    ) as arquivo:

        arquivo.write("\n")
        arquivo.write("=================================\n")
        arquivo.write(f"DATA: {agora}\n")
        arquivo.write("LEON EXECUTADO COM SUCESSO\n")
        arquivo.write("STATUS: OPERACIONAL\n")
        arquivo.write("=================================\n")

    print("DAILY REPORT GERADO")