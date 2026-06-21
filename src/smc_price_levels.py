import csv
from pathlib import Path


CANDLE_FILE = Path(__file__).resolve().parent.parent / "data" / "candle_history.csv"


def load_candles(limit=120):
    if not CANDLE_FILE.exists():
        return []

    candles = []
    try:
        with CANDLE_FILE.open("r", encoding="utf-8", newline="") as file:
            for row in csv.reader(file, delimiter=";"):
                if len(row) < 6:
                    continue
                try:
                    candles.append({
                        "time": row[0],
                        "open": float(row[2]),
                        "high": float(row[3]),
                        "low": float(row[4]),
                        "close": float(row[5]),
                    })
                except ValueError:
                    continue
    except (OSError, csv.Error):
        return []

    return candles[-limit:]


def detect_swing_levels(candles):
    highs = []
    lows = []

    for index in range(1, len(candles) - 1):
        previous = candles[index - 1]
        current = candles[index]
        following = candles[index + 1]

        if current["high"] > previous["high"] and current["high"] >= following["high"]:
            highs.append(current["high"])
        if current["low"] < previous["low"] and current["low"] <= following["low"]:
            lows.append(current["low"])

    return sorted(set(highs)), sorted(set(lows))


def detect_latest_fvg(candles, direction):
    expected = "BULLISH" if direction == "COMPRA" else "BEARISH"

    for index in range(len(candles) - 1, 1, -1):
        first = candles[index - 2]
        third = candles[index]
        later_candles = candles[index + 1:]

        if expected == "BULLISH" and third["low"] > first["high"]:
            if any(candle["low"] <= first["high"] for candle in later_candles):
                continue
            return {
                "type": "FVG_BULLISH",
                "start": first["high"],
                "end": third["low"],
            }

        if expected == "BEARISH" and third["high"] < first["low"]:
            if any(candle["high"] >= first["low"] for candle in later_candles):
                continue
            return {
                "type": "FVG_BEARISH",
                "start": third["high"],
                "end": first["low"],
            }

    return None


def build_smc_trade_levels(direction, min_rr=1.0, candles=None, entry_price=None):
    candles = candles or load_candles()
    if len(candles) < 5:
        return None

    swing_highs, swing_lows = detect_swing_levels(candles)
    fvg = detect_latest_fvg(candles, direction)
    if fvg is None:
        return None

    entry = (
        float(entry_price)
        if entry_price is not None
        else (fvg["start"] + fvg["end"]) / 2
    )
    current_price = candles[-1]["close"]
    zone_low = min(fvg["start"], fvg["end"])
    zone_high = max(fvg["start"], fvg["end"])

    if not zone_low <= current_price <= zone_high:
        return None

    if direction == "COMPRA":
        stops = [level for level in swing_lows if level < entry]
        targets = [level for level in swing_highs if level > entry]
        if not stops or not targets:
            return None
        stop = stops[-1]
        targets.sort()

    elif direction == "VENDA":
        stops = [level for level in swing_highs if level > entry]
        targets = [level for level in swing_lows if level < entry]
        if not stops or not targets:
            return None
        stop = stops[0]
        targets.sort(reverse=True)

    else:
        return None

    risk = abs(entry - stop)
    if risk <= 0:
        return None

    valid_targets = [
        target
        for target in targets
        if abs(target - entry) / risk >= float(min_rr)
    ]
    if not valid_targets:
        return None

    tp1 = targets[0]
    tp2 = valid_targets[0]

    return {
        "entry": round(entry, 2),
        "stop": round(stop, 2),
        "tp1": round(tp1, 2),
        "tp2": round(tp2, 2),
        "fvg": fvg,
        "current_price": round(current_price, 2),
        "technical_rr": round(abs(tp2 - entry) / risk, 2),
        "source": "FVG_REAL + SWINGS + LIQUIDEZ",
    }
