import csv
from datetime import datetime
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parent.parent
SHADOW_FILE = ROOT_DIR / "data" / "shadow_trades.csv"
FIELDS = [
    "id",
    "opened_at",
    "closed_at",
    "symbol",
    "direction",
    "entry",
    "stop",
    "target",
    "missing_confirmations",
    "event_signature",
    "status",
    "result",
]


def _ensure_file():
    SHADOW_FILE.parent.mkdir(parents=True, exist_ok=True)
    if SHADOW_FILE.exists():
        return

    with SHADOW_FILE.open("w", encoding="utf-8", newline="") as file:
        csv.DictWriter(file, fieldnames=FIELDS, delimiter=";").writeheader()


def _read():
    _ensure_file()
    with SHADOW_FILE.open("r", encoding="utf-8", newline="") as file:
        return list(csv.DictReader(file, delimiter=";"))


def _write(rows):
    _ensure_file()
    with SHADOW_FILE.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=FIELDS, delimiter=";")
        writer.writeheader()
        writer.writerows(rows)


def _next_id(rows):
    if not rows:
        return "SHADOW-000001"
    try:
        number = int(rows[-1]["id"].split("-")[-1])
    except (KeyError, ValueError):
        number = len(rows)
    return f"SHADOW-{number + 1:06d}"


def register_shadow_trade(
    candles,
    direction,
    missing_confirmations,
    event_signature,
    symbol="Gold_Spot",
):
    if direction not in ["COMPRA", "VENDA"] or len(candles) < 10:
        return {"ok": False, "error": "INVALID_SHADOW_CONTEXT"}

    rows = _read()
    if any(row.get("event_signature") == event_signature for row in rows):
        return {"ok": False, "error": "SHADOW_EVENT_ALREADY_REGISTERED"}

    closed = candles[:-1] if len(candles) > 1 else candles
    entry_candle = closed[-1]
    entry = float(entry_candle["close"])

    # --- C4: Stop baseado em estrutura (zona), fallback swing expandido ---
    if direction == "COMPRA":
        try:
            from src.interest_zone_engine import find_nearest_zone
            zone = find_nearest_zone(direction, entry, candles)
            stop = zone["zone_stop"] if (zone and zone.get("zone_stop")) else min(float(c["low"]) for c in candles[-15:])
        except ImportError:
            stop = min(float(c["low"]) for c in candles[-15:])
        risk = entry - stop
    else:
        try:
            from src.interest_zone_engine import find_nearest_zone
            zone = find_nearest_zone(direction, entry, candles)
            stop = zone["zone_stop"] if (zone and zone.get("zone_stop")) else max(float(c["high"]) for c in candles[-15:])
        except ImportError:
            stop = max(float(c["high"]) for c in candles[-15:])
        risk = stop - entry

    # --- C3: TP baseado em níveis técnicos, fallback risk * 2 ---
    if direction == "COMPRA":
        try:
            from src.smc_price_levels import build_smc_trade_levels
            levels = build_smc_trade_levels(direction, min_rr=1.0, candles=candles, entry_price=entry)
            target = levels["tp2"] if (levels and levels.get("tp2")) else entry + risk * 2
        except ImportError:
            target = entry + risk * 2
    else:
        try:
            from src.smc_price_levels import build_smc_trade_levels
            levels = build_smc_trade_levels(direction, min_rr=1.0, candles=candles, entry_price=entry)
            target = levels["tp2"] if (levels and levels.get("tp2")) else entry - risk * 2
        except ImportError:
            target = entry - risk * 2

    if risk <= 0:
        return {"ok": False, "error": "INVALID_SHADOW_RISK"}

    row = {
        "id": _next_id(rows),
        "opened_at": entry_candle.get("time") or datetime.now().isoformat(timespec="seconds"),
        "closed_at": "",
        "symbol": symbol,
        "direction": direction,
        "entry": round(entry, 2),
        "stop": round(stop, 2),
        "target": round(target, 2),
        "missing_confirmations": ",".join(missing_confirmations),
        "event_signature": event_signature,
        "status": "ABERTO",
        "result": "EM_ESTUDO",
    }
    rows.append(row)
    _write(rows)
    return {"ok": True, "shadow_trade": row}


def evaluate_shadow_trades(candles):
    if not candles:
        return {"ok": False, "error": "NO_CANDLES"}

    rows = _read()
    updated = []

    for row in rows:
        if row.get("status") != "ABERTO":
            continue

        opened_at = row.get("opened_at") or ""
        later = [
            candle
            for candle in candles
            if str(candle.get("time") or "") > opened_at
        ]
        if not later:
            continue

        stop = float(row["stop"])
        target = float(row["target"])
        direction = row["direction"]

        for candle in later:
            stop_hit = (
                float(candle["low"]) <= stop
                if direction == "COMPRA"
                else float(candle["high"]) >= stop
            )
            target_hit = (
                float(candle["high"]) >= target
                if direction == "COMPRA"
                else float(candle["low"]) <= target
            )

            if not stop_hit and not target_hit:
                continue

            row["status"] = "FECHADO"
            row["closed_at"] = candle.get("time") or datetime.now().isoformat(timespec="seconds")
            row["result"] = "LOSS" if stop_hit else "WIN_2R"
            updated.append(row["id"])
            break

    if updated:
        _write(rows)

    return {"ok": True, "updated": updated}
