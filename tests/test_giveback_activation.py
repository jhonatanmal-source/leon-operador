import unittest

from src.daily_entry_guard import update_daily_state


class GivebackActivationTests(unittest.TestCase):
    def evaluate(self, state, profit, **kwargs):
        return update_daily_state(state, "today", profit, 10000,
                                  closed_pnl=profit, **kwargs)

    def test_threshold_is_strict(self):
        for peak in (12.48, 399.99, 400):
            state = self.evaluate({}, peak)
            state = self.evaluate(state, 0)
            self.assertTrue(state["approved"])
            self.assertFalse(state["giveback_armed"])

    def test_half_peak_and_latch(self):
        state = self.evaluate({}, 400.02)
        self.assertTrue(state["giveback_armed"])
        self.assertTrue(self.evaluate(state, 200.02)["approved"])
        state = self.evaluate(state, 200.01)
        self.assertEqual(state["reason"], "DAILY_PROFIT_GIVEBACK_REACHED")
        self.assertFalse(self.evaluate(state, 600)["approved"])

    def test_peak_tracks_higher_closed_profit(self):
        state = self.evaluate({}, 500)
        state = self.evaluate(state, 800)
        self.assertTrue(self.evaluate(state, 401)["approved"])
        self.assertFalse(self.evaluate(state, 400)["approved"])

    def test_history_reconstructs_peak(self):
        self.assertFalse(self.evaluate({}, 250, closed_peak=500)["approved"])

    def test_floating_profit_does_not_arm(self):
        state = update_daily_state({}, "today", 1000, 10000, closed_pnl=10)
        self.assertFalse(state["giveback_armed"])

    def test_old_small_peak_pause_migrates(self):
        old = dict(day="today", peak=12.48, basis="closed",
                   reason="DAILY_PROFIT_GIVEBACK_REACHED")
        self.assertTrue(self.evaluate(old, -31.56)["approved"])
        self.assertEqual(self.evaluate(old, -200)["reason"], "DAILY_STOP_REACHED")

    def test_old_qualified_pause_and_stop_preserved(self):
        for reason in ("DAILY_PROFIT_GIVEBACK_REACHED", "DAILY_STOP_REACHED"):
            old = dict(day="today", peak=500, basis="closed", reason=reason)
            self.assertFalse(self.evaluate(old, 600)["approved"])

    def test_threshold_scales_and_day_resets(self):
        state = update_daily_state({}, "yesterday", 800, 20000, closed_pnl=800)
        self.assertFalse(state["giveback_armed"])
        state = update_daily_state(state, "today", 0, 20000, closed_pnl=0)
        self.assertEqual(state["peak"], 0)
        self.assertTrue(state["approved"])

    def test_day_capital_grows_independently_of_mesa_baseline(self):
        state = self.evaluate({}, 420, giveback_balance=11000)
        self.assertFalse(state["giveback_armed"])
        self.assertEqual(state["giveback_activation_amount"], 440)
        state = self.evaluate(state, 450, giveback_balance=11450)
        self.assertTrue(state["giveback_armed"])
        self.assertEqual(state["giveback_day_balance"], 11000)
        state = update_daily_state(state, "tomorrow", 0, 10000,
                                   closed_pnl=0, giveback_balance=11450)
        self.assertEqual(state["giveback_activation_amount"], 458)

    def test_larger_account_and_daily_stop_unchanged(self):
        state = self.evaluate({}, 600, giveback_balance=50000)
        self.assertEqual(state["giveback_activation_amount"], 2000)
        self.assertFalse(state["giveback_armed"])
        self.assertEqual(self.evaluate(state, -200)["reason"], "DAILY_STOP_REACHED")
