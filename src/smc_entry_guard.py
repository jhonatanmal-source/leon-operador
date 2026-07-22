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


def validate_smc_entry(direction, smc, bos, choch):
    expected = expected_structure(direction)
    if expected is None:
        return {
            "approved": False,
            "reason": "INVALID_ORDER_DIRECTION",
        }

    smc_ok = smc == expected["smc"]
    bos_ok = bos == expected["bos"]
    choch_ok = choch == expected["choch"]

    if smc_ok and bos_ok and choch_ok:
        return {
            "approved": True,
            "reason": "SMC_STRUCTURE_CONFIRMED_CHOCH_BOS",
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
            "reason": "SMC_STRUCTURE_CONFIRMED_BOS",
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
