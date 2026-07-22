# ===================================
# TOP DOWN AGENT
# ===================================

import csv
from datetime import datetime
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT_DIR / "data"
TOP_DOWN_FILE = DATA_DIR / "top_down_memory.csv"
CANDLE_HISTORY_FILE = DATA_DIR / "candle_history.csv"

FIELDS = [
    "data",
    "macro_semanal",
    "h4_bias",
    "h1_contexto",
    "m15_gatilho",
    "alinhamento",
    "resumo",
]


def _garantir_arquivo():

    DATA_DIR.mkdir(parents=True, exist_ok=True)

    if TOP_DOWN_FILE.exists():
        return

    with TOP_DOWN_FILE.open("w", encoding="utf-8", newline="") as arquivo:
        escritor = csv.DictWriter(arquivo, fieldnames=FIELDS, delimiter=";")
        escritor.writeheader()


def _ler_candles():

    if not CANDLE_HISTORY_FILE.exists():
        return []

    linhas = [
        linha.strip().split(";")
        for linha in CANDLE_HISTORY_FILE.read_text(encoding="utf-8").splitlines()
        if linha.strip()
    ]

    candles = []

    for partes in linhas:
        if len(partes) < 6:
            continue

        try:
            candles.append({
                "data": partes[0],
                "ativo": partes[1],
                "open": float(partes[2]),
                "high": float(partes[3]),
                "low": float(partes[4]),
                "close": float(partes[5]),
            })
        except ValueError:
            continue

    return candles


def _bias(candles):

    if len(candles) < 5:
        return "SEM DADOS"

    closes = [c["close"] for c in candles]

    short_term = sum(closes[-5:]) / 5
    medium_term = sum(closes[-20:]) / 20 if len(closes) >= 20 else sum(closes) / len(closes)

    threshold = medium_term * 0.002  # 0.2% para evitar ruido
    if short_term > medium_term + threshold:
        return "ALTA"

    if short_term < medium_term - threshold:
        return "BAIXA"

    recent_highs = [c["high"] for c in candles[-10:]]
    recent_lows = [c["low"] for c in candles[-10:]]
    higher_highs = recent_highs[-1] > max(recent_highs[:-1]) if len(recent_highs) > 1 else False
    lower_lows = recent_lows[-1] < min(recent_lows[:-1]) if len(recent_lows) > 1 else False

    if higher_highs and not lower_lows:
        return "ALTA"

    if lower_lows and not higher_highs:
        return "BAIXA"

    return "LATERAL"


def gerar_leitura_top_down(candles_h4=None, candles_h1=None, candles_m15=None):

    if candles_h4 and candles_h1 and candles_m15:
        macro = _bias(candles_h4[-120:])
        h4 = _bias(candles_h4[-30:])
        h1 = _bias(candles_h1[-24:])
        m15 = _bias(candles_m15[-8:])
    else:
        candles = _ler_candles()
        # FALLBACK: sem dados multi-timeframe, usamos janelas diferentes
        # do mesmo CSV. O novo _bias() com médias curtas vs longas
        # captura perspectivas diferentes mesmo num único timeframe.
        macro = _bias(candles[-120:])  # ~120 periodos (ex: 10h em M5)
        h4 = _bias(candles[-48:])      # ~48 periodos (ex: 4h em M5)
        h1 = _bias(candles[-24:])      # ~24 periodos (ex: 2h em M5)
        m15 = _bias(candles[-8:])      # ~8 periodos (ex: 40min em M5)

    leituras = [macro, h4, h1, m15]
    validas = [leitura for leitura in leituras if leitura in ["ALTA", "BAIXA"]]

    if len(validas) >= 3 and len(set(validas[-3:])) == 1:
        alinhamento = "ALINHADO"
        resumo = f"Macro para micro favorece {validas[-1]}."
    elif len(validas) >= 2:
        alinhamento = "MISTO"
        resumo = "Timeframes ainda mistos. Operar somente teste/supervisao."
    else:
        alinhamento = "SEM DADOS"
        resumo = "Sem dados suficientes para leitura top-down."

    registro = {
        "data": datetime.now().isoformat(timespec="seconds"),
        "macro_semanal": macro,
        "h4_bias": h4,
        "h1_contexto": h1,
        "m15_gatilho": m15,
        "alinhamento": alinhamento,
        "resumo": resumo,
    }

    _garantir_arquivo()

    with TOP_DOWN_FILE.open("a", encoding="utf-8", newline="") as arquivo:
        escritor = csv.DictWriter(arquivo, fieldnames=FIELDS, delimiter=";")
        escritor.writerow(registro)

    return registro


def ultima_leitura_top_down():

    _garantir_arquivo()

    with TOP_DOWN_FILE.open("r", encoding="utf-8", newline="") as arquivo:
        registros = list(csv.DictReader(arquivo, delimiter=";"))

    if not registros:
        return gerar_leitura_top_down()

    return registros[-1]
