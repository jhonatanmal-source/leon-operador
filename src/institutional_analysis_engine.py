from statistics import median

from elliott_study_engine import validate_impulse_points


def _closed_candles(candles):
    return candles[:-1] if len(candles) > 1 else candles


def detect_pivots(candles, window=2):
    closed = _closed_candles(candles)
    pivots = []

    for index in range(window, len(closed) - window):
        current = closed[index]
        neighbors = closed[index - window:index] + closed[index + 1:index + window + 1]
        if current["high"] > max(candle["high"] for candle in neighbors):
            pivots.append({
                "index": index,
                "type": "HIGH",
                "price": current["high"],
                "time": current.get("time"),
            })
        if current["low"] < min(candle["low"] for candle in neighbors):
            pivots.append({
                "index": index,
                "type": "LOW",
                "price": current["low"],
                "time": current.get("time"),
            })

    pivots.sort(key=lambda pivot: pivot["index"])
    alternating = []
    for pivot in pivots:
        if not alternating or alternating[-1]["type"] != pivot["type"]:
            alternating.append(pivot)
            continue

        previous = alternating[-1]
        more_extreme = (
            pivot["price"] > previous["price"]
            if pivot["type"] == "HIGH"
            else pivot["price"] < previous["price"]
        )
        if more_extreme:
            alternating[-1] = pivot

    return alternating


def _structure_bias(pivots):
    highs = [pivot["price"] for pivot in pivots if pivot["type"] == "HIGH"]
    lows = [pivot["price"] for pivot in pivots if pivot["type"] == "LOW"]
    if len(highs) < 2 or len(lows) < 2:
        return "NEUTRO"
    if highs[-1] > highs[-2] and lows[-1] > lows[-2]:
        return "BULLISH"
    if highs[-1] < highs[-2] and lows[-1] < lows[-2]:
        return "BEARISH"
    return "NEUTRO"


def _displacement(candles, index):
    if index < 0 or index >= len(candles):
        return False
    current = candles[index]
    body = abs(current["close"] - current["open"])
    candle_range = current["high"] - current["low"]
    recent_bodies = [
        abs(candle["close"] - candle["open"])
        for candle in candles[max(0, index - 20):index]
    ]
    baseline = median(recent_bodies) if recent_bodies else 0
    return (
        candle_range > 0
        and body / candle_range >= 0.6
        and (baseline == 0 or body >= baseline * 1.35)
    )


def detect_structure_events(candles, pivots):
    closed = _closed_candles(candles)
    events = []
    broken = set()
    flow = "NEUTRO"

    for index, candle in enumerate(closed):
        available = [pivot for pivot in pivots if pivot["index"] < index]
        highs = [pivot for pivot in available if pivot["type"] == "HIGH"]
        lows = [pivot for pivot in available if pivot["type"] == "LOW"]

        if highs:
            pivot = highs[-1]
            key = ("HIGH", pivot["index"])
            if key not in broken and candle["close"] > pivot["price"]:
                event_type = (
                    "CHOCH_BULLISH" if flow == "BEARISH" else "BOS_BULLISH"
                )
                flow = "BULLISH"
                broken.add(key)
                events.append({
                    "index": index,
                    "direction": "BULLISH",
                    "type": event_type,
                    "level": pivot["price"],
                    "close": candle["close"],
                    "displacement": _displacement(closed, index),
                    "time": candle.get("time"),
                })

        if lows:
            pivot = lows[-1]
            key = ("LOW", pivot["index"])
            if key not in broken and candle["close"] < pivot["price"]:
                event_type = (
                    "CHOCH_BEARISH" if flow == "BULLISH" else "BOS_BEARISH"
                )
                flow = "BEARISH"
                broken.add(key)
                events.append({
                    "index": index,
                    "direction": "BEARISH",
                    "type": event_type,
                    "level": pivot["price"],
                    "close": candle["close"],
                    "displacement": _displacement(closed, index),
                    "time": candle.get("time"),
                })

    return events


def _latest_fvg_near_event(candles, direction, event_index):
    closed = _closed_candles(candles)
    start = max(2, event_index - 2)
    end = min(len(closed), event_index + 4)

    for index in range(end - 1, start - 1, -1):
        first = closed[index - 2]
        third = closed[index]
        later = closed[index + 1:]

        if direction == "BULLISH" and third["low"] > first["high"]:
            mitigated = any(candle["low"] <= first["high"] for candle in later)
            return {
                "type": "FVG_BULLISH",
                "start": first["high"],
                "end": third["low"],
                "mitigated": mitigated,
                "index": index,
            }

        if direction == "BEARISH" and third["high"] < first["low"]:
            mitigated = any(candle["high"] >= first["low"] for candle in later)
            return {
                "type": "FVG_BEARISH",
                "start": third["high"],
                "end": first["low"],
                "mitigated": mitigated,
                "index": index,
            }

    return None


