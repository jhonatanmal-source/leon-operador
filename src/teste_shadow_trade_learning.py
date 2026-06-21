import tempfile
from pathlib import Path
from unittest.mock import patch

import shadow_trade


def candle(time, open_price, high, low, close):
    return {
        "time": time,
        "open": open_price,
        "high": high,
        "low": low,
        "close": close,
    }


def executar_teste():
    base = [
        candle(f"2026-06-18T10:{minute:02d}:00", 100, 102, 99, 101)
        for minute in range(10)
    ]
    base[-1] = candle("2026-06-18T10:09:00", 101, 102, 100, 101)

    with tempfile.TemporaryDirectory() as directory:
        file = Path(directory) / "shadow.csv"
        with patch.object(shadow_trade, "SHADOW_FILE", file):
            created = shadow_trade.register_shadow_trade(
                base,
                "COMPRA",
                ["FIBONACCI_ONDA_2_OU_4"],
                "evento-1",
            )
            duplicate = shadow_trade.register_shadow_trade(
                base,
                "COMPRA",
                ["FIBONACCI_ONDA_2_OU_4"],
                "evento-1",
            )
            target = float(created["shadow_trade"]["target"])
            later = base + [
                candle("2026-06-18T10:11:00", 101, target + 1, 100, target),
            ]
            evaluated = shadow_trade.evaluate_shadow_trades(later)

            assert created["ok"] is True
            assert duplicate["error"] == "SHADOW_EVENT_ALREADY_REGISTERED"
            assert evaluated["updated"] == ["SHADOW-000001"]
            assert shadow_trade._read()[0]["result"] == "WIN_2R"

    print("OK: bloqueio virou experiencia shadow e foi avaliado")


if __name__ == "__main__":
    executar_teste()
