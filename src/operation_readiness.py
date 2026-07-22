from src.operator_status import obter_status_operadores
from src.pre_operation_engine import resumo_pre_operacao
from src.learning_bootstrap import modo_bootstrap_ativo, obter_limiares

MIN_PRE_OPERATION_CLOSED = 20
MIN_PRE_OPERATION_WINRATE = 70


def avaliar_prontidao_operacional():

    status = obter_status_operadores()
    operadores = status["operators"]
    pre_operacao = resumo_pre_operacao()

    bootstrap = modo_bootstrap_ativo()
    limiares = obter_limiares() if bootstrap else {}

    min_closed = limiares.get("min_pre_operation_closed", MIN_PRE_OPERATION_CLOSED) if bootstrap else MIN_PRE_OPERATION_CLOSED
    min_winrate = limiares.get("min_pre_operation_winrate", MIN_PRE_OPERATION_WINRATE) if bootstrap else MIN_PRE_OPERATION_WINRATE

    motivos = []
    if bootstrap:
        nivel = "APRENDIZADO"
    else:
        nivel = "BLOQUEADO"

    if operadores["alignment"]["status"] == "CONFLITO":
        motivos.append("Estrutura e setup ainda estao em conflito.")

    if operadores["collector"]["status"] != "OK":
        motivos.append("Coletor nao esta em estado OK.")

    if operadores["setup"]["status"] != "PRONTO":
        motivos.append("Setup Hunter ainda nao esta pronto.")

    if pre_operacao["fechados"] < min_closed:
        motivos.append(
            "Poucas entradas simuladas fechadas "
            f"({pre_operacao['fechados']}/{min_closed})."
        )

    if pre_operacao["taxa"] < min_winrate:
        motivos.append(
            "Taxa simulada abaixo do minimo "
            f"({pre_operacao['taxa']}%/{min_winrate}%)."
        )

    if not motivos and pre_operacao["fechados"] >= MIN_PRE_OPERATION_CLOSED and pre_operacao["taxa"] >= MIN_PRE_OPERATION_WINRATE:
        nivel = "LIBERADO_PARA_REVISAO"
        resumo = "LEON pode ser revisado para operacao real, ainda sem execucao automatica."
    elif not motivos and bootstrap:
        nivel = "APRENDIZADO"
        resumo = f"LEON em bootstrap ({pre_operacao['fechados']} fechados, {pre_operacao['taxa']}% winrate)."
    elif pre_operacao["total"] > 0 and operadores["collector"]["status"] == "OK":
        if bootstrap:
            nivel = "APRENDIZADO"
        else:
            nivel = "OBSERVACAO"
        resumo = "LEON esta aprendendo em pre-operacao, mas ainda nao esta pronto para real."
    else:
        resumo = "LEON bloqueado para operacao real."

    return {
        "nivel": nivel,
        "resumo": resumo,
        "motivos": motivos,
        "pre_operation": pre_operacao,
        "bootstrap": bootstrap,
        "rules": {
            "min_closed": min_closed,
            "min_winrate": min_winrate,
            "target_closed": MIN_PRE_OPERATION_CLOSED,
            "target_winrate": MIN_PRE_OPERATION_WINRATE,
        },
    }
