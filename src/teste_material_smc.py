import unittest

from operational_study_engine import validate_setup_a_plus
from study_engine import get_study_by_topic


class MaterialSmcTests(unittest.TestCase):

    def test_new_studies_are_available(self):
        topics = [
            "Estrutura SMC Hierarquica",
            "Mapa de Liquidez e Inducement",
            "Qualificacao de POI",
            "Entrada SMC por Confirmacao M15",
        ]

        for topic in topics:
            self.assertIsNotNone(get_study_by_topic(topic))

    def test_loss_pattern_is_not_a_plus(self):
        result = validate_setup_a_plus({
            "direction": "VENDA",
            "trend": "BAIXA",
            "momentum": "BAIXA",
            "liquidity_event": "SEM_CONFIRMACAO",
            "bos": "SEM_BOS",
            "choch": "SEM_CHOCH",
            "fvg": "FVG_BEARISH",
            "poi_score": 45,
            "top_down": "MISTO",
            "session": "ASIA",
            "rr": 3,
            "high_impact_news": False,
            "market_state": "TENDENCIA",
        })

        self.assertFalse(result["approved"])

    def test_complete_m15_confirmation_is_a_plus(self):
        result = validate_setup_a_plus({
            "direction": "VENDA",
            "trend": "BAIXA",
            "momentum": "BAIXA",
            "liquidity_event": "SWEEP_CONFIRMADO",
            "bos": "BOS_BEARISH",
            "choch": "CHOCH_BEARISH",
            "fvg": "FVG_BEARISH",
            "poi_score": 85,
            "top_down": "ALINHADO",
            "session": "LONDRES",
            "rr": 3,
            "high_impact_news": False,
            "market_state": "TENDENCIA",
        })

        self.assertTrue(result["approved"])


if __name__ == "__main__":
    unittest.main()
