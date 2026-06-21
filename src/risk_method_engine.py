# ===================================
# RISK METHOD ENGINE
# ===================================

import configparser
import csv
from collections import defaultdict
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parent.parent
CONFIG_FILE = ROOT_DIR / "config.ini"
PRE_OPERATION_FILE = ROOT_DIR / "data" / "pre_operation_trades.csv"


METHODS = {
    "SMC_TECNICO_VARIAVEL": {
        "rr_target": None,
        "risk_percent": 0.5,
        "daily_loss_percent": 2.0,
        "max_trades_day": 0,
    },
    "CONSERVADOR_1X2": {
        "rr_target": 2.0,
        "risk_percent": 0.5,
        "daily_loss_percent": 1.0,
        "max_trades_day": 3,
    },
    "PADRAO_1X3": {
        "rr_target": 3.0,
        "risk_percent": 0.5,
        "daily_loss_percent": 2.0,
        "max_trades_day": 3,
    },
    "AGRESSIVO_CONTROLADO_1X3": {
        "rr_target": 3.0,
        "risk_percent": 1.0,
        "daily_loss_percent": 2.0,
        "max_trades_day": 3,
    },
}


def metodo_ativo():

    config = configparser.ConfigParser()
    config.read(CONFIG_FILE, encoding="utf-8")

    if not config.has_section("RISK_METHOD"):
        return "SMC_TECNICO_VARIAVEL"

    metodo = config["RISK_METHOD"].get("active", "SMC_TECNICO_VARIAVEL")

    if metodo not in METHODS:
        return "SMC_TECNICO_VARIAVEL"

    return metodo


def obter_metodo(nome=None):

    nome = nome or metodo_ativo()
    metodo = METHODS.get(nome, METHODS["SMC_TECNICO_VARIAVEL"]).copy()
    metodo["name"] = nome

    return metodo


def _ler_pre_operacoes():

    if not PRE_OPERATION_FILE.exists():
        return []

    with PRE_OPERATION_FILE.open("r", encoding="utf-8", newline="") as arquivo:
        return list(csv.DictReader(arquivo, delimiter=";"))


def desempenho_por_metodo():

    registros = _ler_pre_operacoes()
    resumo = defaultdict(lambda: {
        "total": 0,
        "fechadas": 0,
        "wins": 0,
        "losses": 0,
        "taxa": 0,
    })

    for registro in registros:
        metodo = registro.get("metodo_risco") or "SEM_METODO"

        if registro.get("resultado") == "SEM_ENTRADA":
            continue

        resumo[metodo]["total"] += 1

        if registro.get("status") == "FECHADO":
            resumo[metodo]["fechadas"] += 1

            if str(registro.get("resultado", "")).startswith("WIN"):
                resumo[metodo]["wins"] += 1

            if registro.get("resultado") == "LOSS":
                resumo[metodo]["losses"] += 1

    for dados in resumo.values():
        if dados["fechadas"]:
            dados["taxa"] = round((dados["wins"] / dados["fechadas"]) * 100, 2)

    return dict(resumo)
