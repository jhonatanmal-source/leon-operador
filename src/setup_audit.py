import configparser
import csv
import json
from datetime import date, datetime
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT_DIR / "data"
REPORTS_DIR = ROOT_DIR / "reports"
CONFIG_FILE = ROOT_DIR / "config.ini"
PRE_OPERATION_FILE = DATA_DIR / "pre_operation_trades.csv"
ORDER_MEMORY_FILE = DATA_DIR / "mt5_order_memory.csv"


def _read_csv(path):
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8", newline="") as file:
        return list(csv.DictReader(file, delimiter=";"))


def _same_date(value, reference_date):
    try:
        return datetime.fromisoformat(value).date() == reference_date
    except (TypeError, ValueError):
        return False


def _execution_state():
    config = configparser.ConfigParser()
    config.read(CONFIG_FILE, encoding="utf-8")
    operator = config["OPERATOR"] if config.has_section("OPERATOR") else {}
    execution = config["EXECUTION"] if config.has_section("EXECUTION") else {}
    return {
        "demo_execution_enabled": (
            str(operator.get("demo_execution_enabled", "false")).lower()
            == "true"
        ),
        "execution_enabled": (
            str(execution.get("enabled", "false")).lower() == "true"
        ),
        "demo_only": str(execution.get("demo_only", "true")).lower() == "true",
    }


def audit_setup_records(pre_operations, orders, execution, reference_date):
    today_preops = [
        row
        for row in pre_operations
        if _same_date(row.get("data_abertura"), reference_date)
    ]
    today_orders = [
        row
        for row in orders
        if _same_date(row.get("data"), reference_date)
    ]

    order_ids = {
        row.get("pre_operation_id")
        for row in today_orders
        if row.get("status") == "ENVIADA"
    }
    executed = [
        row for row in today_preops
        if row.get("id") in order_ids
    ]
    structural_violations = [
        row for row in executed
        if (
            row.get("smc") not in ["BULLISH", "BEARISH"]
            or row.get("bos") not in ["BOS_BULLISH", "BOS_BEARISH"]
            or row.get("choch") not in ["CHOCH_BULLISH", "CHOCH_BEARISH"]
        )
    ]
    observed = [
        row for row in today_preops
        if row.get("status") == "OBSERVADO"
    ]
    protected_observations = [
        row for row in observed
        if (
            "SMC_STRUCTURE" in str(row.get("observacao"))
            or "INVALID_ORDER_DIRECTION" in str(row.get("observacao"))
        )
    ]
    open_preops = [
        row for row in pre_operations
        if row.get("status") == "ABERTO"
    ]

    current_safe = (
        not execution["demo_execution_enabled"]
        and not execution["execution_enabled"]
        and not open_preops
    )

    findings = []
    if structural_violations:
        findings.append({
            "severity": "CRITICAL",
            "code": "HISTORICAL_EXECUTION_WITHOUT_SMC",
            "count": len(structural_violations),
            "operations": [row.get("id") for row in structural_violations],
        })
    if protected_observations:
        findings.append({
            "severity": "POSITIVE",
            "code": "SMC_GUARD_BLOCKING_WEAK_SETUPS",
            "count": len(protected_observations),
        })
    if current_safe:
        findings.append({
            "severity": "POSITIVE",
            "code": "LEARNING_ONLY_MODE_ACTIVE",
            "count": 1,
        })

    if structural_violations:
        status = "HISTORICAL_VIOLATIONS"
    elif current_safe:
        status = "SAFE_LEARNING"
    else:
        status = "REVIEW_REQUIRED"

    return {
        "reference_date": reference_date.isoformat(),
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "status": status,
        "execution": execution,
        "metrics": {
            "pre_operations_today": len(today_preops),
            "orders_today": len(today_orders),
            "observed_today": len(observed),
            "protected_observations_today": len(protected_observations),
            "historical_structural_violations_today": len(structural_violations),
            "open_pre_operations": len(open_preops),
        },
        "findings": findings,
        "learning_rules": [
            "Analise sem resultado real nao conta como acerto ou erro.",
            "SMC neutro nunca aumenta reputacao operacional.",
            "BOS, CHOCH e FVG devem estar alinhados com a direcao.",
            "Resultado real do MT5 deve ser aprendido uma unica vez.",
            "Durante auditoria, coletar e observar sem enviar ordens.",
        ],
    }


def _format_text(audit):
    metrics = audit["metrics"]
    lines = [
        "LEON | AUDITORIA DO SETUP",
        "=========================",
        f"Data: {audit['reference_date']}",
        f"Status: {audit['status']}",
        "",
        f"Pre-operacoes: {metrics['pre_operations_today']}",
        f"Ordens enviadas: {metrics['orders_today']}",
        f"Observacoes: {metrics['observed_today']}",
        f"Bloqueios protetivos: {metrics['protected_observations_today']}",
        f"Violacoes estruturais historicas: {metrics['historical_structural_violations_today']}",
        f"Pre-operacoes abertas: {metrics['open_pre_operations']}",
        "",
        "Regras de aprendizado:",
    ]
    lines.extend(f"- {rule}" for rule in audit["learning_rules"])
    return "\n".join(lines)


def generate_setup_audit(reference_date=None):
    reference_date = reference_date or date.today()
    audit = audit_setup_records(
        _read_csv(PRE_OPERATION_FILE),
        _read_csv(ORDER_MEMORY_FILE),
        _execution_state(),
        reference_date,
    )

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    json_path = REPORTS_DIR / f"setup_audit_{reference_date.isoformat()}.json"
    text_path = REPORTS_DIR / f"setup_audit_{reference_date.isoformat()}.txt"
    json_path.write_text(
        json.dumps(audit, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    text = _format_text(audit)
    text_path.write_text(text, encoding="utf-8")
    return {
        "audit": audit,
        "text": text,
        "json_path": str(json_path),
        "text_path": str(text_path),
    }
