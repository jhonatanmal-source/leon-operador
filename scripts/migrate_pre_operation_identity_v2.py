#!/usr/bin/env python3
"""Reconcile PRE_OPERATION identities without rewriting archived evidence."""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import os
import shutil
import tarfile
import tempfile
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo


IDENTITY_VERSION = "LEON_PREOP_ID_V2"
PREOP_FILE = "pre_operation_trades.csv"
REGISTRY_FILE = "memory_identity_registry.json"
REPORT_FILE = "memory_identity_migration_v2.json"
SEQUENCE_FILE = "pre_operation_sequence.json"
PREOP_IDENTITY_FIELDS = (
    "cycle_id",
    "analysis_id",
    "identity_version",
    "legacy_id",
)


def read_csv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    if not path.exists():
        return [], []
    with path.open("r", encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file, delimiter=";")
        return list(reader.fieldnames or []), list(reader)


def atomic_write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(
        prefix=f".{path.name}.",
        suffix=".tmp",
        dir=path.parent,
    )
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="") as file:
            file.write(content)
            file.flush()
            os.fsync(file.fileno())
        os.replace(temporary, path)
    except Exception:
        try:
            os.unlink(temporary)
        except OSError:
            pass
        raise


def write_csv(path: Path, fields: list[str], rows: list[dict[str, Any]]) -> None:
    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=fields, delimiter=";", extrasaction="ignore")
    writer.writeheader()
    for row in rows:
        writer.writerow({field: row.get(field, "") for field in fields})
    atomic_write_text(path, output.getvalue())


def write_json(path: Path, payload: Any) -> None:
    atomic_write_text(
        path,
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True, default=str)
        + "\n",
    )


def sha256(path: Path) -> str:
    if not path.exists():
        return ""
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def parse_time(value: Any) -> datetime | None:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is not None:
        parsed = parsed.replace(tzinfo=None)
    return parsed


def stable_key(row: dict[str, Any]) -> tuple[str, str, str]:
    return (
        str(row.get("legacy_id") or row.get("id") or "").strip(),
        str(row.get("data_abertura") or "").strip(),
        str(row.get("region_id") or "").strip(),
    )


def load_archive_rows(backup_dir: Path) -> list[tuple[str, dict[str, str]]]:
    records: list[tuple[str, dict[str, str]]] = []
    for archive in sorted(backup_dir.glob("leon_*.tar.gz")):
        try:
            with tarfile.open(archive, "r:gz") as bundle:
                names = [
                    name
                    for name in bundle.getnames()
                    if name == f"data/{PREOP_FILE}"
                    or name.endswith(f"/data/{PREOP_FILE}")
                ]
                if not names:
                    continue
                extracted = bundle.extractfile(names[0])
                if extracted is None:
                    continue
                text = extracted.read().decode("utf-8-sig", "replace")
                rows = list(csv.DictReader(io.StringIO(text), delimiter=";"))
        except (OSError, tarfile.TarError):
            continue
        records.extend((archive.name, row) for row in rows)
    return records


def load_latest_archive_snapshot(
    backup_dir: Path,
) -> tuple[str, list[str], list[dict[str, str]]]:
    for archive in reversed(sorted(backup_dir.glob("leon_*.tar.gz"))):
        try:
            with tarfile.open(archive, "r:gz") as bundle:
                names = [
                    name
                    for name in bundle.getnames()
                    if name == f"data/{PREOP_FILE}"
                    or name.endswith(f"/data/{PREOP_FILE}")
                ]
                if not names:
                    continue
                extracted = bundle.extractfile(names[0])
                if extracted is None:
                    continue
                text = extracted.read().decode("utf-8-sig", "replace")
                reader = csv.DictReader(io.StringIO(text), delimiter=";")
                rows = list(reader)
                if rows:
                    return archive.name, list(reader.fieldnames or []), rows
        except (OSError, tarfile.TarError):
            continue
    return "", [], []


def local_timestamp(value: Any) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return ""
    if parsed.tzinfo is not None:
        parsed = parsed.astimezone(
            ZoneInfo("America/Sao_Paulo")
        ).replace(tzinfo=None)
    return parsed.isoformat(timespec="seconds")


