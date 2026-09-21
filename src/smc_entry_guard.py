VALID_DIRECTIONS = {"COMPRA", "VENDA"}


def infer_candidate_direction(context_direction, bos, choch):
    if context_direction == "BULLISH":
        return "COMPRA"
    if context_direction == "BEARISH":
        return "VENDA"
    if bos == "BOS_BULLISH" and choch == "CHOCH_BULLISH":
        return "COMPRA"
    if bos == "BOS_BEARISH" and choch == "CHOCH_BEARISH":
        return "VENDA"
    return "AGUARDAR"


def expected_structure(direction):
    if direction == "COMPRA":
        return {
            "smc": "BULLISH",
            "bos": "BOS_BULLISH",
            "choch": "CHOCH_BULLISH",
            "fvg": "FVG_BULLISH",
        }
    if direction == "VENDA":
        return {
            "smc": "BEARISH",
            "bos": "BOS_BEARISH",
            "choch": "CHOCH_BEARISH",
            "fvg": "FVG_BEARISH",
        }
    return None


def classify_operational_smc(direction, bos, choch, fvg):
    expected = expected_structure(direction)
    if expected is None:
        return "NEUTRO"

    if (
        bos == expected["bos"]
        and choch == expected["choch"]
        and fvg == expected["fvg"]
    ):
        return expected["smc"]

    return "NEUTRO"


def confirmed_shift_direction(smc_context, region):
    """A current CHOCH gets a candidate only after its own prospective retest."""
    region = region or {}
    event = smc_context.get('choch_event') or {}
    source = region.get('source_bos') or {}
    if (smc_context.get('bos_event') or region.get('structure_model') != 'CHOCH_RETEST'
            or event.get('time') != source.get('time') or event.get('type') != source.get('type')
            or event.get('direction') != region.get('region_direction')
            or event.get('displacement') is not True):
        return 'AGUARDAR'
    return {'BULLISH':'COMPRA','BEARISH':'VENDA'}.get(region.get('region_direction'),'AGUARDAR')


def validate_smc_entry(direction, smc, bos, choch, *, region_id='', pre_operation_id=None, symbol=None):
    expected = expected_structure(direction)
    if expected is None:
        return {
            "approved": False,
            "reason": "INVALID_ORDER_DIRECTION",
        }

    bos_ok = bos == expected["bos"]
    choch_ok = choch == expected["choch"]

    if not bos_ok and bos == 'SEM_BOS' and choch_ok and region_id:
        from src.interest_zone_engine import validate_zone_for_execution
        # Reload canonical evidence, never trust a flag supplied by the caller.
        check = validate_zone_for_execution({'region_id':region_id, 'id':pre_operation_id, 'ativo':symbol})
        zone = check.get('region') or {}
        event = zone.get('source_bos') or {}
        if (check.get('ok') and zone.get('zone_source') == 'REAL_M15_OB_V1'
                and zone.get('structure_model') == 'CHOCH_RETEST'
                and zone.get('region_direction') == expected['smc']
                and event.get('type') == expected['choch'] and event.get('displacement') is True):
            return {'approved':True,'reason':'SMC_DISPLACED_CHOCH_CANONICAL_RETEST',
                    'expected':expected,'region_id':region_id}

    # ── SMC context: accept exact match OR ABC_RANGE with aligned BOS+CHOCH ──
    # ABC_RANGE means the market is in correction/consolidation, but when the
    # microstructure (BOS + CHOCH) confirms a direction, the range should not
    # block entries. This matches real market behavior where trends emerge
    # from ranges.
    smc_ok = smc == expected["smc"] or (
        smc == "ABC_RANGE" and bos_ok and choch_ok
    )

    # ── Detect if ABC_RANGE was accepted (structure confirmed via BOS+CHOCH) ──
    smc_is_abc_range = smc == "ABC_RANGE" and smc_ok and (bos_ok and choch_ok)
    range_suffix = "_VIA_ABC_RANGE" if smc_is_abc_range else ""

    if smc_ok and bos_ok and choch_ok:
        return {
            "approved": True,
            "reason": f"SMC_STRUCTURE_CONFIRMED_CHOCH_BOS{range_suffix}",
            "expected": expected,
            "received": {
                "smc": smc,
                "bos": bos,
                "choch": choch,
            },
        }

    if smc_ok and bos_ok:
        return {
            "approved": True,
            "reason": f"SMC_STRUCTURE_CONFIRMED_BOS{range_suffix}",
            "expected": expected,
            "received": {
                "smc": smc,
                "bos": bos,
                "choch": choch,
            },
        }

    missing = []
    if not smc_ok:
        missing.append("SMC")
    if not bos_ok:
        missing.append("BOS")
    if not choch_ok:
        missing.append("CHOCH")

    return {
        "approved": False,
        "reason": (
            f"SMC_STRUCTURE_NOT_CONFIRMED:{','.join(missing)}"
        ),
        "expected": expected,
        "received": {
            "smc": smc,
            "bos": bos,
            "choch": choch,
        },
    }
