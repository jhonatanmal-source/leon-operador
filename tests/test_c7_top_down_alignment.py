"""Testes para C7: Ajustar TOP_DOWN alignment threshold
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.top_down_agent import _bias
from src.timeframe_policy import evaluate_timeframe_policy


def candle(open_, high, low, close):
    return {"data": "", "ativo": "XAUUSD", "open": open_, "high": high, "low": low, "close": close}


class C7TopDownThresholdTests(unittest.TestCase):
    """C7: Threshold aumentado para 0.5% reduz ruído."""

    def test_small_noise_within_05pct_returns_lateral(self):
        """Ruído < 0.5% sem HH/LL claros: LATERAL."""
        # Preço oscila lateralmente sem tendência
        candles = []
        base = 100.0
        for i in range(25):
            # Oscila +/- 0.2 em torno de 100 (0.2% de 100)
            offset = (i % 4) * 0.15 - 0.3  # -0.3, -0.15, 0, 0.15
            candles.append(candle(
                base + offset,
                base + offset + 0.3,
                base + offset - 0.3,
                base + offset,
            ))
        result = _bias(candles)
        self.assertEqual(result, "LATERAL",
                         "Ruído < 0.5% deve ser LATERAL com threshold 0.5%")

    def test_strong_trend_above_05pct_still_detected(self):
        """Tendência forte > 0.5%: ainda detecta ALTA corretamente."""
        candles = [candle(100 + i * 0.5, 101 + i * 0.5, 99 + i * 0.5, 100.5 + i * 0.5)
                   for i in range(25)]
        result = _bias(candles)
        self.assertEqual(result, "ALTA",
                         "Tendência > 0.5% deve ser ALTA")


class C7TimeframeAlignmentTests(unittest.TestCase):
    """C7: 2 de 3 timeframes alinhados é suficiente."""

    def test_approves_2_of_3_aligned(self):
        """2 de 3 (H4+H1) alinhados, M15 diverge: aprovado."""
        result = evaluate_timeframe_policy(
            {
                "macro_semanal": "ALTA",
                "h4_bias": "ALTA",
                "h1_contexto": "ALTA",
                "m15_gatilho": "BAIXA",
            },
            "COMPRA",
        )
        self.assertTrue(result["approved"],
                        "2/3 timeframes alinhados deve aprovar (C7)")

    def test_blocks_1_of_3_aligned(self):
        """Apenas 1 TF alinhado: bloqueado."""
        result = evaluate_timeframe_policy(
            {
                "macro_semanal": "ALTA",
                "h4_bias": "ALTA",
                "h1_contexto": "BAIXA",
                "m15_gatilho": "BAIXA",
            },
            "COMPRA",
        )
        self.assertFalse(result["approved"],
                         "1/3 timeframes alinhados deve bloquear")

    def test_approves_3_of_3_aligned_as_tendencia(self):
        """3 de 3 alinhados + macro: TENDENCIA."""
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

    def test_approves_2_of_3_with_correction_mode(self):
        """2/3 alinhados contra macro: aprovado como CORRECAO."""
        result = evaluate_timeframe_policy(
            {
                "macro_semanal": "ALTA",
                "h4_bias": "BAIXA",
                "h1_contexto": "BAIXA",
                "m15_gatilho": "ALTA",  # diverge -> só 2/3
            },
            "VENDA",
        )
        self.assertTrue(result["approved"],
                        "2/3 contra macro = CORRECAO")


if __name__ == "__main__":
    unittest.main()
