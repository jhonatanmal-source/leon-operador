def analisar_liquidez(score):

    if score >= 80:
        return "LIQUIDEZ_FORTE"

    elif score >= 50:
        return "LIQUIDEZ_MEDIA"

    return "LIQUIDEZ_FRACA"