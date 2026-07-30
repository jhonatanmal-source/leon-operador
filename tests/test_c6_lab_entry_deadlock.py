"""Testes para C6: Ajustar lab_entry_policy para evitar deadlock
"""
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import src.lab_entry_policy as lab_entry_policy


def shadow(result, missing="FIBONACCI_ONDA_2_OU_4,CAPTURA_LIQUIDEZ"):
    return {
        "status": "FECHADO",
        "result": result,
        "missing_confirmations": missing,
    }


class C6LabEntryDeadlockTests(unittest.TestCase):
    """C6: Evitar deadlock com thresholds mais realistas."""

    def test_progressive_min_closed_below_30(self):
        """Winrate < 30%: min_closed = 15 (antes era 30)."""
        self.assertEqual(lab_entry_policy._progressive_min_closed(20), 15)

    def test_progressive_min_closed_30_to_49(self):
        """Winrate 30-49%: min_closed = 20 (antes era 30)."""
        self.assertEqual(lab_entry_policy._progressive_min_closed(35), 20)

    def test_progressive_min_closed_50_to_69(self):
        """Winrate 50-69%: min_closed = 10 (antes era 20)."""
        self.assertEqual(lab_entry_policy._progressive_min_closed(55), 10)

    def test_progressive_min_closed_70_plus(self):
        """Winrate >= 70%: min_closed = 5."""
        self.assertEqual(lab_entry_policy._progressive_min_closed(85), 5)

    def test_config_min_winrate_default_updated(self):
        """Verifica que o default da config é 30 (via patch do CONFIG_FILE)."""
        directory = tempfile.TemporaryDirectory()
        config_file = Path(directory.name) / "config.ini"
        # Config sem lab_shadow_min_winrate (usa default)
        config_file.write_text(
            "\n".join([
                "[EXECUTION]",
                "demo_only=true",
                "learning_lab_enabled=true",
                "lab_shadow_evidence_enabled=true",
            ]),
            encoding="utf-8",
        )
        self.addCleanup(directory.cleanup)

        with patch.object(lab_entry_policy, "CONFIG_FILE", config_file):
            config = lab_entry_policy._config()
            self.assertEqual(config["min_winrate"], 30,
                             "Default min_winrate deve ser 30")

    def test_lab_approves_with_winrate_35_and_20_shadows(self):
        """Lab aprova com winrate=35% e 20 shadows (min_closed=20 para 30-49%)."""
        directory = tempfile.TemporaryDirectory()
        config_file = Path(directory.name) / "config.ini"
        config_file.write_text(
            "\n".join([
                "[EXECUTION]",
                "demo_only=true",
                "learning_lab_enabled=true",
                "lab_shadow_evidence_enabled=true",
                "lab_shadow_min_winrate=30",
            ]),
            encoding="utf-8",
        )
        self.addCleanup(directory.cleanup)

        # 7 wins + 13 losses = 20 closed, winrate 35% => >= 30% ok
        # progressive_min_closed(35) = 20, closed=20 >= 20 ok
        rows = [shadow("WIN_2R") for _ in range(7)] + [shadow("LOSS") for _ in range(13)]

        with patch.object(lab_entry_policy, "CONFIG_FILE", config_file):
            result = lab_entry_policy.evaluate_lab_entry(
                smc_confirmed=True,
                top_down_confirmed=True,
                strict_confirmation=False,
                missing_confirmations=["FIBONACCI_ONDA_2_OU_4"],
                rows=rows,
            )

        self.assertTrue(result["approved"],
                        "Lab deve aprovar com winrate 35% e 20 shadows")


if __name__ == "__main__":
    unittest.main()
