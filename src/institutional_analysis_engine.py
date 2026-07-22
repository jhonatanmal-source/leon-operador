from statistics import median

from src.elliott_study_engine import validate_impulse_points

# ─── Detecção de Correção ABC ────────────────────────────────────────────────


def _abc_quad(pivots, direction):
    """Extrai 4 pivots alternados (w0, a, b, c) para formar uma correção ABC.

    w0 → a = onda A
    a  → b = onda B
    b  → c = onda C

    Para direction='ALTA' (correção baixista): espera HIGH, LOW, HIGH, LOW.
    Para direction='BAIXA' (correção altista):  espera LOW, HIGH, LOW, HIGH.

    Retorna (w0_price, a_price, b_price, c_price) ou None.
    """
    if direction == "ALTA":
        expected = ["HIGH", "LOW", "HIGH", "LOW"]
    elif direction == "BAIXA":
        expected = ["LOW", "HIGH", "LOW", "HIGH"]
    else:
        return None

    if len(pivots) < 4:
        return None

    types = [p["type"] for p in pivots]

    # Procura o padrão nos últimos pivots primeiro (mais recentes)
    for start in range(len(types) - 3, -1, -1):
        if types[start:start + 4] == expected:
            prices = [pivots[start + i]["price"] for i in range(4)]
            return tuple(prices)

    return None


def _abc_subtype(w0, a, b, c, direction):
    """Classifica o subtipo de correção ABC com base nos 4 preços (w0, a, b, c).

    w0 = início da onda A
    a  = fim da onda A / início da onda B
    b  = fim da onda B / início da onda C
    c  = fim da onda C
    """
    wave_a = abs(a - w0)
    wave_b = abs(b - a)
    wave_c = abs(c - b)

    if wave_a == 0:
        return "INDEFINIDO"

    b_retrace = wave_b / wave_a
    c_ratio = wave_c / wave_a

    # --- Zigzag: onda C estende além de A, B retrace moderado ---
    if 0.382 <= b_retrace <= 0.886 and c_ratio >= 1.0:
        return "ZIGZAG"

    # --- Flat: B retrace profundo (quase até a origem de A), C ≈ A ---
    if b_retrace >= 0.886 and 0.886 <= c_ratio <= 1.15:
        return "FLAT"

    # --- Flat estendido: B retrace profundo, C um pouco além de A ---
    if b_retrace >= 0.886 and 1.15 < c_ratio <= 1.382:
        return "FLAT_ESTENDIDO"

    # --- Range / correção curta: C não alcança extensão de A ---
    if c_ratio < 0.886:
        return "RANGE"

    return "INDEFINIDO"


def detect_abc_correction(pivots, direction):
    """Detecta estrutura de correção ABC (3 ondas) nos pivots.

    Retorna um dict com:
        valid          — bool
        subtype        — ZIGZAG | FLAT | FLAT_ESTENDIDO | RANGE | INDEFINIDO
        w0_price       — preço de início da onda A
        a_price        — preço fim da onda A / início da onda B
        b_price        — preço fim da onda B / início da onda C
        c_price        — preço fim da onda C
        b_retrace      — retracement de B em relação a A (ratio)
        c_extension    — extensão de C em relação a A (ratio)
        confidence     — 0..100
        reason         — string descritiva
        invalidation   — preço que invalida a contagem
    """
    result = {
        "valid": False,
        "subtype": "",
        "w0_price": None,
        "a_price": None,
        "b_price": None,
        "c_price": None,
        "b_retrace": None,
        "c_extension": None,
        "confidence": 0,
        "reason": "SEM_ABC_DETECTADO",
        "invalidation": None,
    }

    quad = _abc_quad(pivots, direction)
    if quad is None:
        return result

    w0, a, b, c = quad
    wave_a = abs(a - w0)

    if wave_a == 0:
        return result

    wave_b = abs(b - a)
    wave_c = abs(c - b)
    b_retrace = wave_b / wave_a
    c_extension = wave_c / wave_a

    subtype = _abc_subtype(w0, a, b, c, direction)
    if subtype == "INDEFINIDO":
        result.update({
            "valid": False,
            "subtype": subtype,
            "w0_price": w0,
            "a_price": a,
            "b_price": b,
            "c_price": c,
            "b_retrace": round(b_retrace, 4),
            "c_extension": round(c_extension, 4),
            "confidence": 20,
            "reason": "ABC_SEM_CLAREZA_DE_SUBTIPO",
            "invalidation": b,
        })
        return result

    # Calcula confiança baseada na clareza estrutural
    confidence = 45  # base para qualquer ABC detectado
    if subtype == "ZIGZAG":
        confidence = 55
        if 1.272 <= c_extension <= 1.618:
            confidence = 65  # proporção áurea ideal
    elif subtype == "FLAT":
        confidence = 50
        if 0.95 <= c_extension <= 1.05:
            confidence = 60  # flat perfeito

    result.update({
        "valid": True,
        "subtype": subtype,
        "w0_price": w0,
        "a_price": a,
        "b_price": b,
        "c_price": c,
        "b_retrace": round(b_retrace, 4),
        "c_extension": round(c_extension, 4),
        "confidence": confidence,
        "reason": f"ABC_{subtype}_DETECTADO",
        "invalidation": b,  # perda de B invalida contagem ABC
    })
    return result


