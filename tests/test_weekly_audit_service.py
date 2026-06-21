import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import patch

from web_app.services import weekly_audit_service


class WeeklyAuditServiceTests(unittest.TestCase):

    def test_flags_executed_operation_without_complete_structure(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            preops = root / "preops.csv"
            decisions = root / "decisions.csv"
            errors = root / "errors.txt"
            preops.write_text(
                "id;data_abertura;status;resultado;smc;bos;choch;status_setup\n"
                "P-1;2026-06-20T10:00:00;FECHADO;LOSS;NEUTRO;SEM_BOS;SEM_CHOCH;SETUP FRACO\n",
                encoding="utf-8",
            )
            decisions.write_text(
                "data;decisao;motivo;rr_real\n",
                encoding="utf-8",
            )
            errors.write_text("", encoding="utf-8")

            with patch.object(
                weekly_audit_service,
                "PRE_OPERATIONS_FILE",
                preops,
            ), patch.object(
                weekly_audit_service,
                "DECISIONS_FILE",
                decisions,
            ), patch.object(
                weekly_audit_service,
                "ERRORS_FILE",
                errors,
            ), patch.object(
                weekly_audit_service,
                "ORDERS_FILE",
                root / "missing-orders.csv",
            ), patch.object(
                weekly_audit_service,
                "_human_analysis_metrics",
                return_value={
                    "total": 0,
                    "pending": 0,
                    "approved": 0,
                    "rejected": 0,
                },
            ):
                findings = weekly_audit_service._build_findings(
                    weekly_audit_service._read_csv(preops),
                    [],
                    [],
                    {
                        "total": 0,
                        "pending": 0,
                        "approved": 0,
                        "rejected": 0,
                    },
                    executed_operation_ids={"P-1"},
                )

        self.assertEqual(findings[0]["severity"], "CRITICO")

    def test_weak_observation_is_information_not_operational_error(self):
        findings = weekly_audit_service._build_findings(
            [{
                "id": "P-2",
                "status": "OBSERVADO",
                "resultado": "SEM_ENTRADA",
                "smc": "NEUTRO",
                "bos": "SEM_BOS",
                "choch": "SEM_CHOCH",
                "status_setup": "SETUP FRACO",
            }],
            [],
            [],
            {"total": 0, "pending": 0, "approved": 0, "rejected": 0},
        )

        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["severity"], "INFO")


if __name__ == "__main__":
    unittest.main()
