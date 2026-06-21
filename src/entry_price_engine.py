# ===================================
# ENTRY PRICE ENGINE
# ===================================

import configparser
from pathlib import Path

from mt5_execution_refiner import refine_m15_m5
from smc_price_levels import build_smc_trade_levels


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


def calcular_entrada(
    direcao,
    topo,
    fundo,
    buy_liquidity=None,
    sell_liquidity=None,
    fvg_inicio=None,
    fvg_fim=None,
):
    print()
    print("===================================")
    print("ENTRY PRICE ENGINE")
    print("===================================")

    minimum_rr = _minimum_operational_rr()
    refinement = refine_m15_m5(direcao)
    if not refinement.get("ok"):
        print(
            "SEM ENTRADA: nao foi possivel carregar candles M15/M5 "
            f"({refinement.get('error')})."
        )
        return None

    trigger = refinement["trigger"]
    if not trigger.get("confirmed"):
        print(f"SEM ENTRADA: {trigger.get('reason')}.")
        return None

    levels = build_smc_trade_levels(
        direcao,
        min_rr=minimum_rr,
        candles=refinement["m15"],
        entry_price=trigger.get("trigger_price"),
    )
    if levels is None:
        print(
            "SEM ENTRADA: preco fora do FVG ou alvo tecnico "
            f"sem pagar ao menos o risco 1:{minimum_rr}."
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
        print("SEM ENTRADA: niveis SMC sem estrutura operacional valida.")
        return None

    risk = abs(entrada - stop)
    reward = abs(tp2 - entrada)
    if risk <= 0:
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

    return entrada, stop, tp1, tp2, rr
