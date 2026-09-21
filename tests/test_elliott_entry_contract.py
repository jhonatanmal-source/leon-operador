import random
import unittest
from unittest.mock import patch

from src import institutional_analysis_engine as engine


def pivots(prices, direction="ALTA", start=None):
    first = start or ("LOW" if direction == "ALTA" else "HIGH")
    second = "HIGH" if first == "LOW" else "LOW"
    return [
        {"index": i * 3, "confirmed_index": i * 3 + 2,
         "price": price, "type": (first, second)[i % 2]}
        for i, price in enumerate(prices)
    ]


def mirror(prices, direction):
    return prices if direction == "ALTA" else [300 - p for p in prices]


def context(points, direction):
    with patch.object(engine, "detect_pivots", return_value=points):
        return engine.analyze_elliott_context([], direction)


class ElliottEntryContractTests(unittest.TestCase):
    def test_wave_five_valid_in_both_directions(self):
        for direction in ("ALTA", "BAIXA"):
            points = pivots(mirror([100, 120, 110, 150, 135], direction), direction)
            result = engine.analyze_fibonacci_wave_setup(points, direction)
            self.assertTrue(result["valid"])
            self.assertTrue(result["entry_eligible"])
            self.assertEqual(result["direction"], direction)
            self.assertEqual(result["target_wave"], "ONDA 5")
            self.assertIn("WAVE_3_NOT_SHORTEST_REQUIRES_WAVE_5", result["pending_rules"])
            self.assertEqual(result["projection"], 155 if direction == "ALTA" else 145)
            self.assertTrue(context(points, direction)["entry_eligible"])

    def test_wave_five_rejects_overlap_origin_and_wrong_legs(self):
        invalid = [
            [100, 120, 110, 125, 119],  # Study's 40% retracement, overlap.
            [100, 120, 110, 130, 120],  # Touching wave one.
            [100, 120, 100, 150, 135],  # Wave two reaches origin.
            [100, 120, 90, 150, 135],
            [100, 120, 125, 150, 140],  # Wave two in wrong direction.
            [100, 120, 110, 150, 165],  # Wave four in wrong direction.
            [120, 100, 90, 140, 125],  # Wave one in wrong direction.
        ]
        for direction in ("ALTA", "BAIXA"):
            for prices in invalid:
                with self.subTest(direction=direction, prices=prices):
                    result = engine.analyze_fibonacci_wave_setup(
                        pivots(mirror(prices, direction), direction), direction)
                    self.assertFalse(result["valid"])
                    self.assertFalse(result["entry_eligible"])
                    self.assertIsNone(result["target_wave"])

    def test_three_pivots_are_enough_for_fibonacci_wave_three(self):
        for direction in ("ALTA", "BAIXA"):
            result = context(pivots(mirror([100, 120, 108], direction), direction), direction)
            self.assertTrue(result["valid"])
            self.assertTrue(result["entry_eligible"])
            self.assertEqual(result["label"], "ONDA 3")
            self.assertEqual(result["direction"], direction)

    def test_partial_wave_three_contract_and_directions(self):
        for direction in ("ALTA", "BAIXA"):
            result = context(pivots(mirror([100, 120, 110, 140], direction), direction), direction)
            self.assertTrue(result["valid"])
            self.assertTrue(result["entry_eligible"])
            self.assertEqual(result["label"], "POSSIVEL ONDA 3")
            self.assertEqual(result["direction"], direction)
            self.assertFalse(engine._partial_wave_three(mirror([100, 120, 125, 140], direction), direction))
        self.assertFalse(engine._partial_wave_three([100, 120, 110, 140], "NEUTRO"))

    def test_complete_impulse_is_context_only(self):
        for direction in ("ALTA", "BAIXA"):
            result = context(pivots(mirror([100, 120, 110, 150, 135, 160], direction), direction), direction)
            self.assertTrue(result["valid"])
            self.assertFalse(result["entry_eligible"])
            self.assertEqual(result["phase"], "IMPULSO_COMPLETO")

    def test_abc_entry_has_direction(self):
        for direction in ("ALTA", "BAIXA"):
            start = "HIGH" if direction == "ALTA" else "LOW"
            points = pivots(mirror([140, 120, 132, 108], direction), direction, start)
            result = context(points, direction)
            self.assertTrue(result["valid"])
            self.assertTrue(result["entry_eligible"])
            self.assertEqual(result["direction"], direction)
            self.assertEqual(result["label"], "ABC_ZIGZAG")

    def test_abc_does_not_reuse_old_quad_or_accept_wrong_directions(self):
        points = pivots([140, 120, 132, 108, 145], start="HIGH")
        self.assertFalse(engine.detect_abc_correction(points, "ALTA")["entry_eligible"])
        wrong = pivots([120, 140, 128, 152], start="HIGH")
        self.assertFalse(engine.detect_abc_correction(wrong, "ALTA")["entry_eligible"])

    def test_unknown_insufficient_and_fallback_are_not_entries(self):
        for direction, points in [("NEUTRO", pivots([100, 120, 110, 140])),
                                  ("ALTA", []),
                                  ("ALTA", pivots([100, 120, 90, 110]))]:
            result = context(points, direction)
            self.assertFalse(result["valid"])
            self.assertFalse(result["entry_eligible"])
        for direction in (None, "ALTA", "BAIXA"):
            self.assertFalse(engine.analyze_fibonacci_wave_setup([], direction)["entry_eligible"])


