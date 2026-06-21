import csv
import json
from collections import Counter
from datetime import date, datetime, time, timedelta
from pathlib import Path

from web_app.database.db import get_connection


ROOT_DIR = Path(__file__).resolve().parent.parent.parent
DATA_DIR = ROOT_DIR / "data"
LOGS_DIR = ROOT_DIR / "logs"
REPORTS_DIR = ROOT_DIR / "reports" / "weekly_audits"
PRE_OPERATIONS_FILE = DATA_DIR / "pre_operation_trades.csv"
DECISIONS_FILE = DATA_DIR / "operation_decisions.csv"
ORDERS_FILE = DATA_DIR / "mt5_order_memory.csv"
ERRORS_FILE = LOGS_DIR / "errors.txt"


def _read_csv(path):
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8", errors="replace", newline="") as file:
        return list(csv.DictReader(file, delimiter=";"))


def _parse_datetime(value):
    text = str(value or "").strip()
    if not text:
        return None
    if text.startswith("[") and "]" in text:
        text = text[1:text.index("]")]
    elif " | " in text:
        text = text.split(" | ", 1)[0]
    try:
        return datetime.fromisoformat(text)
    except ValueError:
        return None


def _in_period(value, start, end):
    parsed = _parse_datetime(value)
    return parsed is not None and start <= parsed <= end


