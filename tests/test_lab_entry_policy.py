import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


import src.lab_entry_policy as lab_entry_policy


def shadow(result, missing="FIBONACCI_ONDA_2_OU_4,CAPTURA_LIQUIDEZ"):
    return {
        "status": "FECHADO",
        "result": result,
        "missing_confirmations": missing,
    }


class LabEntryPolicyTests(unittest.TestCase):

    def _config_file(self):
        directory = tempfile.TemporaryDirectory()
        config_file = Path(directory.name) / "config.ini"
        config_file.write_text(
            "\n".join(
                [
                    "[EXECUTION]",
                    "demo_only=true",
                    "learning_lab_enabled=true",
                    "lab_shadow_evidence_enabled=true",
                    "lab_shadow_min_closed=2",
                    "lab_shadow_min_winrate=70",
                ]
            ),
            encoding="utf-8",
        )
        return directory, config_file

    def test_approves_demo_lab_with_positive_shadow_evidence(self):
        directory, config_file = self._config_file()
        self.addCleanup(directory.cleanup)
        rows = [shadow("WIN_2R"), shadow("WIN_2R")]

        with patch.object(lab_entry_policy, "CONFIG_FILE", config_file):
            result = lab_entry_policy.evaluate_lab_entry(
                smc_confirmed=True,
                top_down_confirmed=True,
                strict_confirmation=False,
                missing_confirmations=[
                    "FIBONACCI_ONDA_2_OU_4",
                    "CAPTURA_LIQUIDEZ",
                ],
                rows=rows,
            )

        self.assertTrue(result["approved"])
        self.assertEqual(result["evidence"]["winrate"], 100)

    def test_never_bypasses_smc_or_top_down(self):
        directory, config_file = self._config_file()
        self.addCleanup(directory.cleanup)
        rows = [shadow("WIN_2R"), shadow("WIN_2R")]

        with patch.object(lab_entry_policy, "CONFIG_FILE", config_file):
            no_smc = lab_entry_policy.evaluate_lab_entry(
                False,
                True,
                False,
                ["FIBONACCI_ONDA_2_OU_4"],
                rows,
            )
            no_top_down = lab_entry_policy.evaluate_lab_entry(
                True,
                False,
                False,
                ["FIBONACCI_ONDA_2_OU_4"],
                rows,
            )

        self.assertFalse(no_smc["approved"])
        self.assertFalse(no_top_down["approved"])

    def test_rejects_unproven_missing_confirmation(self):
        directory, config_file = self._config_file()
        self.addCleanup(directory.cleanup)

        with patch.object(lab_entry_policy, "CONFIG_FILE", config_file):
            result = lab_entry_policy.evaluate_lab_entry(
                True,
                True,
                False,
                ["SMC_CHOCH_BOS"],
                [shadow("WIN_2R"), shadow("WIN_2R")],
            )

        self.assertFalse(result["approved"])

    def test_lab_event_can_only_be_used_once(self):
        with tempfile.TemporaryDirectory() as directory:
            event_file = Path(directory) / "events.json"
            with patch.object(
                lab_entry_policy,
                "LAB_EVENT_FILE",
                event_file,
            ):
                self.assertTrue(
                    lab_entry_policy.lab_event_available("evento-1")
                )
                self.assertTrue(
                    lab_entry_policy.mark_lab_event("evento-1")
                )
                self.assertFalse(
                    lab_entry_policy.lab_event_available("evento-1")
                )


if __name__ == "__main__":
    unittest.main()
