# ===================================

# LEON XAU ELITE AI V3

# ===================================

from pathlib import Path

import os

os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("MKL_NUM_THREADS", "1")
os.environ.setdefault("NUMEXPR_NUM_THREADS", "1")

import csv
import sys


if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from system_status import exibir_status

from market_reader import ler_preco_xau
from candle_reader import ler_candle_m15

from trend_reader import analisar_tendencia_real

from market_score import calcular_market_score
from signal_quality import avaliar_qualidade

from signal_engine import gerar_sinal
from signal_logger import registrar_sinal

from dashboard_report import mostrar_dashboard

from memory_analyzer import analisar_memoria
from memory_rank import analisar_rank

from setup_reputation import avaliar_setup
from decision_guard import validar_decisao

from brain_engine import analisar_cerebro
from confidence_engine import calcular_confianca

from trade_memory import salvar_memoria_trade
from brain_memory import registrar_brain

from brain_analyzer import analisar_brain
from brain_evolution import evoluir_cerebro

from evolution_report import gerar_relatorio_evolucao
from market_structure import analisar_estrutura

from trade_plan_engine import gerar_trade_plan
from trade_plan_memory import salvar_trade_plan

from entry_price_engine import calcular_entrada
from trade_explanation_engine import explicar_trade
from pre_operation_engine import registrar_pre_operacao
from top_down_agent import gerar_leitura_top_down

from setup_validator import validar_setup
from smc_entry_guard import validate_smc_entry
from institutional_analysis_engine import (
    analyze_elliott_context,
    analyze_smc_context,
)
from mt5_execution_refiner import load_execution_candles
from screenshot_engine import registrar_screenshot
from shadow_trade import evaluate_shadow_trades, register_shadow_trade
from lab_entry_policy import (
    evaluate_lab_entry,
    lab_event_available,
    mark_lab_event,
)
from timeframe_policy import evaluate_timeframe_policy

from alert_engine import gerar_alerta
from telegram_alert import (
    enviar_alerta_bos,
    enviar_alerta_choch,
    enviar_alerta_setup,
)

# ===================================

# LEON CORE

# ===================================

class Leon:

    def __init__(self):

        self.market = "XAU/USD"
        self.status = "Observando Mercado"

    def iniciar(self):

        print()
        print("===================================")
        print("LEON XAU ELITE AI")
        print("===================================")

        print(f"Mercado : {self.market}")
        print(f"Status  : {self.status}")

        print("===================================")
        print("Consistência primeiro.")
        print("Lucro depois.")
        print("===================================")
        print()


class _CandlesIloc:

    def __init__(self, candles):
        self._candles = candles

    def __getitem__(self, indice):
        return self._candles[indice]


class _CandlesLeves:

    def __init__(self, candles):
        self._candles = candles
        self.iloc = _CandlesIloc(candles)

    def __len__(self):
        return len(self._candles)


def carregar_candles_para_bos(limite=20):

    caminho = Path("C:/XAU_ELITE_AI/data/candle_history.csv")

    if not caminho.exists():
        return _CandlesLeves([])

    colunas = ["data", "ativo", "open", "high", "low", "close"]
    candles = []

    with caminho.open("r", encoding="utf-8", errors="replace", newline="") as arquivo:
        leitor = csv.reader(arquivo, delimiter=";")

        for linha in leitor:
            if len(linha) < len(colunas):
                continue

            registro = dict(zip(colunas, linha[:len(colunas)]))

            try:
                registro["open"] = float(registro["open"])
                registro["high"] = float(registro["high"])
                registro["low"] = float(registro["low"])
                registro["close"] = float(registro["close"])
            except ValueError:
                continue

            candles.append(registro)

    return _CandlesLeves(candles[-limite:])


def normalizar_bos(resultado):

    texto = str(resultado or "").upper()

    if "ALTA" in texto or "BULLISH" in texto:
        return "BOS_BULLISH"

    if "BAIXA" in texto or "BEARISH" in texto:
        return "BOS_BEARISH"

    return "SEM_BOS"


# ===================================
# START
# ===================================

leon = Leon()

leon.iniciar()

# ===================================

# COLETA DE DADOS

# ===================================

ler_preco_xau()

ler_candle_m15()

# ===================================

