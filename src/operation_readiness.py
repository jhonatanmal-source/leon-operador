# ===================================
# OPERATION READINESS
# ===================================

from operator_status import obter_status_operadores
from pre_operation_engine import resumo_pre_operacao


MIN_PRE_OPERATION_CLOSED = 20
MIN_PRE_OPERATION_WINRATE = 70


def avaliar_prontidao_operacional():

    status = obter_status_operadores()
    operadores = status["operators"]
    pre_operacao = resumo_pre_operacao()

    motivos = []
    nivel = "BLOQUEADO"

    if operadores["alignment"]["status"] == "CONFLITO":
        motivos.append("Estrutura e setup ainda estao em conflito.")

    if operadores["collector"]["status"] != "OK":
        motivos.append("Coletor nao esta em estado OK.")

    if operadores["setup"]["status"] != "PRONTO":
        motivos.append("Setup Hunter ainda nao esta pronto.")

    if pre_operacao["fechados"] < MIN_PRE_OPERATION_CLOSED:
        motivos.append(
            "Poucas entradas simuladas fechadas "
            f"({pre_operacao['fechados']}/{MIN_PRE_OPERATION_CLOSED})."
        )

    if pre_operacao["taxa"] < MIN_PRE_OPERATION_WINRATE:
        motivos.append(
            "Taxa simulada abaixo do minimo "
            f"({pre_operacao['taxa']}%/{MIN_PRE_OPERATION_WINRATE}%)."
        )

    if not motivos:
        nivel = "LIBERADO_PARA_REVISAO"
        resumo = "LEON pode ser revisado para operacao real, ainda sem execucao automatica."
    elif pre_operacao["total"] > 0 and operadores["collector"]["status"] == "OK":
        nivel = "OBSERVACAO"
        resumo = "LEON esta aprendendo em pre-operacao, mas ainda nao esta pronto para real."
    else:
        resumo = "LEON bloqueado para operacao real."

    return {
        "nivel": nivel,
        "resumo": resumo,
        "motivos": motivos,
        "pre_operation": pre_operacao,
        "rules": {
            "min_closed": MIN_PRE_OPERATION_CLOSED,
            "min_winrate": MIN_PRE_OPERATION_WINRATE,
        },
    }
