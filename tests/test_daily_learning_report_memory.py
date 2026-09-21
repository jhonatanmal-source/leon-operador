import csv
import json
import tempfile
from datetime import date
from pathlib import Path
from unittest import TestCase, mock

import src.daily_learning_report as report


def write_csv(path, fields, rows):
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fields, delimiter=";")
        writer.writeheader()
        writer.writerows(rows)


class DailyLearningReportMemoryTests(TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.files = {
            name: self.root / name
            for name in (
                "trade_memory.csv",
                "trade_plan_memory.csv",
                "brain_memory.csv",
                "brain_context_memory.csv",
                "price_history.csv",
                "candle_history.csv",
                "signals.csv",
                "pre_operation_trades.csv",
                "memory_identity_registry.json",
                "market_context_memory.csv",
                "daily_learning_report.txt",
            )
        }
        targets = {
            "TRADE_MEMORY_FILE": self.files["trade_memory.csv"],
            "TRADE_PLAN_MEMORY_FILE": self.files["trade_plan_memory.csv"],
            "BRAIN_MEMORY_FILE": self.files["brain_memory.csv"],
            "BRAIN_CONTEXT_MEMORY_FILE": self.files["brain_context_memory.csv"],
            "PRICE_HISTORY_FILE": self.files["price_history.csv"],
            "CANDLE_HISTORY_FILE": self.files["candle_history.csv"],
            "SIGNALS_FILE": self.files["signals.csv"],
            "PRE_OPERATION_FILE": self.files["pre_operation_trades.csv"],
            "IDENTITY_REGISTRY_FILE": self.files[
                "memory_identity_registry.json"
            ],
            "MARKET_CONTEXT_MEMORY_FILE": self.files[
                "market_context_memory.csv"
            ],
            "DAILY_LEARNING_FILE": self.files["daily_learning_report.txt"],
            "REPORTS_DIR": self.root,
        }
        self.patches = [
            mock.patch.object(report, name, value)
            for name, value in targets.items()
        ]
        for item in self.patches:
            item.start()

        write_csv(
            self.files["pre_operation_trades.csv"],
            ["id", "identity_version"],
            [
                {"id": "PREOP-000001", "identity_version": "LEON_PREOP_ID_V2"},
                {"id": "PREOP-000002", "identity_version": "LEON_PREOP_ID_V2"},
            ],
        )
        self.files["memory_identity_registry.json"].write_text(
            json.dumps({
                "records": [
                    {"canonical_id": "PREOP-000001"},
                    {"canonical_id": "PREOP-000002"},
                ]
            }),
            encoding="utf-8",
        )
        write_csv(
            self.files["market_context_memory.csv"],
            ["pre_operation_id"],
            [
                {"pre_operation_id": "PREOP-000001"},
                {"pre_operation_id": "PREOP-000002"},
            ],
        )
        write_csv(
            self.files["brain_memory.csv"],
            ["brain_score", "confianca", "resultado"],
            [
                {"brain_score": "20", "confianca": "BAIXA", "resultado": "ERRO"},
                {"brain_score": "20", "confianca": "BAIXA", "resultado": "ERRO"},
                {"brain_score": "20", "confianca": "BAIXA", "resultado": "ERRO"},
            ],
        )

    def tearDown(self):
        for item in reversed(self.patches):
            item.stop()
        self.temp.cleanup()

    def test_memory_integrity_is_not_confused_with_win_rate(self):
        output = report.gerar_relatorio_aprendizado_diario(
            date(2026, 7, 26)
        )

        self.assertIn(
            "LEON VPS | RELATORIO DIARIO DE APRENDIZADO",
            output,
        )
        self.assertIn("Integridade da memoria: 100.00%", output)
        self.assertIn("Contextos vinculados: 2 / 2", output)
        self.assertIn("Resultados historicos usados no aprendizado", output)
        self.assertIn("Taxa historica de acerto: 0.00%", output)
