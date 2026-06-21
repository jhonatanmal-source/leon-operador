# ===================================
# MARKET CONTEXT AGENT
# ===================================

import csv
from collections import Counter, defaultdict
from datetime import datetime, time
from pathlib import Path

from operator_status import obter_status_operadores
from pre_operation_engine import resumo_pre_operacao
from risk_control_agent import calcular_plano_risco
from top_down_agent import ultima_leitura_top_down


ROOT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT_DIR / "data"
CONTEXT_MEMORY_FILE = DATA_DIR / "market_context_memory.csv"

FIELDS = [
    "data",
    "pre_operation_id",
    "sessao",
    "macro",
    "h4",
    "h1",
    "m15",
    "top_down_alinhamento",
    "tendencia",
    "momentum",
    "direcao",
    "smc",
    "elliott",
    "bos",
    "choch",
    "confianca",
    "brain_score",
    "metodo_risco",
    "risco_percentual_estimado",
    "rr",
    "status_setup",
    "resultado",
    "licao",
]


def _garantir_arquivo():

    DATA_DIR.mkdir(parents=True, exist_ok=True)

    if CONTEXT_MEMORY_FILE.exists():
        return

    with CONTEXT_MEMORY_FILE.open("w", encoding="utf-8", newline="") as arquivo:
        escritor = csv.DictWriter(arquivo, fieldnames=FIELDS, delimiter=";")
        escritor.writeheader()


def identificar_sessao(agora=None):

    agora = agora or datetime.now()
    hora = agora.time()

    if time(0, 0) <= hora < time(4, 0):
        return "ASIA"

    if time(4, 0) <= hora < time(9, 0):
        return "LONDRES"

    if time(9, 0) <= hora < time(13, 0):
        return "NY_ABERTURA"

    if time(13, 0) <= hora < time(17, 0):
        return "NY_TARDE"

    return "FORA_DAS_SESSOES"


def _ler_contextos():

    _garantir_arquivo()

    with CONTEXT_MEMORY_FILE.open("r", encoding="utf-8", newline="") as arquivo:
        return list(csv.DictReader(arquivo, delimiter=";"))


def _ja_registrado(pre_operation_id, resultado):

    for registro in _ler_contextos():
        if (
            registro.get("pre_operation_id") == pre_operation_id
            and registro.get("resultado") == resultado
        ):
            return True

    return False


def _gerar_licao(registro):

    resultado = registro["resultado"]

    if resultado.startswith("WIN"):
        return (
            f"Contexto vencedor: {registro['sessao']} | "
            f"Top-Down {registro['top_down_alinhamento']} | "
            f"{registro['direcao']} com {registro['elliott']}."
        )

    if resultado == "LOSS":
        return (
            f"Contexto perdedor: {registro['sessao']} | "
            f"Top-Down {registro['top_down_alinhamento']} | "
            f"SMC {registro['smc']} | revisar filtro."
        )

    if resultado == "INVALIDADA_GERENCIAMENTO":
        return (
            f"Plano invalidado corretamente: {registro['sessao']} | "
            f"Stop tecnico preservado | RR real nao pagou o risco | "
            f"SMC {registro['smc']} | Elliott {registro['elliott']}."
        )

    return (
        f"Contexto em estudo: {registro['sessao']} | "
        f"Top-Down {registro['top_down_alinhamento']}."
    )


def registrar_contexto_mercado():

    pre = resumo_pre_operacao()
    ultimo = pre.get("ultimo")

    if not ultimo:
        return {
            "ok": False,
            "error": "NO_PRE_OPERATION_CONTEXT",
        }

    resultado = ultimo.get("resultado", "EM_ESTUDO")

    if _ja_registrado(ultimo["id"], resultado):
        return {
            "ok": False,
            "error": "MARKET_CONTEXT_ALREADY_REGISTERED",
            "details": ultimo["id"],
        }

    status = obter_status_operadores()["operators"]
    top_down = ultima_leitura_top_down()
    setup = status["setup"]
    estrutura = status["structure"]
    plano_risco = calcular_plano_risco(ultimo) if ultimo.get("status") == "ABERTO" else {}

    registro = {
        "data": datetime.now().isoformat(timespec="seconds"),
        "pre_operation_id": ultimo.get("id"),
        "sessao": identificar_sessao(),
        "macro": top_down.get("macro_semanal"),
        "h4": top_down.get("h4_bias"),
        "h1": top_down.get("h1_contexto"),
        "m15": top_down.get("m15_gatilho"),
        "top_down_alinhamento": top_down.get("alinhamento"),
        "tendencia": estrutura.get("tendencia"),
        "momentum": "DESATIVADO",
        "direcao": ultimo.get("direcao") or setup.get("direcao"),
        "smc": ultimo.get("smc") or setup.get("smc"),
        "elliott": ultimo.get("elliott") or setup.get("elliott"),
        "bos": ultimo.get("bos"),
        "choch": ultimo.get("choch"),
        "confianca": ultimo.get("confianca") or setup.get("confianca"),
        "brain_score": ultimo.get("brain_score") or setup.get("brain_score"),
        "metodo_risco": ultimo.get("metodo_risco"),
        "risco_percentual_estimado": plano_risco.get("estimated_risk_percent", ""),
        "rr": ultimo.get("rr"),
        "status_setup": ultimo.get("status_setup"),
        "resultado": resultado,
        "licao": "",
    }
    registro["licao"] = _gerar_licao(registro)

    _garantir_arquivo()

    with CONTEXT_MEMORY_FILE.open("a", encoding="utf-8", newline="") as arquivo:
        escritor = csv.DictWriter(arquivo, fieldnames=FIELDS, delimiter=";")
        escritor.writerow(registro)

    return {
        "ok": True,
        "context": registro,
    }


def revisar_contextos():

    registros = _ler_contextos()

    if not registros:
        return {
            "total": 0,
            "summary": "Sem contextos registrados ainda.",
        }

    por_sessao = Counter(r["sessao"] for r in registros)
    por_top_down = Counter(r["top_down_alinhamento"] for r in registros)
    resultados = Counter(r["resultado"] for r in registros)
    performance = defaultdict(lambda: {"wins": 0, "losses": 0, "total": 0, "taxa": 0})

    for registro in registros:
        chave = f"{registro['sessao']} | {registro['top_down_alinhamento']} | {registro['direcao']}"
        resultado = registro["resultado"]

        if resultado == "SEM_ENTRADA":
            continue

        performance[chave]["total"] += 1

        if resultado.startswith("WIN"):
            performance[chave]["wins"] += 1

        if resultado == "LOSS":
            performance[chave]["losses"] += 1

    for dados in performance.values():
        if dados["total"]:
            dados["taxa"] = round((dados["wins"] / dados["total"]) * 100, 2)

    melhores = sorted(
        performance.items(),
        key=lambda item: (item[1]["taxa"], item[1]["total"]),
        reverse=True,
    )[:5]

    return {
        "total": len(registros),
        "sessions": dict(por_sessao),
        "top_down": dict(por_top_down),
        "results": dict(resultados),
        "best_contexts": [
            {"context": contexto, **dados}
            for contexto, dados in melhores
        ],
        "last_lesson": registros[-1].get("licao"),
        "summary": "Contextos de mercado revisados.",
    }