class PivotCausalityTests(unittest.TestCase):
    def test_confirmation_requires_closed_right_hand_candles(self):
        candles = [{"high": h, "low": 0, "open": 1, "close": 1, "time": i}
                   for i, h in enumerate([2, 3, 10, 3, 2, 1])]
        self.assertEqual(engine.detect_pivots(candles[:5]), [])
        result = engine.detect_pivots(candles)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["index"], 2)
        self.assertEqual(result[0]["confirmed_index"], 4)
        self.assertEqual(result[0]["confirmed_at"], 4)

    def test_events_wait_for_confirmation_and_ignore_legacy_unknown_time(self):
        candles = [{"open": 9, "close": 11, "high": 12, "low": 8} for _ in range(7)]
        pivot = {"index": 1, "confirmed_index": 4, "type": "HIGH", "price": 10}
        events = engine.detect_structure_events(candles, [pivot])
        self.assertEqual([event["index"] for event in events], [4])
        legacy = {k: v for k, v in pivot.items() if k != "confirmed_index"}
        self.assertEqual(engine.detect_structure_events(candles, [legacy]), [])

    def test_later_compression_preserves_earlier_break(self):
        candles = [{"high": h, "low": 0, "open": 1, "close": c, "time": i}
                   for i, (h, c) in enumerate([(2, 1), (3, 1), (10, 2), (3, 1),
                                              (2, 1), (12, 11), (15, 2), (3, 1),
                                              (2, 1), (2, 1)])]
        early = engine.detect_structure_events(candles[:7], engine.detect_pivots(candles[:7]))
        final_pivots = engine.detect_pivots(candles)
        self.assertEqual(final_pivots[0]["index"], 6)
        self.assertEqual(final_pivots[0]["superseded"][0]["index"], 2)
        final = engine.detect_structure_events(candles, final_pivots)
        self.assertEqual(early, [event for event in final if event["index"] < 6])
        self.assertEqual(early[0]["index"], 5)

    def test_every_prefix_matches_full_history_events(self):
        rng = random.Random(91)
        price = 100
        candles = []
        for i in range(120):
            close = price + rng.uniform(-7, 7)
            candles.append({"open": price, "close": close,
                            "high": max(price, close) + rng.uniform(0.1, 3),
                            "low": min(price, close) - rng.uniform(0.1, 3), "time": i})
            price = close
        for window in (1, 2, 3):
            final = engine.detect_structure_events(candles, engine.detect_pivots(candles, window))
            for length in range(8, len(candles)):
                prefix = candles[:length]
                actual = engine.detect_structure_events(prefix, engine.detect_pivots(prefix, window))
                self.assertEqual(actual, [e for e in final if e["index"] < length - 1],
                                 (window, length))


if __name__ == "__main__":
    unittest.main()
