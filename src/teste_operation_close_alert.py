import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import operation_close_alert as alert


class OperationCloseAlertTests(unittest.TestCase):

    def test_already_sent_is_successfully_skipped(self):
        operation = {
            "id": "PREOP-000106",
            "resultado": "LOSS",
        }

        with tempfile.TemporaryDirectory() as folder:
            state_file = Path(folder) / "alerts.json"
            state_file.write_text(
                '["PREOP-000106:LOSS"]',
                encoding="utf-8",
            )

            with patch.object(alert, "STATE_FILE", state_file):
                result = alert.send_operation_close_alert(operation)

        self.assertTrue(result["ok"])
        self.assertTrue(result["skipped"])
        self.assertEqual(
            result["reason"],
            "OPERATION_CLOSE_ALERT_ALREADY_SENT",
        )


if __name__ == "__main__":
    unittest.main()
