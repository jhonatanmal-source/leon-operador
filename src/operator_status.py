# ===================================
# OPERATOR STATUS
# ===================================

import configparser
import csv
from datetime import datetime, timedelta
from pathlib import Path

from src.autonomy_guard import status_autonomia
from src.emotion_engine import get_emotional_state
from src.telegram_config import CHAT_ID, TELEGRAM_ENABLED, TOKEN


ROOT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT_DIR / "data"
CONFIG_FILE = ROOT_DIR / "config.ini"
TELEGRAM_STATUS_STATE_FILE = DATA_DIR / "telegram_status_state.txt"


def _ler_ultima_linha(caminho):

    if not caminho.exists():
        return None

    with caminho.open("r", encoding="utf-8", errors="replace") as arquivo:
        linhas = [
            linha.strip()
            for linha in arquivo.readlines()
            if linha.strip()
        ]

    if not linhas:
        return None

    return linhas[-1]


def _contar_linhas(caminho):

    if not caminho.exists():
        return 0

    with caminho.open("r", encoding="utf-8", errors="replace") as arquivo:
        return len([linha for linha in arquivo.readlines() if linha.strip()])


def _split_csv_linha(linha):

    if not linha:
        return []

    return next(csv.reader([linha], delimiter=";"))


def _idade_registro(data_texto):

    if not data_texto:
        return None

    try:
        data = datetime.fromisoformat(data_texto)
    except ValueError:
        return None

    segundos = int((datetime.now() - data).total_seconds())

    if segundos < 60:
        return f"{segundos}s"

    minutos = segundos // 60

    if minutos < 60:
        return f"{minutos}m"

    horas = minutos // 60

    if horas < 24:
        return f"{horas}h"

    dias = horas // 24
    return f"{dias}d"


def _segundos_desde(data_texto):

    if not data_texto:
        return None

    try:
        data = datetime.fromisoformat(data_texto)
    except ValueError:
        return None

    return int((datetime.now() - data).total_seconds())


def _traduzir_direcao(valor):

    traducoes = {
        "BULLISH": "ALTA",
        "BEARISH": "BAIXA",
        "BUY": "ALTA",
        "SELL": "BAIXA",
        "COMPRADOR": "ALTA",
        "VENDEDOR": "BAIXA",
    }

    return traducoes.get(valor, valor)


def _diagnosticar_alinhamento(estrutura, setup):

    tendencia = estrutura.get("tendencia")
    smc = setup.get("smc")
    direcao = setup.get("direcao")
    elliott = setup.get("elliott")

    sinais = [
        tendencia,
        smc,
    ]

    sinais_validos = [
        sinal
        for sinal in sinais
        if sinal in ["ALTA", "BAIXA"]
    ]

    if not sinais_validos:
        return {
            "status": "SEM DADOS",
            "summary": "Sem dados suficientes para alinhamento.",
        }

    altas = sinais_validos.count("ALTA")
    baixas = sinais_validos.count("BAIXA")

    if altas == len(sinais_validos):
        base = "ALTA"
    elif baixas == len(sinais_validos):
        base = "BAIXA"
    else:
        base = "CONFLITO"

    if base == "CONFLITO":
        return {
            "status": "CONFLITO",
            "summary": "Estrutura e SMC nao estao alinhados.",
            "tendencia": tendencia,
            "smc": smc,
            "elliott": elliott,
            "direcao": direcao,
        }

    direcao_esperada = "COMPRA" if base == "ALTA" else "VENDA"

    if direcao and direcao != direcao_esperada:
        return {
            "status": "ATENCAO",
            "summary": "Direcao do plano difere do alinhamento principal.",
            "alinhamento": base,
            "direcao": direcao,
            "direcao_esperada": direcao_esperada,
            "elliott": elliott,
        }

    return {
        "status": "ALINHADO",
        "summary": f"Leitura principal em {base}.",
        "alinhamento": base,
        "direcao": direcao,
        "elliott": elliott,
    }


