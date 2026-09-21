from institutional_analysis_engine import analyze_elliott_context
from mt5_execution_refiner import load_execution_candles


def analisar_elliott(tendencia, momentum=None, candles=None):
    print()
    print("===================================")
    print("ELLIOTT ENGINE")
    print("===================================")

    if candles is None:
        market = load_execution_candles(m15_count=220, m5_count=20)
        candles = market.get("m15", []) if market.get("ok") else []

    context = analyze_elliott_context(candles, tendencia)
    print(f"CONTAGEM    : {context['label']}")
    print(f"FASE        : {context['phase']}")
    print(f"VALIDA      : {context['valid']}")
    print(f"CONFIANCA   : {context['confidence']}")
    print(f"INVALIDACAO : {context['invalidation']}")
    print(f"ALTERNATIVA : {context['alternative']}")
    return context["label"]
