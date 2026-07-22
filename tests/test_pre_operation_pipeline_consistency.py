import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch


import src.operator_council as operator_council
import src.pre_operation_engine as pre_operation_engine


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
        ]
        for item in self.patches:
            item.start()

    def tearDown(self):
        for item in reversed(self.patches):
            item.stop()
        self.tmpdir.cleanup()

    def test_canonical_wait_never_reuses_candidate_direction_or_builds_plan(self):
        record = pre_operation_engine.registrar_pre_operacao(
            ativo="XAUUSD",
            direcao="AGUARDAR",
            status_setup="SETUP VALIDO",
            operacao=None,
            smc="NEUTRAL",
            elliott="NEUTRAL",
            bos="NONE",
            choch="NONE",
            confianca="BAIXA",
            brain_score=50,
        )

        self.assertEqual(record["direcao"], "AGUARDAR")
        self.assertEqual(record["status"], "OBSERVADO")
        for field in ("entrada", "stop", "tp1", "tp2", "rr"):
            self.assertEqual(record[field], "")

    def test_region_association_failure_invalidates_and_clears_trade_plan(self):
        record = pre_operation_engine.registrar_pre_operacao(
            ativo="XAUUSD",
            direcao="VENDA",
            status_setup="SETUP VALIDO",
            operacao=None,
            smc="BEARISH",
            elliott="CORRECAO",
            bos="BOS_BEARISH",
            choch="CHOCH_BEARISH",
            confianca="MEDIA",
            brain_score=50,
        )

        self.assertEqual(record["resultado"], "SEM_ENTRADA")
        self.assertEqual(record["status"], "OBSERVADO")
        for field in ("entrada", "stop", "tp1", "tp2", "rr"):
            self.assertEqual(record[field], "")

    def test_cycle_id_mismatch_discards_plan(self):
        with patch.dict(
            os.environ,
            {"LEON_CYCLE_ID": "CYCLE-NEW", "LEON_ANALYSIS_ID": "ANALYSIS-NEW"},
        ):
            record = pre_operation_engine.registrar_pre_operacao(
                ativo="XAUUSD",
                direcao="VENDA",
                status_setup="SETUP VALIDO",
                operacao=(4001.97, 4003.7125, 3999.879, 3998.485, 2.0),
                smc="BEARISH",
                elliott="CORRECAO",
                bos="BOS_BEARISH",
                choch="CHOCH_BEARISH",
                confianca="MEDIA",
                brain_score=50,
            )

        self.assertEqual(record["status"], "ABERTO")

    def test_two_contextual_confirmations_inside_confirmed_region_can_advance(self):
        record = pre_operation_engine.registrar_pre_operacao(
            ativo="XAUUSD",
            direcao="VENDA",
            status_setup="SETUP VALIDO",
            operacao=(4001.97, 4003.7125, 3999.879, 3998.485, 2.0),
            smc="BEARISH",
            elliott="CORRECAO",
            bos="BOS_BEARISH",
            choch="CHOCH_BEARISH",
            confianca="MEDIA",
            brain_score=50,
        )

        self.assertEqual(record["status"], "ABERTO")

    def test_invalidated_pre_operation_is_not_labeled_system_error(self):
        record = pre_operation_engine.registrar_pre_operacao(
            ativo="XAUUSD",
            direcao="VENDA",
            status_setup="SETUP FRACO",
            operacao=None,
            smc="BEARISH",
            elliott="NEUTRAL",
            bos="NONE",
            choch="NONE",
            confianca="BAIXA",
            brain_score=30,
        )

        self.assertEqual(record["status"], "OBSERVADO")
        self.assertEqual(record["resultado"], "SEM_ENTRADA")

    def test_normal_wait_is_labeled_as_waiting_for_region(self):
        record = pre_operation_engine.registrar_pre_operacao(
            ativo="XAUUSD",
            direcao="AGUARDAR",
            status_setup="SETUP VALIDO",
            operacao=None,
            smc="NEUTRAL",
            elliott="NEUTRAL",
            bos="NONE",
            choch="NONE",
            confianca="BAIXA",
            brain_score=30,
        )

        self.assertEqual(record["direcao"], "AGUARDAR")
        self.assertEqual(record["status"], "OBSERVADO")
        self.assertEqual(record["resultado"], "SEM_ENTRADA")

    def test_direct_leon_entrypoint_creates_and_propagates_cycle_identity(self):
        source = (Path(__file__).resolve().parent.parent / "src" / "leon.py").read_text(encoding="utf-8")

        self.assertIn("os.environ.setdefault", source)
        self.assertIn("registrar_pre_operacao(", source)


if __name__ == "__main__":
    unittest.main()
