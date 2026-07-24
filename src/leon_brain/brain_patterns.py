from typing import Any

from .brain_models import OperationalBrainContext, BrainEvidence


SIMILARITY_FIELDS = [
    "macro_trend",
    "direction",
    "session",
    "killzone",
    "zone_type",
    "zone_timeframe",
    "smc_state",
    "elliott_state",
    "liquidity_context",
]


def compare_contexts(current: OperationalBrainContext, historical: dict) -> float:
    score = 0.0
    total = len(SIMILARITY_FIELDS)

    for field in SIMILARITY_FIELDS:
        current_val = getattr(current, field, "")
        historical_val = historical.get(field, "")
        if current_val and historical_val and current_val.lower() == historical_val.lower():
            score += 1.0

    return round(score / total, 2) if total > 0 else 0.0


def find_patterns(context: OperationalBrainContext, evidences: list[BrainEvidence], memories_data: list[dict]) -> dict:
    patterns = {
        "similar_contexts": [],
        "recurring_errors": [],
        "recurring_successes": [],
        "applicable_lessons": [],
        "present_conditions": [],
        "absent_conditions": [],
        "blockers": [],
    }

    for mem in memories_data:
        similarity = compare_contexts(context, mem)
        if similarity >= 0.5:
            patterns["similar_contexts"].append({
                "id": mem.get("id", ""),
                "similarity": similarity,
                "result": mem.get("result", ""),
                "lesson": mem.get("lesson", ""),
            })

            result = mem.get("result", "").lower()
            if "erro" in result or "perda" in result:
                patterns["recurring_errors"].append(mem)
            elif "acerto" in result or "ganho" in result:
                patterns["recurring_successes"].append(mem)

            lesson = mem.get("lesson", "")
            if lesson:
                patterns["applicable_lessons"].append(lesson)

    field_map = {
        "macro_trend": "Tendencia Macro",
        "session": "Sessao",
        "killzone": "Killzone",
        "zone_type": "Tipo de Zona",
        "smc_state": "Estrutura SMC",
        "elliott_state": "Fase Elliott",
    }

    for field, label in field_map.items():
        val = getattr(context, field, "")
        if val:
            patterns["present_conditions"].append(f"{label}: {val}")

    blockers = getattr(context, "current_blockers", [])
    if blockers:
        patterns["blockers"] = blockers

    all_conditions = set(field_map.keys())
    present = {f for f in all_conditions if getattr(context, f, "")}
    absent = all_conditions - present
    for field in absent:
        patterns["absent_conditions"].append(field_map[field])

    return patterns
