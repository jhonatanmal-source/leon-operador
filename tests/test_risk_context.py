import sys
import unittest
from pathlib import Path
from unittest.mock import patch


import src.risk_control_agent as risk_control_agent


class RiskContextTests(unittest.TestCase):

    def test_correction_uses_half_of_primary_risk(self):
        base = {
            "entrada": 2000,
            "stop": 1990,
            "metodo_risco": "SMC_TECNICO_VARIAVEL",
        }
        config = {
            "enabled": True,
            "risk_percent": 0.5,
            "max_risk_percent": 1.0,
            "daily_loss_percent": 2.0,
            "max_lot": 1.0,
            "min_lot": 0.01,
            "correction_risk_factor": 0.5,
            "max_open_risk_percent": 1.0,
        }

        with patch.object(
            risk_control_agent,
            "_risk_config",
            return_value=config,
        ):
            primary = risk_control_agent.calcular_plano_risco(
                {**base, "context_mode": "TENDENCIA"},
                saldo=10000,
            )
            correction = risk_control_agent.calcular_plano_risco(
                {**base, "context_mode": "CORRECAO"},
                saldo=10000,
            )

        self.assertEqual(primary["risk_percent"], 0.5)
        self.assertEqual(correction["risk_percent"], 0.25)


if __name__ == "__main__":
    unittest.main()