def recover_live_rows_from_persisted_evidence(
    data_dir: Path,
    backup_dir: Path,
) -> tuple[list[str], list[dict[str, str]], dict[str, Any]]:
    archive, fields, rows = load_latest_archive_snapshot(backup_dir)
    if not rows:
        raise RuntimeError("PRE_OPERATION_MEMORY_EMPTY_NO_ARCHIVE")

    zones_path = data_dir / "interest_zones.json"
    if not zones_path.exists():
        raise RuntimeError("PRE_OPERATION_MEMORY_EMPTY_NO_ZONE_EVIDENCE")
    payload = json.loads(zones_path.read_text(encoding="utf-8"))
    zones = payload if isinstance(payload, list) else payload.get("zones", [])

    known_regions = {str(row.get("region_id") or "") for row in rows}
    last_opened = max(
        (parse_time(row.get("data_abertura")) or datetime.min for row in rows),
        default=datetime.min,
    )
    candidates = []
    for zone in zones:
        if not isinstance(zone, dict):
            continue
        region_id = str(zone.get("region_id") or zone.get("zone_id") or "")
        opened_at = local_timestamp(zone.get("created_at"))
        opened = parse_time(opened_at)
        if (
            not region_id
            or region_id in known_regions
            or opened is None
            or opened <= last_opened
            or str(zone.get("zone_source") or "").upper() != "LABORATORIO"
        ):
            continue
        candidates.append((opened, zone))

    next_value = max((numeric_id(row.get("id")) for row in rows), default=0)
    recovered = []
    for _, zone in sorted(candidates, key=lambda item: item[0]):
        next_value += 1
        direction = str(zone.get("region_direction") or "").upper()
        is_buy = direction == "BULLISH"
        targets = list(zone.get("target_prices") or [])
        entry = zone.get("current_price")
        stop = zone.get("invalidation_price")
        tp1 = targets[0] if targets else ""
        tp2 = targets[1] if len(targets) > 1 else ""
        try:
            risk = abs(float(entry) - float(stop))
            rr = round(abs(float(tp2) - float(entry)) / risk, 2) if risk else 0
        except (TypeError, ValueError):
            rr = ""
        confirmations = list(zone.get("structural_confirmations") or [])
        brain_score = (
            confirmations[-1].get("brain_score", "")
            if confirmations and isinstance(confirmations[-1], dict)
            else ""
        )
        opened_at = local_timestamp(zone.get("created_at"))
        record = {
            "id": f"PREOP-{next_value:06d}",
            "data_abertura": opened_at,
            "data_fechamento": "",
            "ativo": "Gold_Spot",
            "direcao": "COMPRA" if is_buy else "VENDA",
            "status_setup": "SETUP FRACO",
            "metodo_risco": "SMC_TECNICO_VARIAVEL",
            "context_mode": "LAB_LEARNING",
            "entrada": entry,
            "stop": stop,
            "tp1": tp1,
            "tp2": tp2,
            "rr": rr,
            "smc": "BULLISH" if is_buy else "BEARISH",
            "elliott": "NAO_PERSISTIDO",
            "bos": "BOS_BULLISH" if is_buy else "BOS_BEARISH",
            "choch": "CHOCH_BULLISH" if is_buy else "CHOCH_BEARISH",
            "confianca": (
                "ALTA"
                if str(brain_score).isdigit() and int(brain_score) >= 70
                else "MÉDIA"
            ),
            "brain_score": brain_score,
            "status": "ABERTO",
            "resultado": "EM_SIMULACAO",
            "observacao": (
                "RECOVERED_FROM_PERSISTED_ZONE_EVIDENCE: plano, identidade "
                "regional e horario recuperados sem inferir contexto Elliott."
            ),
            "region_id": str(
                zone.get("region_id") or zone.get("zone_id") or ""
            ),
            "structural_gate_version": "LEON_CAUSAL_CONTRACT_V2",
            "structural_gate_timestamp": opened_at,
            "structural_gate_result": "PASSED",
            "cycle_id": str(zone.get("cycle_id") or ""),
            "analysis_id": str(zone.get("analysis_id") or ""),
        }
        rows.append({key: str(value) for key, value in record.items()})
        recovered.append(record["id"])

    if not recovered:
        raise RuntimeError("PRE_OPERATION_MEMORY_EMPTY_NO_NEW_EVIDENCE")
    return fields, rows, {
        "source_archive": archive,
        "archive_records": len(rows) - len(recovered),
        "zone_evidence_records": len(recovered),
        "recovered_legacy_ids": recovered,
        "unknown_fields_not_inferred": ["elliott"],
    }


