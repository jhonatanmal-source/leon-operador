import unittest
from datetime import date

from setup_audit import audit_setup_records


class SetupAuditTests(unittest.TestCase):

    def test_learning_only_is_safe_without_open_operations(self):
        audit = audit_setup_records(
            pre_operations=[],
            orders=[],
            execution={
                "demo_execution_enabled": False,
                "execution_enabled": False,
                "demo_only": True,
            },
            reference_date=date(2026, 6, 18),
        )

        self.assertEqual(audit["status"], "SAFE_LEARNING")

    def test_neutral_smc_execution_is_flagged(self):
        pre_operations = [{
            "id": "PREOP-TEST",
            "data_abertura": "2026-06-18T01:00:00",
            "status": "FECHADO",
            "smc": "NEUTRO",
            "bos": "SEM_BOS",
            "choch": "SEM_CHOCH",
        }]
        orders = [{
            "data": "2026-06-18T01:01:00",
            "pre_operation_id": "PREOP-TEST",
            "status": "ENVIADA",
        }]

        audit = audit_setup_records(
            pre_operations,
            orders,
            {
                "demo_execution_enabled": False,
                "execution_enabled": False,
                "demo_only": True,
            },
            date(2026, 6, 18),
        )

        self.assertEqual(
            audit["metrics"]["historical_structural_violations_today"],
            1,
        )


if __name__ == "__main__":
    unittest.main()
