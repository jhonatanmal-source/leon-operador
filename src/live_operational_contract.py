from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


def _as_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value or "").strip().upper() in {"1", "TRUE", "SIM", "YES", "OK"}


def evaluate_live_confirmation_gate(zone: dict[str, Any]) -> dict[str, Any]:
    if not zone:
        return {"allowed": False, "gate_passed": False, "reason": "ZONE_EMPTY"}

    expires_at = str(zone.get("expires_at") or "").strip()
    if expires_at:
        try:
            parsed = datetime.fromisoformat(expires_at)
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)
            if datetime.now(timezone.utc) > parsed:
                return {
                    "allowed": False,
                    "gate_passed": False,
                    "reason": "ENTRY_WINDOW_EXPIRED",
                }
        except (ValueError, TypeError):
            pass

    if _as_bool(zone.get("region_invalidated")):
        return {
            "allowed": False,
            "gate_passed": False,
            "reason": zone.get("invalidation_reason") or "REGION_INVALIDATED",
        }

    confirmations: list[Any] = zone.get("structural_confirmations") or []
    if not confirmations:
        confirmations = zone.get("valid_confirmations") or []

    if not confirmations:
        return {
            "allowed": False,
            "gate_passed": False,
            "reason": "NO_STRUCTURAL_CONFIRMATION",
        }

    monitor_timeline: list[Any] = zone.get("monitor_timeline") or []
    event_history: list[Any] = zone.get("event_history") or []
    if not monitor_timeline and not event_history:
        return {
            "allowed": False,
            "gate_passed": False,
            "reason": "NO_OBSERVABLE_TIMELINE",
        }

    if zone.get("region_status") not in {"CONFIRMADA"}:
        return {
            "allowed": False,
            "gate_passed": False,
            "reason": f"REGION_STATUS_{zone.get('region_status', 'UNKNOWN')}",
        }

    return {"allowed": True, "gate_passed": True, "reason": "GATE_PASSED"}
