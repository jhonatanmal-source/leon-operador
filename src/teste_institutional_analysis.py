import unittest

from institutional_analysis_engine import (
    analyze_elliott_context,
    analyze_smc_context,
    detect_liquidity_event,
)


def candle(open_price, high, low, close):
    return {
        "time": "",
        "open": open_price,
        "high": high,
        "low": low,
        "close": close,
    }


class InstitutionalAnalysisTests(unittest.TestCase):

    def test_liquidity_sweep_requires_close_back_inside(self):
        candles = [
            candle(100, 101 + index * 0.1, 99, 100)
            for index in range(21)
        ]
        candles.append(candle(100, 105, 99.5, 100.5))
        candles.append(candle(100.5, 101, 100, 100.2))

        event = detect_liquidity_event(candles)

        self.assertEqual(event["type"], "SWEEP_BUY_SIDE")
        self.assertEqual(event["direction"], "BEARISH")

    def test_elliott_does_not_force_count_without_pivots(self):
        candles = [
            candle(100 + index, 101 + index, 99 + index, 100.5 + index)
            for index in range(12)
        ]

        result = analyze_elliott_context(candles, "ALTA")

        self.assertFalse(result["valid"])
        self.assertEqual(result["label"], "SEM_CONTAGEM")

    def test_smc_stays_neutral_without_choch_bos_sequence(self):
        candles = [
            candle(100 + index, 101 + index, 99 + index, 100.5 + index)
            for index in range(30)
        ]

        result = analyze_smc_context(candles)

        self.assertEqual(result["smc"], "NEUTRO")


if __name__ == "__main__":
    unittest.main()
