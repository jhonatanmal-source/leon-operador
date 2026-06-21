# ===================================
# OPERATION REPORT
# ===================================

import csv
from datetime import date, datetime
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT_DIR / "data"
REPORTS_DIR = ROOT_DIR / "reports"
OPERATIONS_DIR = REPORTS_DIR / "operations"
OPERATION_DECISIONS_FILE = DATA_DIR / "operation_decisions.csv"

FIELDS = [
    "data",
    "pre_operation_id",
    "simbolo",
    "direcao",
    "preco_planejado",
    "preco_real",
    "rr_planejado",
    "rr_real",
    "brain_score",
    "classificacao",
    "decisao",
    "motivo",
    "smc",
    "elliott",
    "melhoria_sugerida",
]


def _garantir_arquivo():

    DATA_DIR.mkdir(parents=True, exist_ok=True)

    if OPERATION_DECISIONS_FILE.exists():
        return

    with OPERATION_DECISIONS_FILE.open("w", encoding="utf-8", newline="") as arquivo:
        escritor = csv.DictWriter(arquivo, fieldnames=FIELDS, delimiter=";")
        escritor.writeheader()


def _float(valor):

    try:
        if valor in [None, ""]:
            return None
        return float(valor)
    except (TypeError, ValueError):
        return None


def calcular_rr_real(direcao, preco_real, stop, take_profit):

    preco_real = _float(preco_real)
    stop = _float(stop)
    take_profit = _float(take_profit)

    if preco_real is None or stop is None or take_profit is None:
        return None

    risco = abs(preco_real - stop)
    retorno = abs(take_profit - preco_real)

    if risco <= 0:
        return 0

    if direcao == "COMPRA" and not (stop < preco_real < take_profit):
        return round(retorno / risco, 2)

    if direcao == "VENDA" and not (take_profit < preco_real < stop):
        return round(retorno / risco, 2)

    return round(retorno / risco, 2)


def _melhoria(decisao, motivo, rr_real, brain_score):

    motivo = str(motivo or "")

    if "RR" in motivo.upper() or (rr_real is not None and rr_real < 1):
        return "Aguardar uma zona em que o alvo tecnico pague ao menos o risco."

    if "ZONA" in motivo.upper() or "DRIFT" in motivo.upper():
        return "Evitar perseguir preco depois que ele saiu da zona planejada."

    if "BRAIN" in motivo.upper() or (brain_score is not None and brain_score < 70):
        return "Aguardar confluencia mais forte antes de permitir execucao demo."

    if decisao == "ENTRAR":
        return "Registrar print, resultado e contexto para revisar no fechamento."

    return "Continuar observando ate haver SMC, Elliott e risco alinhados."


def _registro_existente(pre_operation_id, decisao):

    _garantir_arquivo()

    with OPERATION_DECISIONS_FILE.open("r", encoding="utf-8", newline="") as arquivo:
        leitor = csv.DictReader(arquivo, delimiter=";")
        for registro in leitor:
            if (
                registro.get("pre_operation_id") == pre_operation_id
                and registro.get("decisao") == decisao
            ):
                return True

    return False


def registrar_relatorio_operacao(
    pre_operacao,
    decisao,
    motivo,
    preco_real=None,
    rr_real=None,
):

    if not pre_operacao:
        return {
            "ok": False,
            "error": "OPERATION_REPORT_WITHOUT_PRE_OPERATION",
        }

    pre_operation_id = pre_operacao.get("id") or "SEM_ID"

    if _registro_existente(pre_operation_id, decisao):
        return {
            "ok": False,
            "error": "OPERATION_REPORT_ALREADY_REGISTERED",
            "pre_operation_id": pre_operation_id,
            "decision": decisao,
        }

    entrada = pre_operacao.get("entrada")
    stop = pre_operacao.get("stop")
    tp = pre_operacao.get("tp2")
    direcao = pre_operacao.get("direcao")
    brain_score = _float(pre_operacao.get("brain_score"))

    if rr_real is None:
        rr_real = calcular_rr_real(direcao, preco_real, stop, tp)

    registro = {
        "data": datetime.now().isoformat(timespec="seconds"),
        "pre_operation_id": pre_operation_id,
        "simbolo": pre_operacao.get("ativo"),
        "direcao": direcao,
        "preco_planejado": entrada,
        "preco_real": "" if preco_real is None else round(float(preco_real), 2),
        "rr_planejado": pre_operacao.get("rr"),
        "rr_real": "" if rr_real is None else rr_real,
        "brain_score": pre_operacao.get("brain_score"),
        "classificacao": pre_operacao.get("status_setup"),
        "decisao": decisao,
        "motivo": motivo,
        "smc": pre_operacao.get("smc"),
        "elliott": pre_operacao.get("elliott"),
        "melhoria_sugerida": _melhoria(decisao, motivo, rr_real, brain_score),
    }

    _garantir_arquivo()
    with OPERATION_DECISIONS_FILE.open("a", encoding="utf-8", newline="") as arquivo:
        escritor = csv.DictWriter(arquivo, fieldnames=FIELDS, delimiter=";")
        escritor.writerow(registro)

    OPERATIONS_DIR.mkdir(parents=True, exist_ok=True)
    caminho = OPERATIONS_DIR / f"{pre_operation_id}_{decisao}.txt"
    caminho.write_text(_formatar_relatorio(registro), encoding="utf-8")

    return {
        "ok": True,
        "report": str(caminho),
        "record": registro,
    }


def _formatar_relatorio(registro):

    return "\n".join([
        "LEON | RELATORIO POR OPERACAO",
        "=================================",
        f"Data/hora: {registro['data']}",
        f"Pre-op: {registro['pre_operation_id']}",
        f"Simbolo: {registro['simbolo']}",
        f"Direcao planejada: {registro['direcao']}",
        f"Preco planejado: {registro['preco_planejado']}",
        f"Preco real: {registro['preco_real']}",
        f"RR planejado: {registro['rr_planejado']}",
        f"RR real: {registro['rr_real']}",
        f"Brain Score: {registro['brain_score']}",
        f"Classificacao: {registro['classificacao']}",
        f"Decisao: {registro['decisao']}",
        f"Motivo: {registro['motivo']}",
        f"Contexto SMC: {registro['smc']}",
        f"Contexto Elliott: {registro['elliott']}",
        f"Melhoria sugerida: {registro['melhoria_sugerida']}",
        "=================================",
        "",
    ])


def registros_operacao_do_dia(data=None):

    data = data or date.today()
    prefixo = data.isoformat()
    _garantir_arquivo()

    with OPERATION_DECISIONS_FILE.open("r", encoding="utf-8", newline="") as arquivo:
        return [
            registro
            for registro in csv.DictReader(arquivo, delimiter=";")
            if str(registro.get("data", "")).startswith(prefixo)
        ]
