import re


KEYWORDS = [
    "liquidez",
    "bos",
    "choch",
    "fvg",
    "ob",
    "order block",
    "elliott",
    "onda",
    "retração",
    "rompimento",
    "manipulação",
    "stop",
    "alvo",
    "entrada",
    "venda",
    "compra",
    "tendência",
    "topo",
    "fundo",
    "pullback",
    "mitigação",
    "varredura",
]


def _contains(text, keyword):
    if keyword == "ob":
        return re.search(r"\bob\b", text) is not None
    return keyword in text


def generate_leon_understanding(
    text_analysis,
    direction,
    timeframe,
    analysis_type,
):
    normalized = str(text_analysis or "").lower()
    detected = [keyword for keyword in KEYWORDS if _contains(normalized, keyword)]

    confidence = 40
    if "liquidez" in detected:
        confidence += 10
    if "choch" in detected:
        confidence += 10
    if "bos" in detected:
        confidence += 10
    if any(keyword in detected for keyword in ["fvg", "ob", "order block"]):
        confidence += 10
    if "stop" in detected and "alvo" in detected:
        confidence += 10
    confidence = min(confidence, 90)

    main_factors = detected[:4]
    if main_factors:
        factors_text = ", ".join(main_factors)
        factors_sentence = (
            f"O operador destacou {factors_text} como fatores principais."
        )
    else:
        factors_sentence = (
            "Nenhuma palavra-chave principal foi identificada automaticamente."
        )

    summary = (
        f"LEON entendeu que esta análise sugere {direction} no XAUUSD "
        f"no timeframe {timeframe}, classificada como {analysis_type}. "
        f"{factors_sentence} A leitura será registrada como estudo humano "
        "supervisionado e ficará pendente de validação."
    )

    return {
        "leon_summary": summary,
        "detected_keywords": ", ".join(detected),
        "confidence_score": confidence,
    }
