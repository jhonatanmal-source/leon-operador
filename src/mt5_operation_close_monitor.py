import csv
import json
from datetime import datetime
from pathlib import Path

from src.pre_operation_engine import reconciliar_pre_operacao_mt5
from src.operational_evidence import record_confirmed_outcome, read_json
from src.obsidian_sync import sync_closed_trade


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
        import mt5_safe as mt5
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
        account = mt5.account_info()
        positions = mt5.positions_get()
        if account is None or positions is None:
            return {"ok": False, "error": "MT5_ACCOUNT_OR_POSITIONS_UNAVAILABLE", "operations": []}
        if account.trade_mode != mt5.ACCOUNT_TRADE_MODE_DEMO:
            return {"ok": False, "error": "DEMO_ACCOUNT_REQUIRED", "operations": []}
        account_key = f"{account.server}:{account.login}"
        open_ids = {int(getattr(p, "identifier", p.ticket)) for p in positions}
        if not START_FILE.exists():
            DATA_DIR.mkdir(parents=True, exist_ok=True)
            START_FILE.write_text(
                datetime.now().isoformat(timespec="seconds"),
                encoding="utf-8",
            )

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
            order_ticket = position_id
            metadata = read_json(DATA_DIR / "order_evidence" / f"{account.server}-{account.login}-{order_ticket}.json", {})
            broker_orders = mt5.history_orders_get(ticket=order_ticket)
            if broker_orders:
                position_id = int(broker_orders[0].position_id or order_ticket)
            if position_id in open_ids:
                continue
            deals = mt5.history_deals_get(position=position_id)
            if deals is None:
                continue
            if not any(int(d.order) == order_ticket and d.symbol == order.get("ativo") for d in deals):
                continue
            exits = [
                deal
                for deal in deals
                if deal.entry in [mt5.DEAL_ENTRY_OUT, mt5.DEAL_ENTRY_OUT_BY]
            ]
            if not exits:
                continue

            exit_deal = max(exits, key=lambda deal: (deal.time, deal.ticket))
            exit_datetime = datetime.fromtimestamp(exit_deal.time)
            net_profit = sum(float(d.profit) + float(d.commission) + float(d.swap) + float(d.fee) for d in deals)
            result = "WIN_TP2" if net_profit > 0 else "LOSS" if net_profit < 0 else "FECHADO_ZERO"
            closed_at = exit_datetime.isoformat(timespec="seconds")
            processed_key = f"{pre_operation_id}:{result}:{closed_at}"

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
                "actual_profit": round(net_profit, 2),
                "close_reason": reason,
                "data_fechamento": closed_at,
                "source": "MT5_DEMO_REAL",
                "position_id": position_id,
                "account_key": account_key,
                "currency": account.currency,
                "order_ticket": order_ticket,
                "deal_tickets": [int(d.ticket) for d in deals],
                "setup_version": metadata.get("setup_version", "LEGACY_UNVERIFIED_SETUP"),
                "entry_model": metadata.get("entry_model") or "UNSPECIFIED",
                "context_mode": metadata.get("context_mode") or "UNSPECIFIED",
                "selection_score_at_entry": metadata.get("selection_score"),
                "realized_r": round(net_profit / float(metadata["initial_risk"]), 4) if float(metadata.get("initial_risk") or 0) > 0 else None,
            })
            record_confirmed_outcome(operation)
            sync_closed_trade(operation)
            if processed_key in processed or exit_datetime < monitor_started_at:
                continue
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
