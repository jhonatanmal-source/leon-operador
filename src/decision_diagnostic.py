"""Observability only: these classifications never authorize trades."""
import json
import os
import tempfile
from datetime import datetime, timezone
from src.paths import DATA_DIR

STATUS_FILE = DATA_DIR / "decision_diagnostic.json"
WAIT_CODES = {"NO_OPEN_PRE_OPERATION_TO_EXECUTE", "TOP_DOWN_M15_NOT_ALIGNED",
              "FIBONACCI_OU_LIQUIDEZ_NAO_CONFIRMADOS", "REGION_NOT_CONFIRMED",
              "DEMO_EXECUTION_INTERVAL_WAIT", "ANALYSIS_INTERVAL_WAIT",
              "TOP_DOWN_NOT_ALIGNED", "SMC_STRUCTURE_NOT_CONFIRMED"}
FAIL_CODES = {"ANALYSIS_FAILED", "ANALYSIS_EXCEPTION", "OPERATOR_TASK_EXCEPTION",
              "DAILY_LOSS_GUARD_UNAVAILABLE", "MT5_INITIALIZE_FAILED",
              "MT5_ACCOUNT_NOT_AVAILABLE", "MT5_POSITIONS_UNAVAILABLE",
              "MT5_RECONCILIATION_REQUIRED", "MT5_ORDER_RESULT_UNKNOWN_RECONCILIATION_REQUIRED",
              "NEWS_CALENDAR_UNAVAILABLE_OR_STALE", "FTMO_HISTORY_UNAVAILABLE"}


def classify(result):
    code = str(result.get("error") or result.get("reason") or "")
    if result.get("ok") and not code:
        return {"category": "COMPLETED", "code": "CYCLE_COMPLETED"}
    category = "WAIT" if code in WAIT_CODES else "FAIL" if code in FAIL_CODES else "BLOCKED"
    return {"category": category, "code": code or "UNCLASSIFIED_RESULT"}


def read_status():
    try:
        value = json.loads(STATUS_FILE.read_text(encoding="utf-8"))
        return value if isinstance(value, dict) else {}
    except (OSError, ValueError):
        return {}


def record(source, result, reasons=None):
    # Only stable outcome codes are persisted, never broker account details.
    status = read_status()
    outcome = classify(result)
    if reasons:
        outcome["category"] = "WAIT" if result.get("ok") else outcome["category"]
        outcome["reasons"] = list(dict.fromkeys(reasons))
    outcome["updated_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    status[source] = outcome
    STATUS_FILE.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(dir=STATUS_FILE.parent, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(status, stream, ensure_ascii=False, indent=2)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, STATUS_FILE)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
    return outcome
