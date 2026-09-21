# ===================================
# ENTRY PRICE ENGINE
# ===================================

import configparser
from pathlib import Path

from mt5_execution_refiner import refine_m15_m5
from smc_price_levels import build_smc_trade_levels
from src.canonical_smc_entry import confirmed_zone_entry


CONFIG_FILE = Path(__file__).resolve().parent.parent / "config.ini"


def _minimum_operational_rr():
    config = configparser.ConfigParser()
    config.read(CONFIG_FILE, encoding="utf-8")
    if not config.has_section("EXECUTION"):
        return 1.0
    section = config["EXECUTION"]
    laboratorio = (
        section.get("demo_only", "true").lower() == "true"
        and section.get("learning_lab_enabled", "false").lower() == "true"
    )
    if laboratorio:
        return section.getfloat("lab_min_live_rr", fallback=0.75)
    return section.getfloat("min_live_rr", fallback=1.0)


def _learning_execution_enabled():
    config = configparser.ConfigParser()
    config.read(CONFIG_FILE, encoding="utf-8")
    if not config.has_section("EXECUTION"):
        return False
    section = config["EXECUTION"]
    return (
        section.get("demo_only", "true").lower() == "true"
        and section.get("learning_lab_enabled", "false").lower() == "true"
    )


def _entrada_aprendizado_mercado(direcao, candles, entry_price=None):
    if not candles:
        return None

    recentes = candles[-8:] if len(candles) >= 8 else candles
    entrada = float(entry_price or recentes[-1]["close"])

    if direcao == "COMPRA":
        stop = min(float(c["low"]) for c in recentes)
        risco = entrada - stop
        if risco <= 0:
            risco = max(entrada * 0.001, 1.0)
            stop = entrada - risco
        tp1 = entrada + risco
        tp2 = entrada + (risco * 1.5)
    else:
        stop = max(float(c["high"]) for c in recentes)
        risco = stop - entrada
        if risco <= 0:
            risco = max(entrada * 0.001, 1.0)
            stop = entrada + risco
        tp1 = entrada - risco
        tp2 = entrada - (risco * 1.5)

    rr = round(abs(tp2 - entrada) / max(abs(entrada - stop), 0.01), 2)
    print("ENTRADA APRENDIZADO: mercado atual em demo.")
    print(f"ENTRADA : {round(entrada, 2)}")
    print(f"STOP    : {round(stop, 2)}")
    print(f"TP1     : {round(tp1, 2)}")
    print(f"TP2     : {round(tp2, 2)}")
    print(f"RR      : 1:{rr}")
    return round(entrada, 2), round(stop, 2), round(tp1, 2), round(tp2, 2), rr


def calcular_entrada(
    direcao,
    topo,
    fundo,
    buy_liquidity=None,
    sell_liquidity=None,
    fvg_inicio=None,
    fvg_fim=None,
    symbol=None,
    diagnostics=None,
):
    trace = diagnostics if diagnostics is not None else {}
    trace.update(stage='LOADING_MARKET_DATA', reason='')
    print()
    print("===================================")
    print("ENTRY PRICE ENGINE")
    print("===================================")

    minimum_rr = _minimum_operational_rr()
    aprendizado = _learning_execution_enabled()
    if symbol:
        refinement = refine_m15_m5(direcao, symbol=symbol)
    else:
        refinement = refine_m15_m5(direcao)
    if not refinement.get("ok"):
        trace.update(stage='MARKET_DATA_REJECTED', reason=refinement.get('error', 'MARKET_DATA_UNAVAILABLE'))
        print(
            "SEM ENTRADA: nao foi possivel carregar candles M15/M5 "
            f"({refinement.get('error')})."
        )
        if aprendizado:
            return _entrada_aprendizado_mercado(direcao, refinement.get("m15") or [])
        return None

    # Existing canonical OB/supply-demand confirmations authorize their own
    # retest model. The FVG model below remains an independent alternative.
    structural_plan, structural_reason = confirmed_zone_entry(
        direcao, symbol, refinement['m15'], refinement['m5'], minimum_rr
    )
    trace['structural_reason'] = structural_reason
    if structural_plan is not None:
        trace.update(stage='ENTRY_READY', reason='STRUCTURAL_ZONE_ENTRY_READY', region_id=structural_plan.region_id)
        print(f"ENTRADA SMC: {structural_plan.model}; regiao {structural_plan.region_id}")
        return structural_plan
    print(f"SMC REGIAO: {structural_reason}")

    trigger = refinement["trigger"]
    if not trigger.get("confirmed"):
        trace.update(stage='M5_TRIGGER_REJECTED', reason=trigger.get('reason') or 'M5_TRIGGER_NOT_CONFIRMED')
        print(f"SEM ENTRADA: {trigger.get('reason')}.")
        if aprendizado:
            return _entrada_aprendizado_mercado(
                direcao,
                refinement.get("m15") or [],
                trigger.get("trigger_price"),
            )
        return None

    levels = build_smc_trade_levels(
        direcao,
        min_rr=minimum_rr,
        candles=refinement["m15"],
        entry_price=trigger.get("trigger_price"),
    )
    if levels is None:
        trace.update(stage='LEVELS_REJECTED', reason='FVG_OR_TECHNICAL_TARGETS_AT_RR_REJECTED', minimum_rr=minimum_rr)
        print(
            "SEM ENTRADA: preco fora do FVG ou alvo tecnico "
            f"sem pagar ao menos o risco 1:{minimum_rr}."
        )
        if aprendizado:
            return _entrada_aprendizado_mercado(
                direcao,
                refinement.get("m15") or [],
                trigger.get("trigger_price"),
            )
        return None

    entrada = levels["entry"]
    stop = levels["stop"]
    tp1 = levels["tp1"]
    tp2 = levels["tp2"]

    valid_structure = (
        stop < entrada < tp1 <= tp2
        if direcao == "COMPRA"
        else tp2 <= tp1 < entrada < stop
    )
    if not valid_structure:
        trace.update(stage='LEVELS_REJECTED', reason='INVALID_LEVEL_ORDER')
        print("SEM ENTRADA: niveis SMC sem estrutura operacional valida.")
        return None

    risk = abs(entrada - stop)
    reward = abs(tp2 - entrada)
    if risk <= 0:
        trace.update(stage='LEVELS_REJECTED', reason='INVALID_TECHNICAL_STOP')
        print("SEM ENTRADA: stop tecnico invalido.")
        return None

    rr = round(reward / risk, 2)

    print(f"ENTRADA : {entrada}")
    print(f"STOP    : {stop}")
    print(f"TP1     : {tp1}")
    print(f"TP2     : {tp2}")
    print(f"RR      : 1:{rr}")
    print(f"GATILHO : M5 {trigger.get('reason')}")
    print(f"ORIGEM  : M15 {levels['source']} + REFINO M5")

    trace.update(stage='ENTRY_READY', reason='FVG_ENTRY_READY')
    return entrada, stop, tp1, tp2, rr
