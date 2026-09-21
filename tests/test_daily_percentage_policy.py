import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src import daily_entry_guard as daily
from src import risk_control_agent as risk


class DailyPolicyTests(unittest.TestCase):
    def test_giveback_latches_until_next_day(self):
        state = daily.update_daily_state({}, "2026-09-09", 500, 10000)
        self.assertTrue(daily.update_daily_state(state, "2026-09-09", 251, 10000)["approved"])
        state = daily.update_daily_state(state, "2026-09-09", 250, 10000)
        self.assertFalse(state["approved"])
        self.assertFalse(daily.update_daily_state(state, "2026-09-09", 150, 10000)["approved"])
        self.assertTrue(daily.update_daily_state(state, "2026-09-10", 0, 10000)["approved"])

    def test_daily_loss_and_no_positive_peak(self):
        self.assertTrue(daily.update_daily_state({}, "today", -1, 10000)["approved"])
        state = daily.update_daily_state({}, "today", -200, 10000)
        self.assertEqual(state["reason"], "DAILY_STOP_REACHED")
        self.assertFalse(daily.update_daily_state(state, "today", 0, 10000)["approved"])

    def test_persistence_and_account_isolation(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(daily, "STATE_FILE", Path(directory) / "state.json"):
            daily.evaluate_daily_entry_guard("a", "today", 500, 10000)
            self.assertFalse(daily.evaluate_daily_entry_guard("a", "today", 249, 10000)["approved"])
            self.assertTrue(daily.evaluate_daily_entry_guard("b", "today", 0, 10000)["approved"])


class PercentageSizingTests(unittest.TestCase):
    def plan(self, balance=10000, stop=1990, minimum=0.01):
        config = dict(enabled=True, percentage_sizing=True, risk_percent=0.5, max_risk_percent=0.5,
                      min_lot=0.01, max_lot=0.1, correction_risk_factor=0.5, daily_loss_percent=2)
        method = dict(risk_percent=1, name="test", rr_target=1.5)
        with patch.object(risk, "_risk_config", return_value=config), patch.object(risk, "obter_metodo", return_value=method):
            return risk.calcular_plano_risco({"entrada": 2000, "stop": stop}, saldo=balance,
                especificacoes=dict(contract_size=100, volume_min=minimum, volume_max=100, volume_step=0.01,
                                    tick_size=0.01, tick_value=1))

    def test_lot_scales_with_capital_and_stop(self):
        self.assertEqual(self.plan()["lot"], 0.05)
        self.assertEqual(self.plan(balance=20000)["lot"], 0.1)
        self.assertEqual(self.plan(stop=1999)["lot"], 0.5)
        self.assertEqual(self.plan(stop=1999)["estimated_risk_percent"], 0.5)

    def test_minimum_must_not_exceed_risk(self):
        result = self.plan(balance=100, minimum=0.1)
        self.assertEqual(result["error"], "LOT_BELOW_MINIMUM_EXCEEDS_RISK")


if __name__ == "__main__":
    unittest.main()
