import sys
import unittest
from pathlib import Path


from src.timeframe_policy import evaluate_timeframe_policy


class TimeframePolicyTests(unittest.TestCase):

    def test_approves_primary_trend(self):
        result = evaluate_timeframe_policy(
            {
                "macro_semanal": "ALTA",
                "h4_bias": "ALTA",
                "h1_contexto": "ALTA",
                "m15_gatilho": "ALTA",
            },
            "COMPRA",
        )

        self.assertTrue(result["approved"])
        self.assertEqual(result["mode"], "TENDENCIA")
        self.assertEqual(result["risk_factor"], 1.0)

    def test_approves_confirmed_correction_with_half_risk(self):
        result = evaluate_timeframe_policy(
            {
                "macro_semanal": "ALTA",
                "h4_bias": "BAIXA",
                "h1_contexto": "BAIXA",
                "m15_gatilho": "BAIXA",
            },
            "VENDA",
        )

        self.assertTrue(result["approved"])
        self.assertEqual(result["mode"], "CORRECAO")
        self.assertEqual(result["risk_factor"], 0.5)

    def test_blocks_partial_correction(self):
        result = evaluate_timeframe_policy(
            {
                "macro_semanal": "ALTA",
                "h4_bias": "BAIXA",
                "h1_contexto": "BAIXA",
                "m15_gatilho": "ALTA",
            },
            "VENDA",
        )

        self.assertFalse(result["approved"])


if __name__ == "__main__":
    unittest.main()
