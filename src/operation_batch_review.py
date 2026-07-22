import csv
import json
from collections import defaultdict
from datetime import datetime
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT_DIR / "data"
REPORTS_DIR = ROOT_DIR / "reports" / "operation_batches"
PRE_OPERATION_FILE = DATA_DIR / "pre_operation_trades.csv"
CONTEXT_FILE = DATA_DIR / "market_context_memory.csv"
STATE_FILE = DATA_DIR / "operation_batch_review_state.json"
RECOMMENDATIONS_FILE = DATA_DIR / "confidence_recommendations.json"
BATCH_SIZE = 20


def _read_csv(path):
    if not path.exists():
        return []

    with path.open("r", encoding="utf-8", newline="") as file:
        return list(csv.DictReader(file, delimiter=";"))


def _load_json(path, default):
    if not path.exists():
        return default

    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default


def _save_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def _float(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _closed_operations():
    contexts = {}
    for context in _read_csv(CONTEXT_FILE):
        operation_id = context.get("pre_operation_id")
        if operation_id:
            contexts[operation_id] = context

    operations = []
    for operation in _read_csv(PRE_OPERATION_FILE):
        result = str(operation.get("resultado", ""))
        if result != "LOSS" and not result.startswith("WIN"):
            continue

        item = dict(operation)
        item["context"] = contexts.get(operation.get("id"), {})
        operations.append(item)

    operations.sort(
        key=lambda item: (
            item.get("data_fechamento") or item.get("data_abertura") or ""
        )
    )
    return operations


def _is_win(operation):
    return str(operation.get("resultado", "")).startswith("WIN")


def _dimension_value(operation, dimension):
    context = operation.get("context") or {}
    values = {
        "sessao": context.get("sessao") or "SEM_DADOS",
        "top_down": context.get("top_down_alinhamento") or "SEM_DADOS",
        "direcao": operation.get("direcao") or "SEM_DADOS",
        "smc": operation.get("smc") or "SEM_DADOS",
        "elliott": operation.get("elliott") or "SEM_DADOS",
        "setup": operation.get("status_setup") or "SEM_DADOS",
        "bos": operation.get("bos") or "SEM_DADOS",
        "choch": operation.get("choch") or "SEM_DADOS",
        "rr": _rr_bucket(_float(operation.get("rr"))),
    }
    return values[dimension]


def _rr_bucket(rr):
    if rr < 1:
        return "RR_MENOR_1"
    if rr < 2:
        return "RR_1_A_2"
    if rr < 3:
        return "RR_2_A_3"
    return "RR_3_OU_MAIS"


def _performance_by_dimension(batch, dimension):
    groups = defaultdict(lambda: {"total": 0, "wins": 0, "losses": 0})

    for operation in batch:
        value = _dimension_value(operation, dimension)
        groups[value]["total"] += 1
        if _is_win(operation):
            groups[value]["wins"] += 1
        else:
            groups[value]["losses"] += 1

    results = []
    for value, metrics in groups.items():
        metrics["winrate"] = round(
            metrics["wins"] / metrics["total"] * 100,
            2,
        )
        results.append({"value": value, **metrics})

    return sorted(
        results,
        key=lambda item: (item["winrate"], item["total"]),
        reverse=True,
    )


def _recommendations(batch_number, analyses):
    recommendations = []

    for dimension, results in analyses.items():
        for result in results:
            if result["total"] < 5:
                continue

            if result["value"] in {
                "SEM_DADOS",
                "SEM_BOS",
                "SEM_CHOCH",
                "NEUTRO",
            }:
                continue

            if result["winrate"] >= 70:
                action = "AUMENTAR_CONFIANCA_RECOMENDADA"
                adjustment = 5
                reason = "Contexto consistente no bloco."
            elif result["winrate"] <= 35:
                action = "REDUZIR_CONFIANCA_RECOMENDADA"
                adjustment = -5
                reason = "Contexto apresentou recorrencia de perdas."
            else:
                action = "MANTER_EM_OBSERVACAO"
                adjustment = 0
                reason = "Amostra ainda sem vantagem clara."

            applied = (
                result["total"] >= 10
                and action in ("AUMENTAR_CONFIANCA_RECOMENDADA", "REDUZIR_CONFIANCA_RECOMENDADA")
            )
            recommendations.append({
                "batch": batch_number,
                "dimension": dimension,
                "value": result["value"],
                "sample": result["total"],
                "winrate": result["winrate"],
                "action": action,
                "suggested_adjustment": adjustment,
                "reason": reason,
                "applied_automatically": applied,
            })

    return recommendations


def _operation_r(operation):
    result = str(operation.get("resultado", ""))
    if result == "LOSS":
        return -1.0

    entry = _float(operation.get("entrada"))
    stop = _float(operation.get("stop"))
    risk = abs(entry - stop)
    if risk <= 0:
        return 0.0

    if result == "WIN_TP1":
        return abs(_float(operation.get("tp1")) - entry) / risk

    if result.startswith("WIN"):
        return abs(_float(operation.get("tp2")) - entry) / risk

    return 0.0


def _format_report(review):
    lines = [
        "LEON | REVISAO DE 20 OPERACOES",
        "=================================",
        f"Bloco: {review['batch']}",
        f"Periodo: {review['period_start']} ate {review['period_end']}",
        f"Operacoes: {review['total']}",
        f"Vitorias: {review['wins']}",
        f"Derrotas: {review['losses']}",
        f"Taxa de acerto: {review['winrate']}%",
        f"RR medio: 1:{review['average_rr']}",
        f"Resultado liquido simulado: {review['net_r']}R",
        "",
        "Melhores contextos",
    ]

    for item in review["best_contexts"]:
        lines.append(
            f"- {item['dimension']}={item['value']} | "
            f"{item['winrate']}% em {item['total']} operacoes"
        )

    lines.extend(["", "Contextos para revisar"])
    for item in review["weak_contexts"]:
        lines.append(
            f"- {item['dimension']}={item['value']} | "
            f"{item['winrate']}% em {item['total']} operacoes"
        )

    lines.extend([
        "",
        "Recomendacoes de confianca",
    ])
    if review["recommendations"]:
        for item in review["recommendations"]:
            lines.append(
                f"- {item['action']}: {item['dimension']}={item['value']} "
                f"({item['winrate']}%, amostra {item['sample']}, "
                f"ajuste sugerido {item['suggested_adjustment']:+d})"
            )
    else:
        lines.append("- Sem amostra minima para ajuste de confianca.")

    applied_count = sum(1 for r in review["recommendations"] if r.get("applied_automatically"))
    if applied_count > 0:
        lines.append(f"- {applied_count} recomendacao(oes) foram aplicadas automaticamente.")
    else:
        lines.append("- Nenhuma recomendacao foi aplicada automaticamente.")
    lines.extend([
        "",
        "Protecao",
        "- Risco, BOS, CHOCH, setup e regras operacionais permanecem inalterados.",
        "=================================",
    ])
    return "\n".join(lines)


def _review_batch(batch, batch_number):
    dimensions = [
        "sessao",
        "top_down",
        "direcao",
        "smc",
        "elliott",
        "setup",
        "bos",
        "choch",
        "rr",
    ]
    analyses = {
        dimension: _performance_by_dimension(batch, dimension)
        for dimension in dimensions
    }
    comparable = [
        {"dimension": dimension, **item}
        for dimension, results in analyses.items()
        for item in results
        if item["total"] >= 3
    ]
    best = sorted(
        comparable,
        key=lambda item: (item["winrate"], item["total"]),
        reverse=True,
    )[:5]
    weak = sorted(
        comparable,
        key=lambda item: (item["winrate"], -item["total"]),
    )[:5]
    wins = sum(1 for operation in batch if _is_win(operation))
    losses = len(batch) - wins
    average_rr = round(
        sum(_float(operation.get("rr")) for operation in batch) / len(batch),
        2,
    )
    net_r = round(sum(_operation_r(operation) for operation in batch), 2)
    recommendations = _recommendations(batch_number, analyses)
    review = {
        "batch": batch_number,
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "period_start": batch[0].get("data_fechamento"),
        "period_end": batch[-1].get("data_fechamento"),
        "operation_ids": [operation.get("id") for operation in batch],
        "total": len(batch),
        "wins": wins,
        "losses": losses,
        "winrate": round(wins / len(batch) * 100, 2),
        "average_rr": average_rr,
        "net_r": net_r,
        "best_contexts": best,
        "weak_contexts": weak,
        "recommendations": recommendations,
        "analyses": analyses,
        "rules_changed": False,
    }
    review["report"] = _format_report(review)
    return review


def process_operation_batches():
    operations = _closed_operations()
    complete_batches = len(operations) // BATCH_SIZE
    state = _load_json(STATE_FILE, {"processed_batches": []})
    processed = set(state.get("processed_batches", []))
    generated = []

    for index in range(complete_batches):
        batch_number = index + 1
        if batch_number in processed:
            continue

        start = index * BATCH_SIZE
        batch = operations[start:start + BATCH_SIZE]
        review = _review_batch(batch, batch_number)

        REPORTS_DIR.mkdir(parents=True, exist_ok=True)
        report_path = REPORTS_DIR / f"bloco_{batch_number:03d}.txt"
        json_path = REPORTS_DIR / f"bloco_{batch_number:03d}.json"
        report_path.write_text(review["report"], encoding="utf-8")
        _save_json(json_path, review)

        recommendations = _load_json(RECOMMENDATIONS_FILE, [])
        existing_keys = {
            (
                item.get("batch"),
                item.get("dimension"),
                item.get("value"),
            )
            for item in recommendations
        }
        recommendations.extend(
            item
            for item in review["recommendations"]
            if (
                item.get("batch"),
                item.get("dimension"),
                item.get("value"),
            ) not in existing_keys
        )
        _save_json(RECOMMENDATIONS_FILE, recommendations)

        processed.add(batch_number)
        generated.append({
            "batch": batch_number,
            "report_path": str(report_path),
            "json_path": str(json_path),
            "report": review["report"],
            "summary": (
                f"Bloco {batch_number}: {review['wins']} vitorias, "
                f"{review['losses']} derrotas, {review['winrate']}%."
            ),
        })

    state = {
        "processed_batches": sorted(processed),
        "closed_operations": len(operations),
        "complete_batches": complete_batches,
        "pending_for_next_batch": len(operations) % BATCH_SIZE,
        "updated_at": datetime.now().isoformat(timespec="seconds"),
    }
    _save_json(STATE_FILE, state)

    return {
        "ok": True,
        "generated": generated,
        "state": state,
    }


def latest_batch_status():
    return _load_json(
        STATE_FILE,
        {
            "processed_batches": [],
            "closed_operations": 0,
            "complete_batches": 0,
            "pending_for_next_batch": 0,
        },
    )
