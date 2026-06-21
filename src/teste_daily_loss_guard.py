import unittest

from risk_control_agent import calcular_limite_perda_diaria


class DailyLossGuardTests(unittest.TestCase):

    def test_allows_profitable_day_without_profit_cap(self):
        result = calcular_limite_perda_diaria(
            saldo_atual=10200,
            resultado_realizado=200,
            resultado_aberto=150,
            limite_percentual=2,
        )

        self.assertTrue(result["approved"])
        self.assertEqual(result["total_result"], 350)

    def test_allows_loss_below_two_percent(self):
        result = calcular_limite_perda_diaria(
            saldo_atual=9900,
            resultado_realizado=-100,
            resultado_aberto=-50,
            limite_percentual=2,
        )

        self.assertTrue(result["approved"])
        self.assertEqual(result["current_loss_percent"], 1.5)

    def test_blocks_when_total_loss_reaches_two_percent(self):
        result = calcular_limite_perda_diaria(
            saldo_atual=9850,
            resultado_realizado=-150,
            resultado_aberto=-50,
            limite_percentual=2,
        )

        self.assertFalse(result["approved"])
        self.assertEqual(result["reason"], "DAILY_LOSS_LIMIT_REACHED")


if __name__ == "__main__":
    unittest.main()
