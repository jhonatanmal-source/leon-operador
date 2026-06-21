VALID_DIRECTIONS = {"COMPRA", "VENDA"}


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

    checks = {
        "smc": smc == expected["smc"],
        "bos": bos == expected["bos"],
        "choch": choch == expected["choch"],
    }
    missing = [name.upper() for name, valid in checks.items() if not valid]

    return {
        "approved": not missing,
        "reason": (
            "SMC_STRUCTURE_CONFIRMED"
            if not missing
            else f"SMC_STRUCTURE_NOT_CONFIRMED:{','.join(missing)}"
        ),
        "expected": expected,
        "received": {
            "smc": smc,
            "bos": bos,
            "choch": choch,
        },
    }
