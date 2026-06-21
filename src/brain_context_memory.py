# ===================================
# BRAIN CONTEXT MEMORY
# ===================================

import csv
from datetime import datetime
from pathlib import Path

from operator_status import obter_status_operadores


ROOT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT_DIR / "data"
ARQUIVO = DATA_DIR / "brain_context_memory.csv"

CAMPOS = [
    "data",
    "origem",
    "tipo",
    "collector_status",
    "preco",
    "tendencia",
    "momentum",
    "sinal",
    "direcao",
    "smc",
    "elliott",
    "confianca",
    "brain_score",
    "alinhamento",
    "observacao",
]


def _garantir_arquivo():

    DATA_DIR.mkdir(parents=True, exist_ok=True)

    if ARQUIVO.exists():
        return

    with ARQUIVO.open("w", encoding="utf-8", newline="") as arquivo:
        escritor = csv.DictWriter(
            arquivo,
            fieldnames=CAMPOS,
            delimiter=";",
        )
        escritor.writeheader()


def registrar_contexto_cerebro(
    origem,
    tipo,
    observacao="",
):

    _garantir_arquivo()

    status = obter_status_operadores()["operators"]
    collector = status["collector"]
    structure = status["structure"]
    setup = status["setup"]
    alignment = status["alignment"]

    linha = {
        "data": datetime.now().isoformat(timespec="seconds"),
        "origem": origem,
        "tipo": tipo,
        "collector_status": collector.get("status", "SEM DADOS"),
        "preco": collector.get("last_price", {}).get("bid", "SEM DADOS"),
        "tendencia": structure.get("tendencia", "SEM DADOS"),
        "momentum": "DESATIVADO",
        "sinal": structure.get("sinal", "SEM DADOS"),
        "direcao": setup.get("direcao", "SEM DADOS"),
        "smc": setup.get("smc", "SEM DADOS"),
        "elliott": setup.get("elliott", "SEM DADOS"),
        "confianca": setup.get("confianca", "SEM DADOS"),
        "brain_score": setup.get("brain_score", "SEM DADOS"),
        "alinhamento": alignment.get("status", "SEM DADOS"),
        "observacao": observacao,
    }

    with ARQUIVO.open("a", encoding="utf-8", newline="") as arquivo:
        escritor = csv.DictWriter(
            arquivo,
            fieldnames=CAMPOS,
            delimiter=";",
        )
        escritor.writerow(linha)

    return linha


def registrar_observacao_humana(observacao, origem="humano"):

    return registrar_contexto_cerebro(
        origem=origem,
        tipo="observacao_humana",
        observacao=observacao,
    )
