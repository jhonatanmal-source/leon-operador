import csv
import importlib.util
import io
import json
import os
import tarfile
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import src.operation_close_alert as operation_close_alert
import src.pre_operation_engine as pre_operation_engine


def _write_csv(path, fields, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fields, delimiter=";")
        writer.writeheader()
        writer.writerows(rows)


def _read_csv(path):
    with path.open("r", encoding="utf-8", newline="") as file:
        return list(csv.DictReader(file, delimiter=";"))


def _read_csv_with_fields(path):
    with path.open("r", encoding="utf-8", newline="") as file:
        reader = csv.DictReader(file, delimiter=";")
        return list(reader.fieldnames or []), list(reader)


def _migration_module():
    path = (
        Path(__file__).resolve().parent.parent
        / "scripts"
        / "migrate_pre_operation_identity_v2.py"
    )
    spec = importlib.util.spec_from_file_location("migrate_preop_identity_v2", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class PersistentPreOperationIdentityTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.data = Path(self.temp.name)
        self.sequence = self.data / "pre_operation_sequence.json"
        self.environment = patch.dict(
            os.environ,
            {"LEON_PREOP_SEQUENCE_FILE": str(self.sequence)},
        )
        self.environment.start()

    def tearDown(self):
        self.environment.stop()
        self.temp.cleanup()

    def test_sequence_survives_current_csv_reset(self):
        first = pre_operation_engine._proximo_id([{"id": "PREOP-000412"}])
        second = pre_operation_engine._proximo_id([])

        self.assertEqual(first, "PREOP-000413")
        self.assertEqual(second, "PREOP-000414")
        state = json.loads(self.sequence.read_text(encoding="utf-8"))
        self.assertEqual(state["last_value"], 414)
        self.assertEqual(state["identity_version"], "LEON_PREOP_ID_V2")

    def test_sequence_uses_larger_live_id_without_reuse(self):
        self.sequence.write_text(
            json.dumps({"last_value": 10, "last_id": "PREOP-000010"}),
            encoding="utf-8",
        )

        result = pre_operation_engine._proximo_id([{"id": "PREOP-000099"}])

        self.assertEqual(result, "PREOP-000100")

    def test_native_preop_is_registered_with_stable_identity(self):
        preop_file = self.data / "pre_operation_trades.csv"
        with (
            patch.object(pre_operation_engine, "DATA_DIR", self.data),
            patch.object(
                pre_operation_engine,
                "PRE_OPERATION_FILE",
                preop_file,
            ),
        ):
            record = pre_operation_engine.registrar_pre_operacao(
                ativo="Gold_Spot",
                direcao="AGUARDAR",
                status_setup="SETUP FRACO",
                operacao=None,
                smc="NEUTRAL",
                elliott="NEUTRAL",
                bos="NONE",
                choch="NONE",
                confianca="BAIXA",
                brain_score=0,
            )

        registry = json.loads(
            (self.data / "memory_identity_registry.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(record["legacy_id"], record["id"])
        self.assertEqual(registry["records_total"], 1)
        self.assertEqual(
            registry["records"][0]["canonical_id"],
            record["id"],
        )


class CloseAlertIdentityTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.data = Path(self.temp.name)
        self.state = self.data / "operation_close_alerts.json"
        self.patches = [
            patch.object(operation_close_alert, "DATA_DIR", self.data),
            patch.object(operation_close_alert, "STATE_FILE", self.state),
            patch.object(
                operation_close_alert,
                "enviar_mensagem",
                return_value={"ok": True},
            ),
        ]
        for item in self.patches:
            item.start()

    def tearDown(self):
        for item in reversed(self.patches):
            item.stop()
        self.temp.cleanup()

    def test_same_legacy_id_and_result_are_distinct_by_close_time(self):
        first = {
            "id": "PREOP-000116",
            "resultado": "WIN_TP1",
            "data_fechamento": "2026-07-23T10:00:00",
        }
        second = {
            "id": "PREOP-000116",
            "resultado": "WIN_TP1",
            "data_fechamento": "2026-07-26T10:00:00",
        }

        self.assertTrue(operation_close_alert.send_operation_close_alert(first)["ok"])
        self.assertTrue(operation_close_alert.send_operation_close_alert(second)["ok"])
        duplicate = operation_close_alert.send_operation_close_alert(second)

        self.assertTrue(duplicate["skipped"])
        sent = json.loads(self.state.read_text(encoding="utf-8"))
        self.assertEqual(len(sent), 2)


class MemoryIdentityMigrationTests(unittest.TestCase):
    PREOP_FIELDS = [
        "id",
        "data_abertura",
        "data_fechamento",
        "ativo",
        "direcao",
        "resultado",
        "region_id",
    ]

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.base = Path(self.temp.name)
        self.root = self.base / "app"
        self.data = self.root / "data"
        self.backups = self.base / "backups"
        self.config = self.base / "config"
        self.data.mkdir(parents=True)
        self.backups.mkdir()
        self.config.mkdir()
        self.module = _migration_module()

        archived = {
            "id": "PREOP-000001",
            "data_abertura": "2026-07-22T10:00:00",
            "data_fechamento": "2026-07-22T11:00:00",
            "ativo": "Gold_Spot",
            "direcao": "COMPRA",
            "resultado": "WIN_TP1",
            "region_id": "REG-OLD",
        }
        text = io.StringIO(newline="")
        writer = csv.DictWriter(
            text,
            fieldnames=self.PREOP_FIELDS,
            delimiter=";",
        )
        writer.writeheader()
        writer.writerow(archived)
        archive = self.backups / "leon_20260722.tar.gz"
        with tarfile.open(archive, "w:gz") as bundle:
            payload = text.getvalue().encode("utf-8")
            info = tarfile.TarInfo("data/pre_operation_trades.csv")
            info.size = len(payload)
            bundle.addfile(info, io.BytesIO(payload))

        current = {
            "id": "PREOP-000001",
            "data_abertura": "2026-07-24T10:00:00",
            "data_fechamento": "2026-07-24T11:00:00",
            "ativo": "Gold_Spot",
            "direcao": "COMPRA",
            "resultado": "WIN_TP1",
            "region_id": "REG-CURRENT",
        }
        _write_csv(
            self.data / "pre_operation_trades.csv",
            self.PREOP_FIELDS,
            [current],
        )
        _write_csv(
            self.data / "market_context_memory.csv",
            ["data", "pre_operation_id", "resultado"],
            [{
                "data": "2026-07-22T10:00:00",
                "pre_operation_id": "PREOP-000001",
                "resultado": "WIN_TP1",
            }],
        )
        _write_csv(
            self.data / "mt5_order_memory.csv",
            ["data", "pre_operation_id", "resultado"],
            [{
                "data": "2026-07-24T10:05:00",
                "pre_operation_id": "PREOP-000001",
                "resultado": "WIN_TP1",
            }],
        )
        _write_csv(
            self.data / "operation_decisions.csv",
            ["data", "pre_operation_id", "resultado"],
            [{
                "data": "2026-07-24T10:01:00",
                "pre_operation_id": "PREOP-000001",
                "resultado": "",
            }],
        )
        (self.data / "interest_zones.json").write_text(
            json.dumps([{"region_id": "REG-CURRENT", "pre_operation_id": ""}]),
            encoding="utf-8",
        )
        (self.data / "operation_close_alerts.json").write_text(
            json.dumps(["PREOP-000001:WIN_TP1"]),
            encoding="utf-8",
        )
        (self.data / "mt5_closed_operations_processed.json").write_text(
            json.dumps(
                ["PREOP-000001:WIN_TP1:2026-07-24T11:00:00"]
            ),
            encoding="utf-8",
        )

    def tearDown(self):
        self.temp.cleanup()

    def test_migration_reconciles_reused_ids_and_is_idempotent(self):
        report = self.module.migrate(self.root, apply=True)

        self.assertEqual(report["historical_records_registered"], 2)
        migrated = _read_csv(self.data / "pre_operation_trades.csv")
        self.assertEqual(migrated[0]["id"], "PREOP-000002")
        self.assertEqual(migrated[0]["legacy_id"], "PREOP-000001")
        self.assertEqual(
            migrated[0]["identity_version"],
            "LEON_PREOP_ID_V2",
        )

        orders = _read_csv(self.data / "mt5_order_memory.csv")
        self.assertEqual(orders[0]["pre_operation_id"], "PREOP-000002")
        contexts = _read_csv(self.data / "market_context_memory.csv")
        self.assertEqual(
            {row["pre_operation_id"] for row in contexts},
            {"PREOP-000001", "PREOP-000002"},
        )
        zones = json.loads(
            (self.data / "interest_zones.json").read_text(encoding="utf-8")
        )
        self.assertEqual(zones[0]["pre_operation_id"], "PREOP-000002")
        sequence = json.loads(
            (self.config / "pre_operation_sequence.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(sequence["last_value"], 2)

        registry_before = json.loads(
            (self.data / "memory_identity_registry.json").read_text(
                encoding="utf-8"
            )
        )
        record_hashes_before = [
            record["record_hash"] for record in registry_before["records"]
        ]
        second = self.module.migrate(self.root, apply=True)
        registry_after = json.loads(
            (self.data / "memory_identity_registry.json").read_text(
                encoding="utf-8"
            )
        )
        record_hashes_after = [
            record["record_hash"] for record in registry_after["records"]
        ]

        self.assertEqual(second["historical_records_registered"], 2)
        self.assertEqual(record_hashes_before, record_hashes_after)
        self.assertEqual(
            _read_csv(self.data / "pre_operation_trades.csv")[0]["id"],
            "PREOP-000002",
        )
        dry_run = self.module.migrate(self.root, apply=False)
        self.assertEqual(
            dry_run["csv_references_remapped"],
            {
                "market_context_memory.csv": 0,
                "mt5_order_memory.csv": 0,
                "operation_decisions.csv": 0,
            },
        )

    def test_migration_is_read_only_by_default(self):
        before = (
            self.data / "pre_operation_trades.csv"
        ).read_bytes()

        report = self.module.migrate(self.root, apply=False)

        self.assertEqual(report["status"], "DRY_RUN")
        self.assertEqual(
            (self.data / "pre_operation_trades.csv").read_bytes(),
            before,
        )
        self.assertFalse(
            (self.data / "memory_identity_registry.json").exists()
        )

    def test_existing_closed_record_is_marked_as_historical_alert(self):
        (self.data / "operation_close_alerts.json").write_text(
            "[]",
            encoding="utf-8",
        )

        self.module.migrate(self.root, apply=True)

        sent = json.loads(
            (self.data / "operation_close_alerts.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertIn(
            "PREOP-000002:WIN_TP1:2026-07-24T11:00:00",
            sent,
        )

    def test_empty_live_memory_recovers_archive_and_new_zone_evidence(self):
        _write_csv(
            self.data / "pre_operation_trades.csv",
            self.PREOP_FIELDS,
            [],
        )
        (self.data / "interest_zones.json").write_text(
            json.dumps([
                {
                    "region_id": "REG-NEW",
                    "zone_id": "REG-NEW",
                    "cycle_id": "lab-new",
                    "analysis_id": "lab-bootstrap",
                    "created_at": "2026-07-24T13:05:00+00:00",
                    "zone_source": "LABORATORIO",
                    "region_direction": "BULLISH",
                    "current_price": 4100.0,
                    "invalidation_price": 4090.0,
                    "target_prices": [4115.0, 4130.0],
                    "structural_confirmations": [{"brain_score": 60}],
                }
            ]),
            encoding="utf-8",
        )

        report = self.module.migrate(self.root, apply=True)

        rows = _read_csv(self.data / "pre_operation_trades.csv")
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[-1]["legacy_id"], "PREOP-000002")
        self.assertEqual(rows[-1]["region_id"], "REG-NEW")
        self.assertEqual(rows[-1]["elliott"], "NAO_PERSISTIDO")
        self.assertEqual(
            report["live_memory_recovery"]["zone_evidence_records"],
            1,
        )

    def test_migration_has_no_order_surface(self):
        source = (
            Path(self.module.__file__).read_text(encoding="utf-8")
        )

        self.assertNotIn("order_send(", source)
        self.assertNotIn("order_check(", source)

    def test_orphan_context_is_preserved_without_false_preop_link(self):
        fields, contexts = _read_csv_with_fields(
            self.data / "market_context_memory.csv"
        )
        contexts.append({
            "data": "2026-07-20T01:00:00",
            "pre_operation_id": "PREOP-000777",
            "resultado": "EM_SIMULACAO",
        })
        _write_csv(
            self.data / "market_context_memory.csv",
            fields,
            contexts,
        )

        first = self.module.migrate(self.root, apply=True)
        second = self.module.migrate(self.root, apply=False)
        rows = _read_csv(self.data / "market_context_memory.csv")
        orphan = next(
            row
            for row in rows
            if row.get("legacy_pre_operation_id") == "PREOP-000777"
        )

        self.assertTrue(
            orphan["pre_operation_id"].startswith("LEGACY-UNRESOLVED-")
        )
        self.assertEqual(
            orphan["identity_resolution"],
            "LEGACY_UNRESOLVED_REFERENCE",
        )
        self.assertEqual(
            first["unresolved_csv_references"]["market_context_memory.csv"],
            1,
        )
        self.assertEqual(
            second["csv_references_remapped"]["market_context_memory.csv"],
            0,
        )


if __name__ == "__main__":
    unittest.main()
