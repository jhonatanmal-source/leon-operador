"""Testes para C8: Ajustar Fibonacci para maior tolerância
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.institutional_analysis_engine import analyze_fibonacci_wave_setup


def pivot(index, _type, price):
    return {"index": index, "type": _type, "price": price}


class C8FibonacciToleranceTests(unittest.TestCase):
    """C8: Fibonacci com ranges expandidos e fallback partial."""

    def test_onda3_accepts_retracement_050(self):
        """Onda 3: retracement 0.5 é aceito (antes 0.618 mínimo)."""
        pivots_list = [
            pivot(0, "LOW", 100),
            pivot(1, "HIGH", 110),
            pivot(2, "LOW", 105),  # retracement = 5/10 = 0.5
        ]
        result = analyze_fibonacci_wave_setup(pivots_list, "ALTA")
        self.assertTrue(result["valid"])
        self.assertEqual(result["target_wave"], "ONDA 3")

    def test_onda3_accepts_retracement_0886(self):
        """Onda 3: retracement 0.886 é aceito (antes 0.786 máximo)."""
        pivots_list = [
            pivot(0, "LOW", 100),
            pivot(1, "HIGH", 110),
            pivot(2, "LOW", 101.14),  # retracement = 8.86/10 = 0.886
        ]
        result = analyze_fibonacci_wave_setup(pivots_list, "ALTA")
        self.assertTrue(result["valid"])
        self.assertEqual(result["target_wave"], "ONDA 3")

    def test_onda3_rejects_retracement_040(self):
        """Onda 3: retracement 0.4 rejeitado (abaixo de 0.5)."""
        pivots_list = [
            pivot(0, "LOW", 100),
            pivot(1, "HIGH", 110),
            pivot(2, "LOW", 106),  # retracement = 4/10 = 0.4
        ]
        result = analyze_fibonacci_wave_setup(pivots_list, "ALTA")
        self.assertFalse(result["valid"])

    def test_onda5_accepts_retracement_0236(self):
        """Onda 5: retracement 0.236 é aceito (antes 0.382 mínimo)."""
        pivots_list = [
            pivot(0, "LOW", 100),
            pivot(1, "HIGH", 110),
            pivot(2, "LOW", 105),
            pivot(3, "HIGH", 120),
            pivot(4, "LOW", 116.46),  # retracement = 3.54/15 = 0.236
        ]
        result = analyze_fibonacci_wave_setup(pivots_list, "ALTA")
        self.assertTrue(result["valid"])
        self.assertEqual(result["target_wave"], "ONDA 5")

    def test_onda5_rejects_retracement_060(self):
        """Onda 5: retracement 0.6 rejeitado (acima de 0.5)."""
        pivots_list = [
            pivot(0, "LOW", 100),
            pivot(1, "HIGH", 110),
            pivot(2, "LOW", 105),
            pivot(3, "HIGH", 120),
            pivot(4, "LOW", 111),   # retracement = 9/15 = 0.6 > 0.5
        ]
        result = analyze_fibonacci_wave_setup(pivots_list, "ALTA")
        # Pode cair como Onda 3 se os 3 primeiros pivots formarem onda 3
        # Verifica que NÃO é Onda 5
        self.assertNotEqual(result.get("target_wave"), "ONDA 5")

    def test_partial_fallback_when_no_structure(self):
        """Sem estrutura de ondas: partial=True."""
        pivots_list = [
            pivot(0, "LOW", 100),
            pivot(1, "HIGH", 110),
            # Apenas 2 pivots, não forma Onda 3 nem Onda 5
        ]
        result = analyze_fibonacci_wave_setup(pivots_list, "ALTA")
        self.assertFalse(result["valid"])
        self.assertTrue(result.get("partial"),
                        "Sem estrutura, partial deve ser True")

    def test_expanded_ranges_present_in_all_results(self):
        """expanded_ranges presente sempre, mesmo em resultados inválidos."""
        pivots_list = [
            pivot(0, "LOW", 100),
            pivot(1, "HIGH", 110),
        ]
        result = analyze_fibonacci_wave_setup(pivots_list, "ALTA")
        self.assertIn("expanded_ranges", result)
        self.assertTrue(result["expanded_ranges"])

    def test_partial_false_when_valid(self):
        """Quando Onda 3 válida: partial=False."""
        pivots_list = [
            pivot(0, "LOW", 100),
            pivot(1, "HIGH", 110),
            pivot(2, "LOW", 105),
        ]
        result = analyze_fibonacci_wave_setup(pivots_list, "ALTA")
        self.assertTrue(result["valid"])
        self.assertFalse(result.get("partial"),
                        "Onda 3 válida deve ter partial=False")


if __name__ == "__main__":
    unittest.main()