# ─── Fim Detecção de Correção ABC ────────────────────────────────────────────


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
        and body / candle_range >= 0.35
        and (baseline == 0 or body >= baseline * 1.15)
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
    # Primeiro: tenta par CHOCH+BOS (reversao)
    for bos in reversed(events):
        if not bos["type"].startswith("BOS_"):
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
    # Segundo: se nao achou par, aceita BOS sozinho (tendencia)
    for bos in reversed(events):
        if bos["type"].startswith("BOS_"):
            return None, bos
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
        poi_score >= 35
        and (
            (choch_event is not None and bos_event is not None)
            or (bos_event is not None and liquidity_aligned)
            or (fvg is not None and fvg["type"] == expected_fvg and not fvg["mitigated"])
            or (bos_event is not None and _structure_bias(pivots) == direction)
        )
    )

    return {
        "direction": direction,
        "smc": direction if confirmed else "NEUTRO",
        "bos": bos_event["type"],
        "bos_event": bos_event,
        "choch": choch_event["type"] if choch_event else "SEM_CHOCH",
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
        # --- Campos para InterestZone (mapeamento direto) ---
        "scenario_present": False,
        "scenario_type": "",
        "possible_wave_c": False,
        "impulse_possible": False,
        "correction_possible": False,
        "correction_detected": False,
        "correction_subtype": "",
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
            "scenario_present": True,
            "scenario_type": fibonacci_setup["target_wave"],
            "impulse_possible": True,
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
                "scenario_present": True,
                "scenario_type": "IMPULSO_COMPLETO",
                "impulse_possible": True,
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
            "scenario_present": True,
            "scenario_type": "IMPULSO_EM_DESENVOLVIMENTO",
            "impulse_possible": True,
        })
        return result

    # --- Tenta detecção estruturada de ABC antes do fallback genérico ---
    abc = detect_abc_correction(pivots, direction)
    if abc["valid"]:
        result.update({
            "label": f"ABC_{abc['subtype']}",
            "phase": f"CORRECAO_{abc['subtype']}",
            "valid": True,
            "confidence": abc["confidence"],
            "invalidation": abc["invalidation"],
            "alternative": "IMPULSO_PODE_ESTAR_SE_FORMANDO",
            "abc_detection": abc,
            "scenario_present": True,
            "scenario_type": f"ABC_{abc['subtype']}",
            "possible_wave_c": True,
            "correction_possible": True,
            "correction_detected": True,
            "correction_subtype": abc["subtype"],
        })
        return result

    # --- Fallback genérico: padrão corretivo não identificado ---
    result.update({
        "label": "CORRECAO",
        "phase": "ABC_OU_COMBINACAO",
        "confidence": 35,
        "invalidation": points[-1] if points else None,
        "correction_possible": True,
    })
    return result
