import unittest

from smc_entry_guard import classify_operational_smc, validate_smc_entry


class SmcEntryGuardTests(unittest.TestCase):

    def test_blocks_yesterday_loss_pattern(self):
        result = validate_smc_entry(
            "VENDA",
            "NEUTRO",
            "SEM_BOS",
            "SEM_CHOCH",
        )

        self.assertFalse(result["approved"])
        self.assertIn("SMC", result["reason"])
        self.assertIn("BOS", result["reason"])
        self.assertIn("CHOCH", result["reason"])

    def test_blocks_opposite_structure(self):
        result = validate_smc_entry(
            "VENDA",
            "BEARISH",
            "BOS_BULLISH",
            "CHOCH_BULLISH",
        )

        self.assertFalse(result["approved"])

    def test_allows_confirmed_bearish_structure(self):
        smc = classify_operational_smc(
            "VENDA",
            "BOS_BEARISH",
            "CHOCH_BEARISH",
            "FVG_BEARISH",
        )
        result = validate_smc_entry(
            "VENDA",
            smc,
            "BOS_BEARISH",
            "CHOCH_BEARISH",
        )

        self.assertEqual(smc, "BEARISH")
        self.assertTrue(result["approved"])

    def test_allows_confirmed_bullish_structure(self):
        smc = classify_operational_smc(
            "COMPRA",
            "BOS_BULLISH",
            "CHOCH_BULLISH",
            "FVG_BULLISH",
        )
        result = validate_smc_entry(
            "COMPRA",
            smc,
            "BOS_BULLISH",
            "CHOCH_BULLISH",
        )

        self.assertEqual(smc, "BULLISH")
        self.assertTrue(result["approved"])


if __name__ == "__main__":
    unittest.main()
