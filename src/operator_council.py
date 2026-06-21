# ===================================
# OPERATOR COUNCIL
# ===================================

from operation_readiness import avaliar_prontidao_operacional
from operator_status import obter_status_operadores
from pre_operation_engine import resumo_pre_operacao
from risk_control_agent import calcular_plano_risco, resumo_risco
from top_down_agent import ultima_leitura_top_down


def _voto(nome, estado, decisao, motivo):

    return {
        "operator": nome,
        "state": estado,
        "decision": decisao,
        "reason": motivo,
    }


def avaliar_conselho_operadores():

    status = obter_status_operadores()
    operadores = status["operators"]
    pre_operacao = resumo_pre_operacao()
    prontidao = avaliar_prontidao_operacional()
    risco = resumo_risco()
    ultimo = pre_operacao.get("ultimo")
    top_down = ultima_leitura_top_down()

    votos = []

    coletor = operadores["collector"]
    if coletor["status"] == "OK":
        votos.append(_voto("Coletor", "OK", "APROVA", "Dados recentes disponíveis."))
    else:
        votos.append(_voto("Coletor", coletor["status"], "BLOQUEIA", coletor["summary"]))

    alinhamento = operadores["alignment"]
    if alinhamento["status"] == "ALINHADO":
        votos.append(_voto("Estrutura", "ALINHADO", "APROVA", alinhamento["summary"]))
    elif alinhamento["status"] == "ATENCAO":
        votos.append(_voto("Estrutura", "ATENCAO", "ALERTA", alinhamento["summary"]))
    else:
        votos.append(_voto("Estrutura", alinhamento["status"], "BLOQUEIA", alinhamento["summary"]))

    setup = operadores["setup"]
    direcao = setup.get("direcao")
    if direcao in ["COMPRA", "VENDA"]:
        votos.append(_voto("Setup Hunter", setup["status"], "APROVA", f"Direção detectada: {direcao}."))
    else:
        votos.append(_voto("Setup Hunter", setup["status"], "BLOQUEIA", "Sem direção operacional válida."))

    if top_down["alinhamento"] == "ALINHADO":
        votos.append(_voto("Top-Down", "ALINHADO", "APROVA", top_down["resumo"]))
    elif top_down["alinhamento"] == "MISTO":
        votos.append(_voto("Top-Down", "MISTO", "ALERTA", top_down["resumo"]))
    else:
        votos.append(_voto("Top-Down", top_down["alinhamento"], "BLOQUEIA", top_down["resumo"]))

    if ultimo and ultimo.get("status") == "ABERTO":
        plano_risco = calcular_plano_risco(ultimo)
        if plano_risco.get("approved"):
            votos.append(_voto("Gestor de Risco", "APROVADO", "APROVA", plano_risco["reason"]))
        else:
            votos.append(_voto("Gestor de Risco", "BLOQUEADO", "BLOQUEIA", str(plano_risco)))
    else:
        votos.append(_voto("Gestor de Risco", "AGUARDANDO", "ALERTA", "Sem pré-operação aberta para calcular lote."))

    if prontidao["nivel"] == "LIBERADO_PARA_REVISAO":
        votos.append(_voto("Professor LEON", prontidao["nivel"], "APROVA", prontidao["resumo"]))
    elif prontidao["nivel"] == "OBSERVACAO":
        votos.append(_voto("Professor LEON", prontidao["nivel"], "ALERTA", prontidao["resumo"]))
    else:
        votos.append(_voto("Professor LEON", prontidao["nivel"], "BLOQUEIA", prontidao["resumo"]))

    bloqueios = [voto for voto in votos if voto["decision"] == "BLOQUEIA"]
    alertas = [voto for voto in votos if voto["decision"] == "ALERTA"]

    if bloqueios:
        decisao = "BLOQUEADO"
        resumo = "Um ou mais operadores bloquearam a execução."
    elif alertas:
        decisao = "SOMENTE_TESTE"
        resumo = "Sem bloqueio crítico, mas ainda exige modo teste/supervisão."
    else:
        decisao = "APROVADO_PARA_REVISAO"
        resumo = "Todos os operadores aprovaram revisão humana antes de real."

    return {
        "decision": decisao,
        "summary": resumo,
        "votes": votos,
        "risk": risco,
        "top_down": top_down,
        "pre_operation": pre_operacao,
        "readiness": prontidao,
    }