def _config_risco():

    config = configparser.ConfigParser()
    config.read(CONFIG_FILE, encoding="utf-8")

    if not config.has_section("RISK"):
        return {
            "max_trades_day": "NAO CONFIGURADO",
            "min_setup_score": "NAO CONFIGURADO",
        }

    risco = config["RISK"]
    max_trades_day = risco.get("max_trades_day", "NAO CONFIGURADO")

    if str(max_trades_day).strip() == "0":
        max_trades_day = "SEM LIMITE (CONTROLADO POR RISCO)"

    return {
        "max_trades_day": max_trades_day,
        "min_setup_score": risco.get("min_setup_score", "NAO CONFIGURADO"),
    }


def _config_operador():

    config = configparser.ConfigParser()
    config.read(CONFIG_FILE, encoding="utf-8")

    if not config.has_section("OPERATOR"):
        return {
            "telegram_status_enabled": True,
            "telegram_status_interval_minutes": 720,
            "collector_enabled": True,
            "collector_interval_minutes": 15,
        }

    operador = config["OPERATOR"]

    return {
        "telegram_status_enabled": operador.get(
            "telegram_status_enabled",
            "true",
        ).lower() == "true",
        "telegram_status_interval_minutes": operador.getint(
            "telegram_status_interval_minutes",
            fallback=720,
        ),
        "collector_enabled": operador.get(
            "collector_enabled",
            "true",
        ).lower() == "true",
        "collector_interval_minutes": operador.getint(
            "collector_interval_minutes",
            fallback=15,
        ),
    }


def _ler_datetime_arquivo(caminho):

    if not caminho.exists():
        return None

    conteudo = caminho.read_text(encoding="utf-8").strip()

    if not conteudo:
        return None

    try:
        return datetime.fromisoformat(conteudo)
    except ValueError:
        return None


def _status_coletor():

    preco = _split_csv_linha(_ler_ultima_linha(DATA_DIR / "price_history.csv"))
    candle = _split_csv_linha(_ler_ultima_linha(DATA_DIR / "candle_history.csv"))

    ultimo_preco = {}
    ultimo_candle = {}

    if len(preco) >= 4:
        idade_segundos = _segundos_desde(preco[0])
        ultimo_preco = {
            "data": preco[0],
            "ativo": preco[1],
            "bid": preco[2],
            "ask": preco[3],
            "idade": _idade_registro(preco[0]),
            "idade_segundos": idade_segundos,
        }

    if len(candle) >= 6:
        idade_segundos = _segundos_desde(candle[0])
        ultimo_candle = {
            "data": candle[0],
            "ativo": candle[1],
            "open": candle[2],
            "high": candle[3],
            "low": candle[4],
            "close": candle[5],
            "idade": _idade_registro(candle[0]),
            "idade_segundos": idade_segundos,
        }

    ativo = bool(ultimo_preco or ultimo_candle)
    idades = [
        item.get("idade_segundos")
        for item in [ultimo_preco, ultimo_candle]
        if item.get("idade_segundos") is not None
    ]
    mais_recente = min(idades) if idades else None

    if not ativo:
        status = "SEM DADOS"
        resumo = "Sem historico de coleta."
    elif mais_recente is not None and mais_recente > 1800:
        status = "DADOS ANTIGOS"
        resumo = "Coleta existe, mas nao esta recente."
    else:
        status = "OK"
        resumo = "Coleta possui historico recente."

    return {
        "name": "Market Collector",
        "status": status,
        "summary": resumo,
        "last_price": ultimo_preco,
        "last_candle": ultimo_candle,
        "price_records": _contar_linhas(DATA_DIR / "price_history.csv"),
        "candle_records": _contar_linhas(DATA_DIR / "candle_history.csv"),
    }


def _status_estrutura():

    sinal = _split_csv_linha(_ler_ultima_linha(DATA_DIR / "signals.csv"))

    if len(sinal) < 5:
        return {
            "name": "Market Structure",
            "status": "SEM DADOS",
            "summary": "Sem sinal estrutural registrado.",
        }

    return {
        "name": "Market Structure",
        "status": "OBSERVANDO",
        "summary": "Ultimo sinal registrado na memoria.",
        "data": sinal[0],
        "tendencia": sinal[1],
        "momentum": "DESATIVADO",
        "score": sinal[3],
        "sinal": sinal[4],
        "idade": _idade_registro(sinal[0]),
    }


