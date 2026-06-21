from institutional_analysis_engine import analyze_smc_context
from mt5_execution_refiner import load_execution_candles


def analisar_smc(tendencia=None, momentum=None, score=None, candles=None):
    print()
    print("===================================")
    print("SMC ENGINE INSTITUCIONAL")
    print("===================================")

    if candles is None:
        market = load_execution_candles(m15_count=220, m5_count=20)
        candles = market.get("m15", []) if market.get("ok") else []

    context = analyze_smc_context(candles)
    print(f"SMC       : {context['smc']}")
    print(f"BOS       : {context['bos']}")
    print(f"CHOCH     : {context['choch']}")
    print(f"FVG       : {context['fvg']}")
    print(f"POI SCORE : {context['poi_score']}")
    print(f"MOTIVO    : {context['reason']}")
    return context["smc"]
