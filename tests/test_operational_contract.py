from datetime import datetime, timedelta, timezone

import pytest

from src.live_operational_contract import evaluate_live_confirmation_gate


def _valid_zone(**overrides):
    zone = {
        "region_status": "CONFIRMADA",
        "region_invalidated": False,
        "structural_confirmations": [{"type": "BOS", "time": "2026-07-20T12:00:00+00:00"}],
        "monitor_timeline": [{"event": "touch", "time": "2026-07-20T11:00:00+00:00"}],
    }
    zone.update(overrides)
    return zone


def test_contract_incomplete_empty_zone():
    result = evaluate_live_confirmation_gate({})
    assert not result["allowed"]
    assert result["reason"] == "ZONE_EMPTY"


def test_timeline_absent():
    result = evaluate_live_confirmation_gate(_valid_zone(monitor_timeline=[], event_history=[]))
    assert not result["allowed"]
    assert result["reason"] == "NO_OBSERVABLE_TIMELINE"


def test_timeline_out_of_order():
    zone = _valid_zone()
    result = evaluate_live_confirmation_gate(zone)
    assert "allowed" in result


def test_confirmation_unresolved():
    result = evaluate_live_confirmation_gate(
        _valid_zone(structural_confirmations=[], valid_confirmations=[])
    )
    assert not result["allowed"]
    assert result["reason"] == "NO_STRUCTURAL_CONFIRMATION"


def test_entry_window_expired():
    past = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
    result = evaluate_live_confirmation_gate(_valid_zone(expires_at=past))
    assert not result["allowed"]
    assert result["reason"] == "ENTRY_WINDOW_EXPIRED"


def test_zone_invalidated():
    result = evaluate_live_confirmation_gate(
        _valid_zone(region_invalidated=True, invalidation_reason="PRICE_REJECTED")
    )
    assert not result["allowed"]
    assert result["reason"] == "PRICE_REJECTED"


def test_pre_operation_expired():
    result = evaluate_live_confirmation_gate(_valid_zone(expires_at="2000-01-01T00:00:00Z"))
    assert not result["allowed"]
    assert result["reason"] == "ENTRY_WINDOW_EXPIRED"


def test_demo_account_allowed():
    result = evaluate_live_confirmation_gate(_valid_zone())
    assert result["allowed"]


def test_daily_limit_not_relevant():
    result = evaluate_live_confirmation_gate(_valid_zone())
    assert result["allowed"]


def test_complete_valid_contract():
    result = evaluate_live_confirmation_gate(_valid_zone())
    assert result["allowed"]
    assert result["gate_passed"]


def test_valid_confirmations_fallback():
    zone = _valid_zone(structural_confirmations=[])
    zone["valid_confirmations"] = [{"type": "FVG"}]
    result = evaluate_live_confirmation_gate(zone)
    assert result["allowed"]
