from web_app.services.leon_understanding_service import KEYWORDS


def analyze_human_text(text):
    normalized = str(text or "").lower()
    detected = [keyword for keyword in KEYWORDS if keyword in normalized]
    return {
        "detected_keywords": detected,
        "keyword_count": len(detected),
    }
