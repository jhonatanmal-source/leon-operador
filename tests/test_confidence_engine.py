import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.confidence_engine import (
    calcular_confianca,
    _net_adjustments,
)


class ConfidenceEngineTests(unittest.TestCase):
    """Testes para confidence engine e feedback loop."""

    def test_calcular_confianca_muito_alta(self):
        self.assertEqual(calcular_confianca(95), "MUITO ALTA")
        self.assertEqual(calcular_confianca(90), "MUITO ALTA")

    def test_calcular_confianca_alta(self):
        self.assertEqual(calcular_confianca(80), "ALTA")
        self.assertEqual(calcular_confianca(70), "ALTA")

    def test_calcular_confianca_media(self):
        self.assertEqual(calcular_confianca(60), "MÉDIA")
        self.assertEqual(calcular_confianca(50), "MÉDIA")

    def test_calcular_confianca_baixa(self):
        self.assertEqual(calcular_confianca(40), "BAIXA")
        self.assertEqual(calcular_confianca(0), "BAIXA")

    def test_calcular_confianca_invariante(self):
        """calcular_confianca original permanece inalterado."""
        self.assertEqual(calcular_confianca(75), "ALTA")
        self.assertEqual(calcular_confianca(49), "BAIXA")
        self.assertEqual(calcular_confianca(89), "ALTA")


class ConfidenceFeedbackLoopTests(unittest.TestCase):
    """Testes para calcular_confianca_ajustada com recomendações."""

    def setUp(self):
        self.recs_patch = Path(tempfile.mktemp(suffix=".json"))

    def _create_recs(self, recs):
        self.recs_patch.write_text(json.dumps(recs, indent=2))

    # Monkey-patch the RECOMMENDATIONS_FILE path
    @classmethod
    def setUpClass(cls):
        import src.confidence_engine as ce
        cls._original_path = ce.RECOMMENDATIONS_FILE

    @classmethod
    def tearDownClass(cls):
        import src.confidence_engine as ce
        ce.RECOMMENDATIONS_FILE = cls._original_path

    def setUp(self):
        import src.confidence_engine as ce
        self.temp_recs = Path(tempfile.mktemp(suffix="_recs.json"))
        ce.RECOMMENDATIONS_FILE = self.temp_recs

    def tearDown(self):
        if self.temp_recs.exists():
            self.temp_recs.unlink(missing_ok=True)

    def test_sem_arquivo_retorna_score_original(self):
        from src.confidence_engine import calcular_confianca_ajustada
        # Arquivo não existe (temp_recs não foi criado)
        score, label = calcular_confianca_ajustada(75)
        self.assertEqual(score, 75)
        self.assertEqual(label, "ALTA")

    def test_sem_recomendacoes_aplicadas_retorna_original(self):
        from src.confidence_engine import calcular_confianca_ajustada
        self.temp_recs.write_text(json.dumps([
            {
                "dimension": "smc",
                "value": "NEUTRO",
                "applied_automatically": False,
                "suggested_adjustment": -5,
            }
        ]))
        score, label = calcular_confianca_ajustada(75, smc="NEUTRO")
        self.assertEqual(score, 75)
        self.assertEqual(label, "ALTA")

    def test_uma_recomendacao_aplicada_ajusta_score(self):
        from src.confidence_engine import calcular_confianca_ajustada
        self.temp_recs.write_text(json.dumps([
            {
                "dimension": "smc",
                "value": "NEUTRO",
                "applied_automatically": True,
                "suggested_adjustment": -5,
            }
        ]))
        score, label = calcular_confianca_ajustada(75, smc="NEUTRO")
        self.assertEqual(score, 70)
        self.assertEqual(label, "ALTA")

    def test_multiplas_recomendacoes_acumulam(self):
        from src.confidence_engine import calcular_confianca_ajustada
        self.temp_recs.write_text(json.dumps([
            {
                "dimension": "smc",
                "value": "NEUTRO",
                "applied_automatically": True,
                "suggested_adjustment": -5,
            },
            {
                "dimension": "elliott",
                "value": "ONDA 5 CONCLUIDA",
                "applied_automatically": True,
                "suggested_adjustment": -5,
            },
        ]))
        score, label = calcular_confianca_ajustada(75, smc="NEUTRO", elliott="ONDA 5 CONCLUIDA")
        self.assertEqual(score, 65)
        self.assertEqual(label, "MÉDIA")

    def test_ajuste_nao_ultrapassa_limites_0_100(self):
        from src.confidence_engine import calcular_confianca_ajustada
        self.temp_recs.write_text(json.dumps([
            {
                "dimension": "smc",
                "value": "NEUTRO",
                "applied_automatically": True,
                "suggested_adjustment": -200,
            }
        ]))
        score, label = calcular_confianca_ajustada(10, smc="NEUTRO")
        self.assertEqual(score, 0)
        self.assertEqual(label, "BAIXA")

    def test_contexto_irrelevante_ignorado(self):
        from src.confidence_engine import calcular_confianca_ajustada
        self.temp_recs.write_text(json.dumps([
            {
                "dimension": "direcao",
                "value": "COMPRA",
                "applied_automatically": True,
                "suggested_adjustment": -10,
            }
        ]))
        # Passando smc=... mas a recomendação é para direcao=COMPRA
        score, label = calcular_confianca_ajustada(75, smc="NEUTRO")
        self.assertEqual(score, 75)
        self.assertEqual(label, "ALTA")

    def test_net_adjustments_agrega_corretamente(self):
        self.temp_recs.write_text(json.dumps([
            {
                "dimension": "smc",
                "value": "NEUTRO",
                "applied_automatically": True,
                "suggested_adjustment": -5,
            },
            {
                "dimension": "smc",
                "value": "NEUTRO",
                "applied_automatically": True,
                "suggested_adjustment": -5,
            },
            {
                "dimension": "direcao",
                "value": "COMPRA",
                "applied_automatically": True,
                "suggested_adjustment": -10,
            },
        ]))
        from src.confidence_engine import RECOMMENDATIONS_FILE
        # Manually reload by calling _net_adjustments
        adj = _net_adjustments()
        self.assertEqual(adj.get("smc=NEUTRO"), -10)  # -5 + -5
        self.assertEqual(adj.get("direcao=COMPRA"), -10)


if __name__ == "__main__":
    unittest.main()