def _safe_float(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _error_lines(start, end):
    if not ERRORS_FILE.exists():
        return []
    lines = ERRORS_FILE.read_text(
        encoding="utf-8",
        errors="replace",
    ).splitlines()
    return [line.strip() for line in lines if _in_period(line, start, end)]


def _human_analysis_metrics(start, end):
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT status, COUNT(*) AS total
            FROM human_analyses
            WHERE created_at BETWEEN ? AND ?
            GROUP BY status
            """,
            (
                start.isoformat(timespec="seconds"),
                end.isoformat(timespec="seconds"),
            ),
        ).fetchall()
    counts = {row["status"]: row["total"] for row in rows}
    return {
        "total": sum(counts.values()),
        "pending": counts.get("PENDENTE", 0),
        "approved": counts.get("APROVADA", 0),
        "rejected": counts.get("REJEITADA", 0),
    }


def _severity_rank(severity):
    return {"CRITICO": 0, "ALTO": 1, "MEDIO": 2, "INFO": 3}.get(
        severity,
        4,
    )


def _build_findings(
    pre_operations,
    decisions,
    errors,
    human,
    executed_operation_ids=None,
):
    findings = []
    executed_operation_ids = set(executed_operation_ids or [])
    executed = [
        row for row in pre_operations
        if row.get("id") in executed_operation_ids
    ]
    structural_violations = [
        row
        for row in executed
        if (
            row.get("smc") not in {"BULLISH", "BEARISH"}
            or row.get("bos") not in {"BOS_BULLISH", "BOS_BEARISH"}
            or row.get("choch") not in {"CHOCH_BULLISH", "CHOCH_BEARISH"}
        )
    ]
    weak_observations = [
        row
        for row in pre_operations
        if row.get("status_setup") == "SETUP FRACO"
        or row.get("smc") == "NEUTRO"
    ]
    low_rr = [
        row
        for row in decisions
        if "RR" in str(row.get("motivo", "")).upper()
        or (
            row.get("rr_real") not in {None, ""}
            and _safe_float(row.get("rr_real")) < 1
        )
    ]
    price_drift = [
        row
        for row in decisions
        if any(
            marker in str(row.get("motivo", "")).upper()
            for marker in ("ZONA", "DRIFT")
        )
    ]

    if structural_violations:
        findings.append({
            "severity": "CRITICO",
            "title": "Execução sem estrutura completa",
            "count": len(structural_violations),
            "detail": "Há operações executadas sem SMC, BOS e CHOCH válidos.",
            "correction": (
                "Manter essas entradas bloqueadas e revisar cada ID antes de "
                "qualquer nova liberação."
            ),
            "items": [row.get("id") for row in structural_violations[:8]],
        })
    if errors:
        findings.append({
            "severity": "ALTO",
            "title": "Erros técnicos registrados",
            "count": len(errors),
            "detail": "O operador registrou falhas técnicas durante a semana.",
            "correction": (
                "Confirmar recuperação no log, corrigir a causa recorrente e "
                "executar os testes do módulo afetado."
            ),
            "items": [line[-180:] for line in errors[-5:]],
        })
    if low_rr:
        findings.append({
            "severity": "MEDIO",
            "title": "Risco-retorno insuficiente",
            "count": len(low_rr),
            "detail": "Entradas foram bloqueadas ou avaliadas com RR abaixo do mínimo.",
            "correction": (
                "Aguardar retorno à zona planejada; não perseguir preço para "
                "forçar uma entrada."
            ),
            "items": [],
        })
    if price_drift:
        findings.append({
            "severity": "MEDIO",
            "title": "Preço fora da zona planejada",
            "count": len(price_drift),
            "detail": "O preço se afastou da região definida para entrada.",
            "correction": (
                "Invalidar a oportunidade após o drift e exigir uma nova "
                "estrutura antes de recalcular a entrada."
            ),
            "items": [],
        })
    if human["rejected"]:
        findings.append({
            "severity": "MEDIO",
            "title": "Análises humanas rejeitadas",
            "count": human["rejected"],
            "detail": "Há análises colaborativas rejeitadas no período.",
            "correction": (
                "Revisar os comentários do supervisor e reenviar somente após "
                "corrigir contexto, direção e justificativa."
            ),
            "items": [],
        })
    if weak_observations:
        findings.append({
            "severity": "INFO",
            "title": "Setups fracos bloqueados corretamente",
            "count": len(weak_observations),
            "detail": "O filtro evitou execução em contexto neutro ou fraco.",
            "correction": (
                "Manter o bloqueio. Usar esses casos como estudo, sem tratá-los "
                "como erro operacional."
            ),
            "items": [],
        })
    return sorted(findings, key=lambda item: _severity_rank(item["severity"]))


def _daily_summary(start_date, end_date, pre_operations, decisions, errors):
    days = []
    current = start_date
    while current <= end_date:
        prefix = current.isoformat()
        day_preops = [
            row
            for row in pre_operations
            if str(row.get("data_abertura", "")).startswith(prefix)
        ]
        day_decisions = [
            row
            for row in decisions
            if str(row.get("data", "")).startswith(prefix)
        ]
        day_errors = [
            line
            for line in errors
            if (_parse_datetime(line) or datetime.min).date() == current
        ]
        days.append({
            "date": current.strftime("%d/%m/%Y"),
            "studies": len(day_preops),
            "entries": sum(row.get("decisao") == "ENTRAR" for row in day_decisions),
            "blocks": sum(row.get("decisao") == "BLOQUEAR" for row in day_decisions),
            "observations": sum(
                row.get("decisao") == "OBSERVAR"
                for row in day_decisions
            ),
            "errors": len(day_errors),
        })
        current += timedelta(days=1)
    return days


def build_weekly_audit(reference_date=None):
    reference_date = reference_date or date.today()
    start_date = reference_date - timedelta(days=6)
    start = datetime.combine(start_date, time.min)
    end = datetime.combine(reference_date, time.max)
    pre_operations = [
        row
        for row in _read_csv(PRE_OPERATIONS_FILE)
        if _in_period(row.get("data_abertura"), start, end)
    ]
    decisions = [
        row
        for row in _read_csv(DECISIONS_FILE)
        if _in_period(row.get("data"), start, end)
    ]
    orders = [
        row
        for row in _read_csv(ORDERS_FILE)
        if _in_period(row.get("data"), start, end)
        and row.get("status") == "ENVIADA"
    ]
    errors = _error_lines(start, end)
    human = _human_analysis_metrics(start, end)
    findings = _build_findings(
        pre_operations,
        decisions,
        errors,
        human,
        executed_operation_ids={
            row.get("pre_operation_id")
            for row in orders
            if row.get("pre_operation_id")
        },
    )
    reason_counts = Counter(
        str(row.get("motivo") or "SEM MOTIVO")
        for row in decisions
        if row.get("decisao") == "BLOQUEAR"
    )
    critical_groups = sum(item["severity"] == "CRITICO" for item in findings)
    high_groups = sum(item["severity"] == "ALTO" for item in findings)
    medium_groups = sum(item["severity"] == "MEDIO" for item in findings)
    score = max(
        0,
        100
        - critical_groups * 35
        - high_groups * 20
        - min(medium_groups, 3) * 8,
    )
    status = (
        "CRITICO"
        if critical_groups
        else "ATENCAO"
        if high_groups or medium_groups
        else "OK"
    )

    return {
        "generated_at": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
        "period_start": start_date.strftime("%d/%m/%Y"),
        "period_end": reference_date.strftime("%d/%m/%Y"),
        "reference_date": reference_date.isoformat(),
        "status": status,
        "score": score,
        "metrics": {
            "studies": len(pre_operations),
            "entries": sum(row.get("decisao") == "ENTRAR" for row in decisions),
            "blocks": sum(row.get("decisao") == "BLOQUEAR" for row in decisions),
            "observations": sum(
                row.get("decisao") == "OBSERVAR"
                for row in decisions
            ),
            "technical_errors": len(errors),
            "wins": sum(
                str(row.get("resultado", "")).startswith("WIN")
                for row in pre_operations
            ),
            "losses": sum(row.get("resultado") == "LOSS" for row in pre_operations),
        },
        "human_analyses": human,
        "findings": findings,
        "daily": _daily_summary(
            start_date,
            reference_date,
            pre_operations,
            decisions,
            errors,
        ),
        "top_block_reasons": [
            {"reason": reason, "count": count}
            for reason, count in reason_counts.most_common(5)
        ],
        "safety_note": (
            "A auditoria recomenda correções, mas não altera regras, risco ou "
            "execução automaticamente."
        ),
    }


def save_weekly_audit(audit):
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    path = REPORTS_DIR / f"weekly_audit_{audit['reference_date']}.json"
    path.write_text(
        json.dumps(audit, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return path