def _status_setup():

    plano = _split_csv_linha(_ler_ultima_linha(DATA_DIR / "trade_plan_memory.csv"))

    if len(plano) < 7 or plano[0].lower() == "data":
        return {
            "name": "Setup Hunter",
            "status": "SEM DADOS",
            "summary": "Nenhum plano de setup encontrado.",
        }

    return {
        "name": "Setup Hunter",
        "status": "PRONTO",
        "summary": "Ultimo plano combina SMC + Elliott.",
        "data": plano[0],
        "ativo": plano[1],
        "direcao": plano[2],
        "smc": _traduzir_direcao(plano[3]),
        "smc_original": plano[3],
        "elliott": plano[4],
        "brain_score": plano[5],
        "confianca": plano[6],
        "idade": _idade_registro(plano[0]),
    }


def _status_risco():

    risco = _config_risco()

    return {
        "name": "Risk Manager",
        "status": "PROTEGENDO",
        "summary": "Limites carregados do config.ini.",
        "max_trades_day": risco["max_trades_day"],
        "min_setup_score": risco["min_setup_score"],
    }


def _status_professor():

    brain_total = _contar_linhas(DATA_DIR / "brain_memory.csv")
    trade_total = _contar_linhas(DATA_DIR / "trade_memory.csv")
    autonomia = status_autonomia()
    emocao = get_emotional_state()

    ultimo_brain = _split_csv_linha(_ler_ultima_linha(DATA_DIR / "brain_memory.csv"))

    detalhes = {}

    if len(ultimo_brain) >= 3:
        detalhes = {
            "brain_score": ultimo_brain[0],
            "confianca": ultimo_brain[1],
            "resultado": ultimo_brain[2],
        }

    return {
        "name": "Professor LEON",
        "status": "AUTONOMO" if autonomia["active"] else "AGUARDANDO",
        "summary": "Aprendizado diario e memoria operacional.",
        "autonomy": autonomia,
        "brain_records": brain_total,
        "trade_records": trade_total,
        "last_brain": detalhes,
        "emotion": emocao,
    }


def _status_telegram():
    operador = _config_operador()
    ultimo_status = _ler_datetime_arquivo(TELEGRAM_STATUS_STATE_FILE)
    proximo_status = None

    if ultimo_status is not None:
        proximo_status = ultimo_status + timedelta(
            minutes=operador["telegram_status_interval_minutes"],
        )
        if proximo_status <= datetime.now():
            proximo_status = datetime.now() + timedelta(
                minutes=operador["telegram_status_interval_minutes"],
            )

    return {
        "name": "Telegram",
        "status": "ATIVO" if TELEGRAM_ENABLED else "DESLIGADO",
        "summary": "Comunicacao externa do LEON.",
        "enabled": TELEGRAM_ENABLED,
        "has_token": bool(TOKEN),
        "has_chat_id": bool(CHAT_ID),
        "heartbeat_enabled": operador["telegram_status_enabled"],
        "heartbeat_interval_minutes": operador["telegram_status_interval_minutes"],
        "last_heartbeat": (
            ultimo_status.isoformat(timespec="seconds")
            if ultimo_status else None
        ),
        "next_heartbeat": (
            proximo_status.isoformat(timespec="seconds")
            if proximo_status else "AGUARDANDO PRIMEIRO ENVIO"
        ),
    }


def obter_status_operadores():

    collector = _status_coletor()
    structure = _status_estrutura()
    setup = _status_setup()
    risk = _status_risco()
    professor = _status_professor()
    telegram = _status_telegram()

    return {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "operators": {
            "collector": collector,
            "structure": structure,
            "setup": setup,
            "risk": risk,
            "professor": professor,
            "telegram": telegram,
            "alignment": _diagnosticar_alinhamento(
                structure,
                setup,
            ),
        },
    }
