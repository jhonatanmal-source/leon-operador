# ===================================
# FVG ENGINE V2
# ===================================

from smc_price_levels import detect_latest_fvg, load_candles


def analisar_fvg_v2(tendencia, topo, fundo):
    print()
    print("===================================")
    print("FVG ENGINE V2")
    print("===================================")

    direction = "COMPRA" if tendencia == "ALTA" else "VENDA" if tendencia == "BAIXA" else None
    fvg = detect_latest_fvg(load_candles(), direction) if direction else None

    if fvg is None:
        print("TIPO   : SEM_FVG_CONFIRMADO")
        print("INICIO : 0")
        print("FIM    : 0")
        return "SEM_FVG_CONFIRMADO", 0, 0

    print(f"TIPO   : {fvg['type']}")
    print(f"INICIO : {fvg['start']}")
    print(f"FIM    : {fvg['end']}")
    return fvg["type"], fvg["start"], fvg["end"]
