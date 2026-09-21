import sys
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch

from web_app.services import system_health_service


class ShadowTradePlausibilityTests(unittest.TestCase):
    """Filtro M1: registros corrompidos (entry fora da faixa da mediana) são
    excluídos da exibição sem alterar o CSV bruto."""

    CSV_HEADER = (
        "id;opened_at;closed_at;symbol;direction;entry;stop;target;status;result;"
        "missing_confirmations\n"
    )

    def _write_csv(self, logs, lines):
        (logs / "shadow_trades.csv").write_text(
            self.CSV_HEADER + "".join(lines), encoding="utf-8"
        )

    def test_corrupt_record_hidden_from_list(self):
        with tempfile.TemporaryDirectory() as directory:
            logs = Path(directory)
            self._write_csv(
                logs,
                [
                    "SHADOW-000040;2026-07-30T10:00;2026-07-30T11:00;Gold_Spot;BUY;"
                    "4054.56;4040.00;4090.00;FECHADO;WIN_TP1;SMC OK\n",
                    "SHADOW-000041;2026-07-30T10:30;2026-07-30T11:30;Gold_Spot;BUY;"
                    "2301.80;2299.50;2306.40;FECHADO;WIN_TP1;SMC OK\n",
                    "SHADOW-000042;2026-07-30T12:00;2026-07-30T13:00;Gold_Spot;BUY;"
                    "4110.65;4095.00;4140.00;FECHADO;WIN_TP1;SMC OK\n",
                ],
            )
            with patch.object(system_health_service, "DATA_DIR", logs):
                trades = system_health_service._shadow_trades_list()
                summary = system_health_service._shadow_summary()

            ids = [t["id"] for t in trades]
            self.assertIn("SHADOW-000040", ids)
            self.assertNotIn("SHADOW-000041", ids)
            self.assertIn("SHADOW-000042", ids)
            self.assertEqual(len(trades), 2)
            # Resumo coerente com a tabela (R1)
            self.assertEqual(summary["total"], 2)
            self.assertEqual(summary["wins"], 2)

            # CSV bruto intocado
            raw = (logs / "shadow_trades.csv").read_text(encoding="utf-8")
            self.assertIn("2301.80", raw)

    def test_missing_or_empty_csv(self):
        with tempfile.TemporaryDirectory() as directory:
            logs = Path(directory)
            with patch.object(system_health_service, "DATA_DIR", logs):
                self.assertEqual(
                    system_health_service._shadow_trades_list(), []
                )
                self.assertEqual(
                    system_health_service._shadow_summary(),
                    {"total": 0, "open": 0, "wins": 0, "losses": 0},
                )

    def test_invalid_entries_are_excluded(self):
        with tempfile.TemporaryDirectory() as directory:
            logs = Path(directory)
            self._write_csv(
                logs,
                [
                    "SHADOW-000001;;;Gold_Spot;BUY;4090.00;;;ABERTO;;\n",
                    "SHADOW-000002;;;Gold_Spot;BUY;nao_e_numero;;;ABERTO;;\n",
                ],
            )
            with patch.object(system_health_service, "DATA_DIR", logs):
                trades = system_health_service._shadow_trades_list()
                summary = system_health_service._shadow_summary()

        self.assertEqual(len(trades), 1)
        self.assertEqual(trades[0]["id"], "SHADOW-000001")
        self.assertEqual(summary["total"], 1)


class LabModeActiveTests(unittest.TestCase):
    def test_recent_state_means_active(self):
        with tempfile.TemporaryDirectory() as directory:
            logs = Path(directory)
            recent = datetime.now() - timedelta(minutes=5)
            (logs / "study_state.txt").write_text(
                recent.isoformat(), encoding="utf-8"
            )
            with patch.object(system_health_service, "DATA_DIR", logs):
                self.assertTrue(system_health_service._lab_mode_active())

    def test_old_state_means_waiting(self):
        with tempfile.TemporaryDirectory() as directory:
            logs = Path(directory)
            old = datetime.now() - timedelta(days=2)
            (logs / "study_state.txt").write_text(old.isoformat(), encoding="utf-8")
            with patch.object(system_health_service, "DATA_DIR", logs):
                self.assertFalse(system_health_service._lab_mode_active())


if __name__ == "__main__":
    unittest.main()
