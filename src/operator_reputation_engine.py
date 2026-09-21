def calculate_reputation(total, approved, rejected, average_quality):
    total = int(total or 0)
    average_quality = float(average_quality or 0)

    if total >= 50 and average_quality >= 85:
        return "ELITE"
    if total >= 20 and average_quality >= 75:
        return "ALTA"
    if total >= 5 and average_quality >= 60:
        return "MEDIA"
    return "BAIXA"
