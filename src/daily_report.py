from src.paths import BASE_DIR
# ===================================
# DAILY REPORT
# ===================================

from datetime import datetime

def gerar_relatorio_diario():

    agora = datetime.now()

    with open(
        f"{BASE_DIR.as_posix()}/reports/daily_report.txt",
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