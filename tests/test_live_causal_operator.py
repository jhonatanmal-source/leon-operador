from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

from src.interest_zone_engine import monitor_touched_zone
from src.live_causal_confirmation import (
    classify_live_zone_causality,
    live_causal_snapshot,
    progress_live_confirmations,
)


T0 = datetime(2026, 7, 16, 10, 0, tzinfo=timezone.utc)


def _zone(**changes):
    zone = {
        "region_id": "REG-LIVE-1",
        "zone_id": "REG-LIVE-1",
        "symbol": "GOLD_SPOT",
        "created_at": T0.isoformat(),
        "source_candle_timestamp": (T0 - timedelta(hours=1)).isoformat(),
        "source_timeframe": "H1",
        "source_event_id": "SRC-1",
        "source_structure_id": "STR-1",
        "source_zone_type": "DEMAND_ZONE",
        "source_lower_price": 4000.0,
        "source_upper_price": 4010.0,
        "region_low": 4000.0,
        "region_high": 4010.0,
        "region_direction": "BULLISH",
        "region_status": "TOCADA",
        "region_valid": True,
        "created_before_touch": True,
        "touch_timestamp": (T0 + timedelta(minutes=15)).isoformat(),
        "invalidation_price": 3998.0,
        "target_prices": [4020.0, 4040.0],
        "current_price": 4005.0,
        "confirmation_history": [],
        "structural_confirmations": [],
        "event_history": [],
    }
    zone.update(changes)
    return zone


def _raw():
    stamp = T0 + timedelta(minutes=30)
    return [{
        "event_id": "EVT-LIVE-CHOCH-1",
        "confirmation_id": "EVT-LIVE-CHOCH-1",
        "confirmation_type": "CHOCH",
        "direction": "BULLISH",
        "timeframe": "M15",
        "timestamp": stamp.isoformat(),
        "structure_price": 4008.0,
        "source_module": "test",
    }]


def _candle(at, open_price, high, low, close):
    return {"time": at.isoformat(), "open": open_price, "high": high, "low": low, "close": close}


def test_live_event_is_not_promoted_without_full_timeline():
    result = progress_live_confirmations(
        zone=_zone(), raw_events=_raw(),
        closed_candle=_candle(T0 + timedelta(minutes=30), 4005, 4009, 4002, 4008),
    )
    assert result["complete_confirmations"] == []
    assert result["structural_confirmations"][0]["confirmation_state"] == "WAITING_FOR_RETEST"


def test_same_closed_candle_advances_at_most_one_stage():
    zone = _zone()
    first = progress_live_confirmations(zone=zone, raw_events=_raw(), closed_candle={})
    zone["structural_confirmations"] = first["structural_confirmations"]
    candle = _candle(T0 + timedelta(minutes=45), 4004, 4009, 4002, 4007)
    second = progress_live_confirmations(zone=zone, raw_events=[], closed_candle=candle)
    zone["structural_confirmations"] = second["structural_confirmations"]
    repeated = progress_live_confirmations(zone=zone, raw_events=[], closed_candle=candle)
    assert second["structural_confirmations"][0]["retest_at"]
    assert repeated["structural_confirmations"][0]["defense_at"] is None


def test_closed_candles_build_complete_causal_confirmation():
    zone = _zone()
    state = progress_live_confirmations(zone=zone, raw_events=_raw(), closed_candle={})
    for candle in (
        _candle(T0 + timedelta(minutes=45), 4005, 4009, 4002, 4006),
        _candle(T0 + timedelta(minutes=60), 4004, 4008, 4001, 4007),
        _candle(T0 + timedelta(minutes=75), 4007, 4013, 4006, 4012),
    ):
        zone["structural_confirmations"] = state["structural_confirmations"]
        state = progress_live_confirmations(zone=zone, raw_events=[], closed_candle=candle)
    confirmation = state["complete_confirmations"][0]
    assert confirmation["confirmation_state"] == "COMPLETE"
    assert confirmation["timeline_state"] == "OBSERVABLE"
    assert all(confirmation[field] for field in (
        "structure_event_at", "retest_at", "defense_at",
        "continuation_at", "confirmation_completed_at",
    ))


def test_complete_causal_confirmation_opens_window_at_completion_only():
    zone = _zone()
    state = live_causal_snapshot(zone=zone, raw_events=_raw(), closed_candle={})
    for candle in (
        _candle(T0 + timedelta(minutes=45), 4005, 4009, 4002, 4006),
        _candle(T0 + timedelta(minutes=60), 4004, 4008, 4001, 4007),
        _candle(T0 + timedelta(minutes=75), 4007, 4013, 4006, 4012),
    ):
        zone["structural_confirmations"] = state["structural_confirmations"]
        state = live_causal_snapshot(zone=zone, raw_events=[], closed_candle=candle)
    assert state["causality_state"] == "CAUSAL"
    monitored = monitor_touched_zone(
        zone=zone,
        market_snapshot={
            "timestamp": T0 + timedelta(minutes=75),
            "candle": _candle(T0 + timedelta(minutes=75), 4007, 4013, 4006, 4012),
            "events_detected": state["complete_confirmations"],
            "structural_confirmations": state["structural_confirmations"],
            "context_valid": True,
            "contract_mode": "OFFICIAL_CAUSAL",
        },
    )
    assert monitored["entry_window_open_at"] == monitored["confirmation_completed_at"]
    assert not monitored.get("first_post_confirmation_observation_at")


def test_missing_zone_timeline_is_unknown_and_blocking():
    state, reason = classify_live_zone_causality(_zone(touch_timestamp=""), {})
    assert state == "UNKNOWN_CAUSALITY"
    assert reason == "CAUSAL_EVIDENCE_INCOMPLETE"


def test_positive_noncausal_evidence_is_not_unknown():
    confirmation = {
        "direction": "BULLISH",
        "structure_event_at": (T0 + timedelta(minutes=30)).isoformat(),
        "confirmation_completed_at": (T0 + timedelta(minutes=75)).isoformat(),
    }
    state, reason = classify_live_zone_causality(
        _zone(created_at=(T0 + timedelta(minutes=20)).isoformat()), confirmation
    )
    assert (state, reason) == ("NON_CAUSAL", "ZONE_CREATED_AFTER_TOUCH")


def test_live_entrypoint_no_longer_selects_legacy_contract():
    source = Path("src/leon.py").read_text(encoding="utf-8")
    assert 'contract_mode="LEGACY_PRODUCTION"' not in source
    assert "from institutional_analysis_engine import" in source


def test_live_causal_adapter_has_no_mt5_or_execution_surface():
    source = Path("src/live_causal_confirmation.py").read_text(encoding="utf-8")
    assert "MetaTrader5" not in source
    assert "order_send(" not in source
    assert "order_check(" not in source