# ANÁLISE

# ===================================

tendencia = analisar_tendencia_real()


print()
print("===================================")
print("ANÁLISE")
print("===================================")

print(f"TENDÊNCIA : {tendencia}")

# ===================================

# SCORE

# ===================================

score = calcular_market_score(tendencia)

print(f"SCORE     : {score}")

# ===================================

# QUALIDADE

# ===================================

qualidade = avaliar_qualidade(tendencia)

print(f"QUALIDADE : {qualidade}")



# ===================================
# SINAL
# ===================================

if qualidade == "CONFLITO":

    sinal = "BLOQUEADO"

    print("SETUP BLOQUEADO")

else:

    sinal = gerar_sinal(score)

print(f"SINAL : {sinal}")

# ===================================

# DASHBOARD

# ===================================

mostrar_dashboard()

print()
print("===================================")
print("LEON FINALIZADO")
print("===================================")

print(f"SINAL : {sinal}")

# ===================================

# MEMÓRIA

# ===================================

analisar_memoria()

analisar_rank()

# ===================================

# REPUTAÇÃO

# ===================================

reputacao = avaliar_setup(tendencia)

print(f"REPUTAÇÃO : {reputacao}")

# ===================================

# DECISÃO

# ===================================

decisao = validar_decisao(
qualidade,
reputacao
)

print(f"DECISÃO FINAL : {decisao}")

# ===================================
# Operacional
# ===================================

gerar_relatorio_evolucao()

estrutura = analisar_estrutura(
    tendencia
)

mercado_operacional = load_execution_candles(
    symbol="XAUUSD",
    m15_count=220,
    m5_count=180,
)
if mercado_operacional.get("ok"):
    candles_m15 = mercado_operacional["m15"]
    candles_h1 = mercado_operacional["h1"]
    candles_h4 = mercado_operacional["h4"]
    leitura_top_down = gerar_leitura_top_down(
        candles_h4=candles_h4,
        candles_h1=candles_h1,
        candles_m15=candles_m15,
    )
    smc_context = analyze_smc_context(candles_m15)
    tendencia_elliott = (
        leitura_top_down["h1_contexto"]
        if leitura_top_down["h1_contexto"] in ["ALTA", "BAIXA"]
        else tendencia
    )
    elliott_context = analyze_elliott_context(candles_h1, tendencia_elliott)
    evaluate_shadow_trades(candles_m15)
else:
    candles_m15 = []
    leitura_top_down = gerar_leitura_top_down()
    smc_context = {
        "direction": None,
        "smc": "NEUTRO",
        "bos": "SEM_BOS",
        "choch": "SEM_CHOCH",
        "fvg": "SEM_FVG_CONFIRMADO",
        "fvg_zone": None,
        "liquidity": {"type": "SEM_EVENTO", "direction": None},
        "poi_score": 0,
        "pivots": [],
        "reason": mercado_operacional.get("error", "SEM_DADOS_M15"),
    }
    elliott_context = {
        "label": "SEM_CONTAGEM",
        "phase": "INDEFINIDA",
        "valid": False,
        "confidence": 0,
        "invalidation": None,
        "alternative": "SEM_DADOS",
    }

smc = smc_context["smc"]
bos = smc_context["bos"]
choch = smc_context["choch"]
fvg = smc_context["fvg"]
elliott = elliott_context["label"]

print()
print("===================================")
print("SMC INSTITUCIONAL M15")
print("===================================")
print(f"SMC       : {smc}")
print(f"BOS       : {bos}")
print(f"CHOCH     : {choch}")
print(f"FVG       : {fvg}")
print(f"LIQUIDEZ  : {smc_context['liquidity'].get('type')}")
print(f"POI SCORE : {smc_context['poi_score']}")
print(f"MOTIVO    : {smc_context['reason']}")

