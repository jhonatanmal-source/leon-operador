import unittest

from elliott_study_engine import (
    score_elliott_smc_confluence,
    validate_impulse_points,
)
from study_engine import get_study_by_topic


class MaterialElliottTests(unittest.TestCase):

    def test_new_topics_are_loaded(self):
        topics = [
            "Regras Duras do Impulso Elliott",
            "Graus e Contagens Alternativas Elliott",
            "Familias Corretivas Elliott",
            "Alternancia Extensao e Truncamento",
            "Fibonacci Probabilistico em Elliott",
            "Integracao Elliott SMC no XAUUSD",
        ]

        for topic in topics:
            self.assertIsNotNone(get_study_by_topic(topic))

    def test_valid_bullish_impulse(self):
        result = validate_impulse_points(
            [100, 110, 104, 124, 114, 132],
            "ALTA",
        )

        self.assertTrue(result["valid"])

    def test_wave_two_breaking_origin_invalidates_count(self):
        result = validate_impulse_points(
            [100, 110, 99, 124, 114, 132],
            "ALTA",
        )

        self.assertFalse(result["valid"])
        self.assertIn("wave_2_preserves_origin", result["failed"])

    def test_elliott_without_smc_never_approves_entry(self):
        result = score_elliott_smc_confluence({
            "wave_rules_valid": True,
            "invalidation_defined": True,
            "alternative_count": True,
            "smc_confirmed": False,
            "m15_confirmed": False,
        })

        self.assertFalse(result["approved"])
        self.assertEqual(result["policy"], "ELLIOTT_CONTEXT_ONLY")

    def test_complete_confluence_can_be_approved(self):
        result = score_elliott_smc_confluence({
            "wave_rules_valid": True,
            "invalidation_defined": True,
            "alternative_count": True,
            "smc_confirmed": True,
            "m15_confirmed": True,
        })

        self.assertTrue(result["approved"])


if __name__ == "__main__":
    unittest.main()