def load_existing_registry(path: Path) -> dict[tuple[str, str, str], dict[str, Any]]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    result = {}
    for record in payload.get("records", []):
        key = (
            str(record.get("legacy_id") or ""),
            str(record.get("opened_at") or ""),
            str(record.get("region_id") or ""),
        )
        if all(key[:2]):
            result[key] = dict(record)
    return result


def numeric_id(value: Any) -> int:
    text = str(value or "")
    suffix = text.rsplit("-", 1)[-1]
    return int(suffix) if text.startswith("PREOP-") and suffix.isdigit() else 0


def build_registry(
    backup_dir: Path,
    current_rows: list[dict[str, str]],
    existing_path: Path,
) -> list[dict[str, Any]]:
    existing = load_existing_registry(existing_path)
    aggregate: dict[tuple[str, str, str], dict[str, Any]] = {}

    for source, row in load_archive_rows(backup_dir):
        key = stable_key(row)
        if not key[0] or not key[1]:
            continue
        item = aggregate.setdefault(
            key,
            {"row": dict(row), "sources": set()},
        )
        item["sources"].add(source)

    for row in current_rows:
        key = stable_key(row)
        if not key[0] or not key[1]:
            continue
        item = aggregate.setdefault(key, {"row": dict(row), "sources": set()})
        item["row"] = dict(row)
        item["sources"].add("CURRENT")

    last_value = max(
        (numeric_id(record.get("canonical_id")) for record in existing.values()),
        default=0,
    )
    new_keys = sorted(
        (key for key in aggregate if key not in existing),
        key=lambda key: (
            parse_time(key[1]) or datetime.max,
            key[0],
            key[2],
        ),
    )
    for key in new_keys:
        last_value += 1
        existing[key] = {
            "canonical_id": f"PREOP-{last_value:06d}",
            "legacy_id": key[0],
            "opened_at": key[1],
            "region_id": key[2],
        }

    records = []
    for key, item in aggregate.items():
        row = item["row"]
        record = dict(existing[key])
        record.pop("record_hash", None)
        record.update(
            {
                "closed_at": str(row.get("data_fechamento") or ""),
                "symbol": str(row.get("ativo") or ""),
                "direction": str(row.get("direcao") or ""),
                "result": str(row.get("resultado") or ""),
                "sources": sorted(item["sources"]),
                "identity_version": IDENTITY_VERSION,
            }
        )
        record_hash_payload = json.dumps(
            record,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        record["record_hash"] = hashlib.sha256(record_hash_payload).hexdigest()
        records.append(record)

    return sorted(records, key=lambda item: numeric_id(item["canonical_id"]))


def registry_indexes(records: list[dict[str, Any]]):
    by_key = {}
    by_legacy: dict[str, list[dict[str, Any]]] = defaultdict(list)
    by_canonical = {}
    for record in records:
        key = (
            record["legacy_id"],
            record["opened_at"],
            record["region_id"],
        )
        by_key[key] = record
        by_legacy[record["legacy_id"]].append(record)
        by_canonical[record["canonical_id"]] = record
    return by_key, by_legacy, by_canonical


def reference_time(row: dict[str, Any]) -> datetime | None:
    for field in (
        "data",
        "data_abertura",
        "data_fechamento",
        "closed_at",
        "timestamp",
    ):
        parsed = parse_time(row.get(field))
        if parsed is not None:
            return parsed
    return None


def choose_record(
    legacy_id: str,
    timestamp: datetime | None,
    candidates_by_legacy: dict[str, list[dict[str, Any]]],
    *,
    candidates_by_canonical: dict[str, dict[str, Any]] | None = None,
    result: str = "",
) -> dict[str, Any] | None:
    reference_id = str(legacy_id or "").strip()
    candidates = list(candidates_by_legacy.get(reference_id, []))
    canonical_match = (
        (candidates_by_canonical or {}).get(reference_id)
    )
    if canonical_match is not None and all(
        candidate["canonical_id"] != canonical_match["canonical_id"]
        for candidate in candidates
    ):
        candidates.append(canonical_match)
    if not candidates:
        return None
    if len(candidates) == 1:
        return candidates[0]
    if timestamp is None:
        if canonical_match is not None:
            return canonical_match
        return candidates[-1]

    def score(record: dict[str, Any]):
        opened = parse_time(record.get("opened_at")) or datetime.min
        closed = parse_time(record.get("closed_at"))
        targets = [opened]
        if result and closed is not None:
            targets.append(closed)
        result_penalty = int(
            bool(
                result
                and record.get("result")
                and record.get("result") != result
            )
        )
        return (
            min(abs((timestamp - target).total_seconds()) for target in targets),
            result_penalty,
        )

    return min(candidates, key=score)


def reference_distance_seconds(
    record: dict[str, Any],
    timestamp: datetime | None,
    *,
    result: str = "",
) -> float | None:
    if timestamp is None:
        return None
    opened = parse_time(record.get("opened_at"))
    closed = parse_time(record.get("closed_at"))
    candidates = [value for value in (opened, closed if result else None) if value]
    if not candidates:
        return None
    return min(abs((timestamp - value).total_seconds()) for value in candidates)


def remap_csv_references(
    path: Path,
    candidates_by_legacy: dict[str, list[dict[str, Any]]],
    candidates_by_canonical: dict[str, dict[str, Any]],
    *,
    id_field: str,
) -> tuple[list[str], list[dict[str, str]], int, int]:
    fields, rows = read_csv(path)
    for field in (
        "legacy_pre_operation_id",
        "identity_version",
        "identity_resolution",
    ):
        if field not in fields:
            fields.append(field)
    changed = 0
    unresolved = 0
    for row in rows:
        legacy_id = str(row.get(id_field) or "").strip()
        if row.get("identity_resolution") == "LEGACY_UNRESOLVED_REFERENCE":
            unresolved += 1
            continue
        timestamp = reference_time(row)
        result = str(row.get("resultado") or "")
        record = choose_record(
            legacy_id,
            timestamp,
            candidates_by_legacy,
            candidates_by_canonical=candidates_by_canonical,
            result=result,
        )
        distance = (
            reference_distance_seconds(record, timestamp, result=result)
            if record
            else None
        )
        if timestamp is not None and (record is None or distance is None or distance > 900):
            fingerprint = hashlib.sha256(
                f"{path.name}|{legacy_id}|{timestamp.isoformat()}".encode("utf-8")
            ).hexdigest()[:16].upper()
            unresolved_id = f"LEGACY-UNRESOLVED-{fingerprint}"
            row["legacy_pre_operation_id"] = (
                row.get("legacy_pre_operation_id") or legacy_id
            )
            row[id_field] = unresolved_id
            row["identity_version"] = IDENTITY_VERSION
            row["identity_resolution"] = "LEGACY_UNRESOLVED_REFERENCE"
            changed += int(legacy_id != unresolved_id)
            unresolved += 1
            continue
        if record and legacy_id != record["canonical_id"]:
            row["legacy_pre_operation_id"] = (
                row.get("legacy_pre_operation_id") or legacy_id
            )
            row[id_field] = record["canonical_id"]
            changed += 1
        if record:
            row["identity_version"] = IDENTITY_VERSION
            row["identity_resolution"] = "CANONICAL_REFERENCE"
    return fields, rows, changed, unresolved


def session_for(opened_at: str) -> str:
    parsed = parse_time(opened_at)
    if parsed is None:
        return "NAO_PERSISTIDO"
    hour = parsed.hour
    if 4 <= hour < 9:
        return "LONDRES"
    if 9 <= hour < 13:
        return "OVERLAP_LONDRES_NY"
    if 13 <= hour < 19:
        return "NY"
    if 19 <= hour < 20:
        return "MANUTENCAO"
    return "ASIA"


def build_partial_context(row: dict[str, str]) -> dict[str, str]:
    return {
        "data": row.get("data_abertura", ""),
        "pre_operation_id": row.get("id", ""),
        "sessao": session_for(row.get("data_abertura", "")),
        "macro": "NAO_PERSISTIDO",
        "h4": "NAO_PERSISTIDO",
        "h1": "NAO_PERSISTIDO",
        "m15": "NAO_PERSISTIDO",
        "top_down_alinhamento": "NAO_PERSISTIDO",
        "tendencia": "NAO_PERSISTIDO",
        "momentum": "DESATIVADO",
        "direcao": row.get("direcao", ""),
        "smc": row.get("smc", ""),
        "elliott": row.get("elliott", ""),
        "bos": row.get("bos", ""),
        "choch": row.get("choch", ""),
        "confianca": row.get("confianca", ""),
        "brain_score": row.get("brain_score", ""),
        "metodo_risco": row.get("metodo_risco", ""),
        "risco_percentual_estimado": "",
        "rr": row.get("rr", ""),
        "status_setup": row.get("status_setup", ""),
        "resultado": row.get("resultado", ""),
        "licao": (
            "IDENTITY_MIGRATION_V2: contexto parcial reconstruido apenas "
            "da PRE_OPERATION persistida; campos ausentes nao foram inferidos."
        ),
        "legacy_pre_operation_id": row.get("legacy_id", ""),
        "identity_version": IDENTITY_VERSION,
        "identity_resolution": "CANONICAL_REFERENCE",
    }


def backup_files(paths: list[Path], backup_root: Path) -> Path:
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    target = backup_root / f"memory_identity_v2_{stamp}"
    target.mkdir(parents=True, exist_ok=False)
    for path in paths:
        if path.exists():
            shutil.copy2(path, target / path.name)
    return target


def migrate(root: Path, apply: bool) -> dict[str, Any]:
    data_dir = root / "data"
    backup_dir = root.parent / "backups"
    config_dir = root.parent / "config"
    preop_path = data_dir / PREOP_FILE
    registry_path = data_dir / REGISTRY_FILE
    report_path = data_dir / REPORT_FILE
    sequence_path = config_dir / SEQUENCE_FILE

    preop_fields, current_rows = read_csv(preop_path)
    recovery = None
    if not current_rows:
        preop_fields, current_rows, recovery = (
            recover_live_rows_from_persisted_evidence(data_dir, backup_dir)
        )

    records = build_registry(backup_dir, current_rows, registry_path)
    by_key, by_legacy, by_canonical = registry_indexes(records)
    region_to_canonical = {}
    migrated_preops = []
    for row in current_rows:
        legacy_id, opened_at, region_id = stable_key(row)
        record = by_key[(legacy_id, opened_at, region_id)]
        updated = dict(row)
        updated["legacy_id"] = legacy_id
        updated["id"] = record["canonical_id"]
        updated["identity_version"] = IDENTITY_VERSION
        if region_id:
            region_to_canonical[region_id] = record["canonical_id"]
        migrated_preops.append(updated)

    for row in current_rows:
        for field in row:
            if field not in preop_fields:
                preop_fields.append(field)
    for field in PREOP_IDENTITY_FIELDS:
        if field not in preop_fields:
            preop_fields.append(field)

    reference_specs = [
        (data_dir / "market_context_memory.csv", "pre_operation_id"),
        (data_dir / "mt5_order_memory.csv", "pre_operation_id"),
        (data_dir / "operation_decisions.csv", "pre_operation_id"),
    ]
    remapped_csvs = {}
    unresolved_csv_references = {}
    csv_payloads = {}
    for path, id_field in reference_specs:
        fields, rows, changed, unresolved = remap_csv_references(
            path,
            by_legacy,
            by_canonical,
            id_field=id_field,
        )
        remapped_csvs[path.name] = changed
        unresolved_csv_references[path.name] = unresolved
        csv_payloads[path] = (fields, rows)

    context_path = data_dir / "market_context_memory.csv"
    context_fields, context_rows = csv_payloads.get(context_path, ([], []))
    context_ids = {str(row.get("pre_operation_id") or "") for row in context_rows}
    partial_contexts = 0
    for row in migrated_preops:
        if row["id"] not in context_ids:
            context_rows.append(build_partial_context(row))
            context_ids.add(row["id"])
            partial_contexts += 1
    csv_payloads[context_path] = (context_fields, context_rows)

    zones_path = data_dir / "interest_zones.json"
    zones_changed = 0
    zones_payload = None
    if zones_path.exists():
        zones_payload = json.loads(zones_path.read_text(encoding="utf-8"))
        zone_rows = zones_payload if isinstance(zones_payload, list) else zones_payload.get("zones", [])
        for zone in zone_rows:
            if not isinstance(zone, dict):
                continue
            region_id = str(zone.get("region_id") or zone.get("zone_id") or "")
            canonical = region_to_canonical.get(region_id)
            if canonical and zone.get("pre_operation_id") != canonical:
                zone["pre_operation_id"] = canonical
                zones_changed += 1

    close_state_path = data_dir / "operation_close_alerts.json"
    close_state = []
    close_keys_added = 0
    if close_state_path.exists():
        loaded = json.loads(close_state_path.read_text(encoding="utf-8"))
        close_state = list(loaded if isinstance(loaded, list) else [])
        sent = set(close_state)
        for old, new in zip(current_rows, migrated_preops):
            result = str(new.get("resultado") or "")
            closed_at = str(new.get("data_fechamento") or "")
            canonical_key = f"{new.get('id')}:{result}:{closed_at or 'SEM_TIMESTAMP'}"
            if result and closed_at and canonical_key not in sent:
                sent.add(canonical_key)
                close_keys_added += 1
        close_state = sorted(sent)

    processed_path = data_dir / "mt5_closed_operations_processed.json"
    processed_payload = []
    processed_changed = 0
    if processed_path.exists():
        loaded = json.loads(processed_path.read_text(encoding="utf-8"))
        for item in loaded if isinstance(loaded, list) else []:
            parts = str(item).split(":", 2)
            if len(parts) == 3:
                record = choose_record(
                    parts[0],
                    parse_time(parts[2]),
                    by_legacy,
                    candidates_by_canonical=by_canonical,
                    result=parts[1],
                )
                if record:
                    replacement = f"{record['canonical_id']}:{parts[1]}:{parts[2]}"
                    processed_changed += int(replacement != item)
                    item = replacement
            processed_payload.append(item)

    sequence_value = max(numeric_id(record["canonical_id"]) for record in records)
    sequence_payload = {
        "identity_version": IDENTITY_VERSION,
        "last_value": sequence_value,
        "last_id": f"PREOP-{sequence_value:06d}",
        "updated_at": datetime.now().isoformat(timespec="seconds"),
        "migration": "CAUSAL_MEMORY_IDENTITY_RECONCILIATION",
    }
    registry_payload = {
        "identity_version": IDENTITY_VERSION,
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "records_total": len(records),
        "records": records,
    }

    affected_paths = [
        preop_path,
        registry_path,
        report_path,
        sequence_path,
        zones_path,
        close_state_path,
        processed_path,
        *(path for path, _ in reference_specs),
    ]
    before_hashes = {str(path): sha256(path) for path in affected_paths}
    report = {
        "status": "DRY_RUN" if not apply else "APPLIED",
        "identity_version": IDENTITY_VERSION,
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "historical_records_registered": len(records),
        "live_pre_operations_migrated": len(migrated_preops),
        "first_live_canonical_id": migrated_preops[0]["id"],
        "last_live_canonical_id": migrated_preops[-1]["id"],
        "sequence_last_value": sequence_value,
        "csv_references_remapped": remapped_csvs,
        "unresolved_csv_references": unresolved_csv_references,
        "partial_contexts_reconstructed": partial_contexts,
        "zones_associated": zones_changed,
        "close_alert_keys_added": close_keys_added,
        "closed_processed_remapped": processed_changed,
        "before_hashes": before_hashes,
        "orders_sent": 0,
        "live_memory_recovery": recovery,
    }

    if not apply:
        return report

    backup_target = backup_files(affected_paths, backup_dir)
    write_csv(preop_path, preop_fields, migrated_preops)
    for path, (fields, rows) in csv_payloads.items():
        if fields:
            write_csv(path, fields, rows)
    if zones_payload is not None:
        write_json(zones_path, zones_payload)
    if close_state_path.exists():
        write_json(close_state_path, close_state)
    if processed_path.exists():
        write_json(processed_path, processed_payload)
    write_json(registry_path, registry_payload)
    write_json(sequence_path, sequence_payload)

    report["backup_dir"] = str(backup_target)
    report["after_hashes"] = {str(path): sha256(path) for path in affected_paths}
    write_json(report_path, report)
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    report = migrate(args.root.resolve(), args.apply)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