def detect_liquidity_event(candles, lookback=20):
    closed = _closed_candles(candles)
    if len(closed) < lookback + 2:
        return {"type": "SEM_EVENTO", "direction": None}

    for index in range(len(closed) - 1, max(lookback, len(closed) - 6), -1):
        current = closed[index]
        previous = closed[index - lookback:index]
        previous_high = max(candle["high"] for candle in previous)
        previous_low = min(candle["low"] for candle in previous)

        if current["high"] > previous_high and current["close"] < previous_high:
            return {
                "type": "SWEEP_BUY_SIDE",
                "direction": "BEARISH",
                "level": previous_high,
                "index": index,
            }
        if current["low"] < previous_low and current["close"] > previous_low:
            return {
                "type": "SWEEP_SELL_SIDE",
                "direction": "BULLISH",
                "level": previous_low,
                "index": index,
            }

    return {"type": "SEM_EVENTO", "direction": None}


def _event_pair(events):
    for bos in reversed(events):
        if not bos["type"].startswith("BOS_") or not bos["displacement"]:
            continue
        expected_choch = f"CHOCH_{bos['direction']}"
        choch = next(
            (
                event for event in reversed(events)
                if event["index"] < bos["index"]
                and event["type"] == expected_choch
            ),
            None,
        )
        if choch:
            return choch, bos
    return None, None


def analyze_smc_context(candles):
    closed = _closed_candles(candles)
    pivots = detect_pivots(candles)
    events = detect_structure_events(candles, pivots)
    choch_event, bos_event = _event_pair(events)
    liquidity = detect_liquidity_event(candles)

    if not bos_event:
        return {
            "direction": None,
            "smc": "NEUTRO",
            "bos": "SEM_BOS",
            "choch": "SEM_CHOCH",
            "fvg": "SEM_FVG_CONFIRMADO",
            "fvg_zone": None,
            "liquidity": liquidity,
            "poi_score": 0,
            "structure_bias": _structure_bias(pivots),
            "pivots": pivots,
            "events": events,
            "reason": "SEM_SEQUENCIA_CHOCH_BOS_COM_DESLOCAMENTO",
        }

    direction = bos_event["direction"]
    fvg = _latest_fvg_near_event(candles, direction, bos_event["index"])
    expected_fvg = f"FVG_{direction}"
    range_high = max((pivot["price"] for pivot in pivots if pivot["type"] == "HIGH"), default=0)
    range_low = min((pivot["price"] for pivot in pivots if pivot["type"] == "LOW"), default=0)
    midpoint = (range_high + range_low) / 2 if range_high > range_low else 0
    current_price = closed[-1]["close"] if closed else 0
    premium_discount_ok = (
        current_price <= midpoint
        if direction == "BULLISH"
        else current_price >= midpoint
    )
    liquidity_aligned = liquidity.get("direction") == direction

    poi_score = 25
    if fvg and fvg["type"] == expected_fvg:
        poi_score += 20
    if liquidity_aligned:
        poi_score += 20
    if fvg and not fvg["mitigated"]:
        poi_score += 15
    if premium_discount_ok:
        poi_score += 10
    if _structure_bias(pivots) == direction:
        poi_score += 10

    confirmed = (
        fvg is not None
        and fvg["type"] == expected_fvg
        and not fvg["mitigated"]
        and poi_score >= 70
    )

    return {
        "direction": direction,
        "smc": direction if confirmed else "NEUTRO",
        "bos": bos_event["type"],
        "bos_event": bos_event,
        "choch": choch_event["type"],
        "choch_event": choch_event,
        "fvg": fvg["type"] if fvg else "SEM_FVG_CONFIRMADO",
        "fvg_zone": fvg,
        "liquidity": liquidity,
        "poi_score": poi_score,
        "structure_bias": _structure_bias(pivots),
        "pivots": pivots,
        "events": events,
        "reason": "SMC_CONFIRMADO" if confirmed else "POI_OU_FVG_NAO_CONFIRMADO",
    }


def _partial_wave_three(points, direction):
    if len(points) < 4:
        return False
    p0, p1, p2, p3 = points[-4:]
    if direction == "ALTA":
        return p1 > p0 and p2 > p0 and p3 > p1
    return p1 < p0 and p2 < p0 and p3 < p1


