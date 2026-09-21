import sys
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch


from web_app.services import system_health_service


class WebActiveErrorsTests(unittest.TestCase):

    def test_resolved_old_errors_are_hidden(self):
        with tempfile.TemporaryDirectory() as directory:
            logs = Path(directory)
            old = datetime.now() - timedelta(days=2)
            recent = datetime.now() - timedelta(minutes=1)
            (logs / "errors.txt").write_text(
                f"{old.isoformat()} | OPERATOR | falha na analise: MemoryError\n",
                encoding="utf-8",
            )
            (logs / "leon_log.txt").write_text(
                f"[{recent.isoformat()}] OPERATOR | analise programada executada\n",
                encoding="utf-8",
            )

            with patch.object(system_health_service, "LOGS_DIR", logs):
                result = system_health_service._active_errors()

        self.assertIn("Sem erros ativos", result)
        self.assertNotIn("MemoryError", result)


if __name__ == "__main__":
    unittest.main()