print()
print("===================================")
print("ELLIOTT COM INVALIDACAO")
print("===================================")
print(f"CONTAGEM    : {elliott}")
print(f"FASE        : {elliott_context['phase']}")
print(f"VALIDA      : {elliott_context['valid']}")
print(f"CONFIANCA   : {elliott_context['confidence']}")
print(f"INVALIDACAO : {elliott_context['invalidation']}")
print(f"ALTERNATIVA : {elliott_context['alternative']}")
fibonacci_setup = elliott_context.get("fibonacci_setup") or {}
print(f"FIBONACCI   : {fibonacci_setup.get('reason', 'SEM_DADOS')}")
print(f"RETRACAO    : {fibonacci_setup.get('retracement')}")
print(f"PROJECAO    : {fibonacci_setup.get('projection')}")
liquidez_alinhada = (
    smc_context["liquidity"].get("direction")
    == smc_context.get("direction")
)
print(f"LIQUIDEZ OK : {liquidez_alinhada}")

enviar_alerta_bos(
    "XAUUSD",
    "OPERACIONAL",
    bos,
    smc_context.get("bos_event"),
)

enviar_alerta_choch(
    "XAUUSD",
    "OPERACIONAL",
    choch,
    smc_context.get("choch_event"),
)

high_pivots = [
    pivot["price"]
    for pivot in smc_context["pivots"]
    if pivot["type"] == "HIGH"
]
low_pivots = [
    pivot["price"]
    for pivot in smc_context["pivots"]
    if pivot["type"] == "LOW"
]
topo = high_pivots[-1] if high_pivots else 0
fundo = low_pivots[-1] if low_pivots else 0
buy_liquidity = topo
sell_liquidity = fundo
fvg_zone = smc_context.get("fvg_zone") or {}
fvg_inicio = fvg_zone.get("start", 0)
fvg_fim = fvg_zone.get("end", 0)

brain_score = analisar_cerebro(
    tendencia,
    smc,
    elliott,
    score,
    qualidade,
    reputacao
)
confianca = calcular_confianca(brain_score)

direcao_candidata = (
    "COMPRA"
    if smc_context.get("direction") == "BULLISH"
    else "VENDA"
    if smc_context.get("direction") == "BEARISH"
    else "AGUARDAR"
)

smc_guard = validate_smc_entry(
    direcao_candidata,
    smc,
    bos,
    choch,
)
if not smc_guard["approved"]:
    print(f"ENTRADA BLOQUEADA: {smc_guard['reason']}")

setup_onda_confirmado = (
    fibonacci_setup.get("valid") is True
    and fibonacci_setup.get("target_wave") in ["ONDA 3", "ONDA 5"]
    and liquidez_alinhada
)
if not setup_onda_confirmado:
    print("ENTRADA BLOQUEADA: FIBONACCI_OU_LIQUIDEZ_NAO_CONFIRMADOS")

direcao_m15 = (
    "ALTA"
    if direcao_candidata == "COMPRA"
    else "BAIXA"
    if direcao_candidata == "VENDA"
    else None
)
timeframe_policy = evaluate_timeframe_policy(
    leitura_top_down,
    direcao_candidata,
)
top_down_confirmado = timeframe_policy["approved"]
if not top_down_confirmado:
    print("ENTRADA BLOQUEADA: TOP_DOWN_M15_NOT_ALIGNED")
elif timeframe_policy["mode"] == "CORRECAO":
    print(
        "MODO CORRECAO: macro contrario, mas H4/H1/M15 "
        "confirmam movimento tatico."
    )

confirmacoes_faltantes = []
if not smc_guard["approved"]:
    confirmacoes_faltantes.append("SMC_CHOCH_BOS")
if not fibonacci_setup.get("valid"):
    confirmacoes_faltantes.append("FIBONACCI_ONDA_2_OU_4")
if not liquidez_alinhada:
    confirmacoes_faltantes.append("CAPTURA_LIQUIDEZ")
if not top_down_confirmado:
    confirmacoes_faltantes.append("TOP_DOWN_H4_H1_M15")

bos_event = smc_context.get("bos_event") or {}
choch_event = smc_context.get("choch_event") or {}
lab_event_signature = "|".join(
    [
        direcao_candidata,
        str(bos_event.get("time")),
        str(choch_event.get("time")),
    ]
)
lab_entry = evaluate_lab_entry(
    smc_confirmed=smc_guard["approved"],
    top_down_confirmed=top_down_confirmado,
    strict_confirmation=setup_onda_confirmado,
    missing_confirmations=confirmacoes_faltantes,
)
if lab_entry["approved"] and not lab_event_available(lab_event_signature):
    lab_entry["approved"] = False
    lab_entry["mode"] = "LAB_EVENT_ALREADY_USED"
