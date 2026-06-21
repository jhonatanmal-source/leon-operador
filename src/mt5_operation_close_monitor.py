import csv
import json
from datetime import datetime
from pathlib import Path

from pre_operation_engine import reconciliar_pre_operacao_mt5


ROOT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT_DIR / "data"
ORDER_MEMORY_FILE = DATA_DIR / "mt5_order_memory.csv"
PRE_OPERATION_FILE = DATA_DIR / "pre_operation_trades.csv"
START_FILE = DATA_DIR / "operation_close_monitor_started_at.txt"
PROCESSED_FILE = DATA_DIR / "mt5_closed_operations_processed.json"


def _read_csv(path):
    if not path.exists():
        return []

    with path.open("r", encoding="utf-8", newline="") as file:
        return list(csv.DictReader(file, delimiter=";"))


def _pre_operations_by_id():
    return {
        row.get("id"): row
        for row in _read_csv(PRE_OPERATION_FILE)
        if row.get("id")
    }


def _load_processed():
    if not PROCESSED_FILE.exists():
        return set()
    try:
        data = json.loads(PROCESSED_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return set()
    return set(data if isinstance(data, list) else [])


def _save_processed(processed):
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    PROCESSED_FILE.write_text(
        json.dumps(sorted(processed), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def _close_reason(mt5, deal):
    reasons = {
        mt5.DEAL_REASON_SL: "STOP LOSS",
        mt5.DEAL_REASON_TP: "TAKE PROFIT",
        mt5.DEAL_REASON_CLIENT: "FECHAMENTO MANUAL",
        mt5.DEAL_REASON_EXPERT: "FECHAMENTO PELO AGENTE",
    }
    return reasons.get(deal.reason, f"MT5_REASON_{deal.reason}")


def _result_from_deal(mt5, deal):
    if deal.reason == mt5.DEAL_REASON_SL or deal.profit < 0:
        return "LOSS"
    if deal.reason == mt5.DEAL_REASON_TP or deal.profit > 0:
        return "WIN_TP2"
    return "FECHADO_ZERO"


def check_mt5_closed_operations():
    try:
        import MetaTrader5 as mt5
    except ImportError:
        return {"ok": False, "error": "MT5_IMPORT_ERROR", "operations": []}

    if not mt5.initialize():
        return {
            "ok": False,
            "error": "MT5_INITIALIZE_FAILED",
            "details": str(mt5.last_error()),
            "operations": [],
        }

    operations = []
    sent_orders = [
        order
        for order in _read_csv(ORDER_MEMORY_FILE)
        if order.get("status") == "ENVIADA"
    ]
    executed_ids = {
        order.get("pre_operation_id")
        for order in sent_orders
        if order.get("pre_operation_id")
    }
    pre_operations = _pre_operations_by_id()
    processed = _load_processed()

    try:
        if not START_FILE.exists():
            DATA_DIR.mkdir(parents=True, exist_ok=True)
            START_FILE.write_text(
                datetime.now().isoformat(timespec="seconds"),
                encoding="utf-8",
            )
            return {
                "ok": True,
                "operations": [],
                "executed_ids": sorted(executed_ids),
                "baseline_initialized": True,
            }

        try:
            monitor_started_at = datetime.fromisoformat(
                START_FILE.read_text(encoding="utf-8").strip()
            )
        except (OSError, ValueError):
            monitor_started_at = datetime.now()

        for order in sent_orders:

            pre_operation_id = order.get("pre_operation_id")
            pre_operation = pre_operations.get(pre_operation_id)
            if not pre_operation:
                continue

            try:
                position_id = int(order.get("ticket") or 0)
            except ValueError:
                continue

            if position_id <= 0:
                continue

            deals = mt5.history_deals_get(position=position_id) or []
            exits = [
                deal
                for deal in deals
                if deal.entry in [mt5.DEAL_ENTRY_OUT, mt5.DEAL_ENTRY_OUT_BY]
            ]
            if not exits:
                continue

            exit_deal = exits[-1]
            exit_datetime = datetime.fromtimestamp(exit_deal.time)
            if exit_datetime < monitor_started_at:
                continue

            result = _result_from_deal(mt5, exit_deal)
            closed_at = exit_datetime.isoformat(timespec="seconds")
            processed_key = f"{pre_operation_id}:{result}:{closed_at}"
            if processed_key in processed:
                continue

            reason = _close_reason(mt5, exit_deal)
            observation = (
                f"Resultado reconciliado com MT5. {reason}; "
                f"preco {exit_deal.price}; lucro/prejuizo {exit_deal.profit}."
            )
            reconciliation = reconciliar_pre_operacao_mt5(
                pre_operation_id,
                result,
                closed_at,
                observation,
            )

            operation = dict(pre_operation)
            if reconciliation.get("ok"):
                operation.update(reconciliation["pre_operation"])
            operation.update({
                "id": pre_operation_id,
                "resultado": result,
                "actual_close_price": round(float(exit_deal.price), 2),
                "actual_profit": round(float(exit_deal.profit), 2),
                "close_reason": reason,
                "data_fechamento": closed_at,
                "source": "MT5_DEMO_REAL",
            })
            operations.append(operation)
            processed.add(processed_key)
            _save_processed(processed)
    finally:
        mt5.shutdown()

    return {
        "ok": True,
        "operations": operations,
        "executed_ids": sorted(executed_ids),
    }
