import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch


ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR / "src"))

import operator_council
import pre_operation_engine


class PreOperationPipelineConsistencyTests(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.data_dir = Path(self.tmpdir.name)
        self.store = MagicMock()
        self.patches = [
            patch.dict(
                os.environ,
                {"LEON_CYCLE_ID": "CYCLE-1", "LEON_ANALYSIS_ID": "ANALYSIS-1"},
            ),
            patch.object(pre_operation_engine, "DATA_DIR", self.data_dir),
            patch.object(
                pre_operation_engine,
                "PRE_OPERATION_FILE",
                self.data_dir / "pre_operation_trades.csv",
            ),
            patch.object(pre_operation_engine, "register_decision"),
            patch.object(pre_operation_engine, "registrar_log"),
            patch.object(
                pre_operation_engine,
                "InterestZoneStore",
                return_value=self.store,
            ),
            patch.object(pre_operation_engine, "_laboratorio_demo_ativo", return_value=True),
        ]
        for item in self.patches:
            item.start()

    def tearDown(self):
        for item in reversed(self.patches):
            item.stop()
        self.tmpdir.cleanup()

    @staticmethod
    def _region(cycle_id="CYCLE-1"):
        return {
            "region_id": "REG-CONSISTENCY",
            "cycle_id": cycle_id,
            "analysis_id": "ANALYSIS-1",
            "symbol": "XAUUSD",
            "source_candle_timestamp": "2026-07-14T07:00:00",
            "region_type": "BEARISH_ORDER_BLOCK",
            "region_low": 3998.0,
            "region_high": 4003.0,
            "region_direction": "BEARISH",
            "region_status": "CONFIRMADA",
            "region_valid": True,
            "region_invalidated": False,
            "liquidity_swept": True,
            "bos_present": True,
            "choch_present": True,
            "next_required_event": "VALIDAR_PRE_TRADE_E_RISCO",
        }

    def _register(self, **overrides):
        payload = {
            "ativo": "XAUUSD",
            "direcao": "VENDA",
            "status_setup": "SETUP VALIDO",
            "operacao": (4001.97, 4003.7125, 3999.879, 3998.485, 2.0),
            "smc": "BEARISH",
            "elliott": "CORRECAO",
            "bos": "BOS_BEARISH",
            "choch": "CHOCH_BEARISH",
            "confianca": "MEDIA",
            "brain_score": 50,
            "region_context": self._region(),
        }
        payload.update(overrides)
        return pre_operation_engine.registrar_pre_operacao(**payload)

    def test_canonical_wait_never_reuses_candidate_direction_or_builds_plan(self):
        record = self._register(
            direcao="AGUARDAR",
            operacao=None,
            region_context=None,
        )

        self.assertEqual(record["direcao"], "AGUARDAR")
        self.assertEqual(record["decision"], "AGUARDAR")
        self.assertEqual(record["status"], "OBSERVADO")
        for field in ("entrada", "stop", "tp1", "tp2", "rr"):
            self.assertEqual(record[field], "")

    def test_region_association_failure_invalidates_and_clears_trade_plan(self):
        self.store.associate_pre_operation.side_effect = ValueError(
            "Zona ja associada a outra PRE_OPERATION"
        )

        record = self._register()

        self.assertEqual(record["resultado"], "REGION_ASSOCIATION_FAILED")
        self.assertEqual(record["operational_state"], "INVALIDADO")
        self.assertEqual(record["decision"], "NAO_OPERAR")
        self.assertEqual(record["status"], "OBSERVADO")
        for field in ("entrada", "stop", "tp1", "tp2", "rr"):
            self.assertEqual(record[field], "")

    def test_cycle_id_mismatch_discards_plan(self):
        with patch.dict(
            os.environ,
            {"LEON_CYCLE_ID": "CYCLE-NEW", "LEON_ANALYSIS_ID": "ANALYSIS-NEW"},
        ):
            record = self._register(region_context=self._region("CYCLE-OLD"))

        self.assertEqual(record["resultado"], "CYCLE_ID_MISMATCH")
        self.assertFalse(record["executable"])
        for field in ("entrada", "stop", "tp1", "tp2", "rr"):
            self.assertEqual(record[field], "")

    def test_two_contextual_confirmations_inside_confirmed_region_can_advance(self):
        region = self._region()
        region["choch_present"] = False

        record = self._register(region_context=region)

        self.assertEqual(record["status"], "ABERTO")
        self.assertEqual(record["operational_state"], "PRE_TRADE_VALID")
        self.assertTrue(record["executable"])
        self.assertGreaterEqual(int(record["confirmation_count"]), 2)

    def test_invalidated_pre_operation_is_not_labeled_system_error(self):
        classification = operator_council._classificar_estado_operacional(
            {
                "status": "OBSERVADO",
                "resultado": "REGION_ASSOCIATION_FAILED",
                "operational_state": "INVALIDADO",
                "direcao": "VENDA",
                "bos": "BOS_BEARISH",
            },
            {},
            {},
            {"direcao": "VENDA"},
        )

        self.assertEqual(classification["operational_state"], "INVALIDADO")
        self.assertEqual(
            classification["telegram_title"],
            "LEON | PRE-OPERACAO INVALIDADA",
        )
        self.assertNotIn("ERRO DO SISTEMA", classification["telegram_title"])

    def test_normal_wait_is_labeled_as_waiting_for_region(self):
        classification = operator_council._classificar_estado_operacional(
            {
                "status": "OBSERVADO",
                "resultado": "NO_DIRECTIONAL_SETUP",
                "operational_state": "CONTEXTO_INDEFINIDO",
                "direcao": "AGUARDAR",
            },
            {},
            {},
            {"direcao": "AGUARDAR"},
        )

        self.assertEqual(classification["operational_state"], "FORA_DE_REGIAO")
        self.assertEqual(
            classification["telegram_title"],
            "LEON | AGUARDANDO REGIAO",
        )
        self.assertNotIn("ERRO", classification["telegram_title"])

    def test_direct_leon_entrypoint_creates_and_propagates_cycle_identity(self):
        source = (ROOT_DIR / "src" / "leon.py").read_text(encoding="utf-8")

        self.assertIn("os.environ.setdefault", source)
        self.assertIn("registrar_pre_operacao(", source)


if __name__ == "__main__":
    unittest.main()