if lab_entry["approved"]:
    print(
        "LAB DEMO LIBERADO: evidencia shadow "
        f"{lab_entry['evidence']['wins']}W/"
        f"{lab_entry['evidence']['losses']}L "
        f"({lab_entry['evidence']['winrate']}%)."
    )

if direcao_candidata in ["COMPRA", "VENDA"] and confirmacoes_faltantes:
    assinatura_shadow = "|".join(
        [
            direcao_candidata,
            str(bos_event.get("time")),
            str(choch_event.get("time")),
        ]
    )
    shadow_result = register_shadow_trade(
        candles_m15,
        direcao_candidata,
        confirmacoes_faltantes,
        assinatura_shadow,
    )
    print(f"SHADOW TRADE: {shadow_result}")

direcao = (
    direcao_candidata
    if (
        smc_guard["approved"]
        and top_down_confirmado
        and (setup_onda_confirmado or lab_entry["approved"])
    )
    else "AGUARDAR"
)

qualidade_operacional = (
    qualidade
    if smc_guard["approved"] and setup_onda_confirmado and top_down_confirmado
    else "LAB_SHADOW_VALIDATED"
    if lab_entry["approved"]
    else (
        "SMC_NAO_CONFIRMADO"
        if not smc_guard["approved"]
        else (
            "FIBONACCI_LIQUIDEZ_NAO_CONFIRMADOS"
            if not setup_onda_confirmado
            else "TOP_DOWN_NAO_CONFIRMADO"
        )
    )
)
sinal_operacional = (
    sinal
    if (
        smc_guard["approved"]
        and top_down_confirmado
        and (setup_onda_confirmado or lab_entry["approved"])
    )
    else "OBSERVAR"
)

salvar_memoria_trade(
    tendencia,
    "DESATIVADO",
    score,
    sinal_operacional,
    qualidade_operacional,
    smc,
    elliott,
    confianca
)
registrar_sinal(
    tendencia,
    "DESATIVADO",
    score,
    sinal_operacional
)
analisar_brain()
evoluir_cerebro()

gerar_trade_plan(
    "XAUUSD",
    direcao,
    confianca,
    smc,
    elliott,
    brain_score
)

salvar_trade_plan(
    "XAUUSD",
    direcao,
    smc,
    elliott,
    brain_score,
    confianca
)

operacao = None
if direcao != "AGUARDAR":
    operacao = calcular_entrada(
        direcao,
        topo,
        fundo,
        buy_liquidity=buy_liquidity,
        sell_liquidity=sell_liquidity,
        fvg_inicio=fvg_inicio,
        fvg_fim=fvg_fim,
    )
    if operacao is not None and lab_entry["approved"]:
        mark_lab_event(lab_event_signature)
explicar_trade(
    tendencia,
    estrutura,
    bos,
    choch,
    smc,
    elliott,
    brain_score,
    confianca
)
status_setup = validar_setup(
    choch,
    bos,
    smc,
    elliott,
    confianca
)

if direcao == "AGUARDAR":
    status_setup = "SETUP FRACO"

print()
print("===================================")
print("TOP-DOWN AGENT")
print("===================================")
print(f"MACRO : {leitura_top_down['macro_semanal']}")
print(f"H4    : {leitura_top_down['h4_bias']}")
print(f"H1    : {leitura_top_down['h1_contexto']}")
print(f"M15   : {leitura_top_down['m15_gatilho']}")
print(f"ALINHAMENTO: {leitura_top_down['alinhamento']}")

registrar_pre_operacao(
    "XAUUSD",
    direcao,
    status_setup,
    operacao,
    smc,
    elliott,
    bos,
    choch,
    confianca,
    brain_score,
    context_mode=timeframe_policy["mode"],
)

if status_setup in [
    "SETUP PREMIUM",
    "SETUP A+"
]:

    registrar_screenshot()

    alerta = gerar_alerta(
        status_setup,
        confianca,
        direcao
    )

    if alerta:

        enviar_alerta_setup(
            "XAUUSD",
            status_setup,
            direcao,
            confianca,
            smc,
            elliott,
            bos,
            choch,
            brain_score
        )
    
    