def analyze_fibonacci_wave_setup(pivots, direction):
    result = {
        "valid": False,
        "target_wave": None,
        "retracement": None,
        "preferred_zone": None,
        "projection": None,
        "reason": "SEM_ESTRUTURA_FIBONACCI",
    }
    if direction not in ["ALTA", "BAIXA"]:
        return result

    wave_five_types = (
        ["LOW", "HIGH", "LOW", "HIGH", "LOW"]
        if direction == "ALTA"
        else ["HIGH", "LOW", "HIGH", "LOW", "HIGH"]
    )
    if len(pivots) >= 5 and [pivot["type"] for pivot in pivots[-5:]] == wave_five_types:
        p0, p1, p2, p3, p4 = [pivot["price"] for pivot in pivots[-5:]]
        wave_three = abs(p3 - p2)
        retracement = abs(p3 - p4) / wave_three if wave_three > 0 else 0
        structure_ok = (
            p3 > p1 and p4 > p2
            if direction == "ALTA"
            else p3 < p1 and p4 < p2
        )
        if structure_ok and 0.382 <= retracement <= 0.5:
            wave_one = abs(p1 - p0)
            projection = p4 + wave_one if direction == "ALTA" else p4 - wave_one
            return {
                "valid": True,
                "target_wave": "ONDA 5",
                "retracement": round(retracement, 4),
                "preferred_zone": [0.382, 0.5],
                "projection": round(projection, 2),
                "reason": "ONDA_4_NA_ZONA_FIBONACCI",
                "pivots": pivots[-5:],
            }

    wave_three_types = (
        ["LOW", "HIGH", "LOW"]
        if direction == "ALTA"
        else ["HIGH", "LOW", "HIGH"]
    )
    if len(pivots) >= 3 and [pivot["type"] for pivot in pivots[-3:]] == wave_three_types:
        p0, p1, p2 = [pivot["price"] for pivot in pivots[-3:]]
        wave_one = abs(p1 - p0)
        retracement = abs(p1 - p2) / wave_one if wave_one > 0 else 0
        origin_preserved = p2 > p0 if direction == "ALTA" else p2 < p0
        if origin_preserved and 0.618 <= retracement <= 0.786:
            projection = (
                p2 + wave_one * 1.618
                if direction == "ALTA"
                else p2 - wave_one * 1.618
            )
            return {
                "valid": True,
                "target_wave": "ONDA 3",
                "retracement": round(retracement, 4),
                "preferred_zone": [0.618, 0.786],
                "projection": round(projection, 2),
                "reason": "ONDA_2_NA_ZONA_FIBONACCI",
                "pivots": pivots[-3:],
            }

    return result


def analyze_elliott_context(candles, trend):
    pivots = detect_pivots(candles)
    points = [pivot["price"] for pivot in pivots]
    types = [pivot["type"] for pivot in pivots]
    direction = "ALTA" if trend == "ALTA" else "BAIXA" if trend == "BAIXA" else None

    result = {
        "label": "SEM_CONTAGEM",
        "phase": "INDEFINIDA",
        "direction": direction,
        "valid": False,
        "confidence": 0,
        "invalidation": None,
        "alternative": "CORRECAO_COMPLEXA",
        "pivots": pivots,
        "fibonacci_setup": analyze_fibonacci_wave_setup(pivots, direction),
    }
    if direction is None or len(points) < 4:
        return result

    fibonacci_setup = result["fibonacci_setup"]
    if fibonacci_setup["valid"]:
        result.update({
            "label": fibonacci_setup["target_wave"],
            "phase": "CORRECAO_CONCLUIDA_AGUARDANDO_SMC",
            "valid": True,
            "confidence": 80,
            "invalidation": points[-1],
            "alternative": "CONTAGEM_INVALIDA_SE_PERDER_ORIGEM_DA_CORRECAO",
        })
        return result

    expected_start = "LOW" if direction == "ALTA" else "HIGH"
    if len(points) >= 6 and types[-6] == expected_start:
        validation = validate_impulse_points(points[-6:], direction)
        if validation["valid"]:
            result.update({
                "label": "ONDA 5 CONCLUIDA",
                "phase": "IMPULSO_COMPLETO",
                "valid": True,
                "confidence": 75,
                "invalidation": points[-2],
                "validation": validation,
                "alternative": "TRUNCAMENTO_OU_CORRECAO_INICIANDO",
            })
            return result

    if types[-4] == expected_start and _partial_wave_three(points, direction):
        result.update({
            "label": "POSSIVEL ONDA 3",
            "phase": "IMPULSO_EM_DESENVOLVIMENTO",
            "valid": True,
            "confidence": 70,
            "invalidation": points[-2],
            "alternative": "PERNA_C_DE_ZIGUE_ZAGUE",
        })
        return result

    result.update({
        "label": "CORRECAO",
        "phase": "ABC_OU_COMBINACAO",
        "confidence": 35,
        "invalidation": points[-1] if points else None,
    })
    return result
