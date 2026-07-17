from datetime import datetime, timezone
from pathlib import Path

from src.backtest.leon_strategy_replayer import (
    _contextual_market_decision,
    _entry_remains_in_zone,
    _zone_context,
)
from src.backtest.statistical_report import TRADE_FIELDS
from src.interest_zone_engine import build_zone_from_context, monitor_zone


ROOT = Path(__file__).resolve().parents[1]


def _decision(**changes):
    values = {
        "direction": "COMPRA",
        "bos": "BOS_BULLISH",
        "choch": "CHOCH_BULLISH",
        "has_fvg": True,
        "has_order_block": False,
        "liquidity_sweep": True,
        "fibonacci_setup": {"valid": False},
        "elliott": {"valid": False},
        "weekly": "BAIXA",
        "daily": "ALTA",
        "h4": "ALTA",
        "h1": "ALTA",
        "m15": "ALTA",
    }
    values.update(changes)
    return _contextual_market_decision(**values)


def test_contextual_decision_does_not_require_elliott_or_fibonacci():
    result = _decision()
    assert result["decision"] == "PRE_TRADE_VALID"
    assert result["operational_state"] == "CONTEXTO_CONFLUENTE"
    assert "FIBONACCI_ALIGNED" in result["conditions_missing"]
    assert "ELLIOTT_SCENARIO" in result["conditions_missing"]


def test_contextual_decision_waits_for_liquidity_and_confirmation():
    waiting_liquidity = _decision(liquidity_sweep=False)
    assert waiting_liquidity["operational_state"] == "AGUARDANDO_LIQUIDEZ"

    waiting_confirmation = _decision(m15="BAIXA")
    assert waiting_confirmation["operational_state"] == "AGUARDANDO_CONFIRMACAO"


def test_explicit_h4_h1_contradiction_invalidates_context():
    result = _decision(h4="BAIXA", h1="BAIXA")
    assert result["decision"] == "NAO_OPERAR"
    assert result["operational_state"] == "INVALIDADO"
    assert "H4_H1_CONTRADICT_DIRECTION" in result["conditions_contradictory"]


def test_context_builds_canonical_zone_and_requires_full_confirmation():
    timestamp = datetime(2026, 1, 1, 12, tzinfo=timezone.utc)
    identity = {
        "cycle_id": "BT-CYCLE-1",
        "analysis_id": "BT-ANALYSIS-1",
        "pre_operation_id": "",
        "symbol": "XAUUSD",
        "timeframe": "M15",
        "candle_timestamp": timestamp.isoformat(),
    }
    context = _zone_context(
        identity=identity,
        direction_en="BULLISH",
        weekly="ALTA",
        daily="ALTA",
        h4="ALTA",
        h1="ALTA",
        fvg={"type": "FVG_BULLISH", "start": 4000, "end": 4010, "mitigated": False},
        order_block=None,
        liquidity={"type": "SWEEP_SELL_SIDE", "direction": "BULLISH"},
        bos="BOS_BULLISH",
        choch="CHOCH_BULLISH",
        elliott={"valid": False, "label": "SEM_CONTAGEM"},
    )
    zone = build_zone_from_context(identity, context, current_price=4005)
    assert zone["region_id"].startswith("REG-")
    assert zone["region_status"] == "ATIVA"

    zone = monitor_zone(
        zone,
        current_price=4005,
        evidence={
            "liquidity_present": True,
            "liquidity_swept": True,
            "choch_present": True,
            "trigger_confirmed": True,
        },
        now=timestamp,
    )
    assert zone["region_status"] == "CONFIRMADA"


def test_backtest_contract_has_contextual_identity_and_legacy_markers():
    required = {
        "region_id",
        "pre_operation_id",
        "region_status",
        "operational_state",
        "decision",
        "primary_reason",
        "conditions_present",
        "score_legacy_only",
        "momentum_legacy_only",
    }
    assert required.issubset(TRADE_FIELDS)


def test_replayer_has_no_numeric_release_gate_or_execution_surface():
    source = (ROOT / "src" / "backtest" / "leon_strategy_replayer.py").read_text(encoding="utf-8")
    assert 'interpretation["score"] <' not in source
    assert "brain_score < self.min_brain_score" not in source
    assert "tactical_votes >=" not in source
    assert "order_send(" not in source
    assert "MetaTrader5" not in source
    assert "enviar_mensagem" not in source
    assert "contextual_state_statistics" in source
    assert "STOP_TOO_TIGHT_FOR_ATR" not in source
    assert "STOP_TOO_WIDE_FOR_ATR" not in source
    assert "min_stop_atr" not in source
    assert "max_stop_atr" not in source


def test_next_candle_entry_must_remain_inside_confirmed_zone():
    zone = {"region_low": 4000.0, "region_high": 4010.0}

    assert _entry_remains_in_zone(zone, 4005.0) is True
    assert _entry_remains_in_zone(zone, 4010.01) is False
    assert _entry_remains_in_zone(zone, None) is False


def test_replayer_treats_mixed_top_down_as_context_observation():
    source = (ROOT / "src" / "backtest" / "leon_strategy_replayer.py").read_text(encoding="utf-8")

    assert 'if not timeframe_policy["approved"]:' in source
    assert '"TOP_DOWN_CONTEXT_MIXED"' in source
    assert '"TOP_DOWN_CONTEXT_NOT_APPROVED"' not in source
    assert '"ENTRY_LEFT_OPERATIONAL_ZONE"' in source


def test_live_orchestrator_does_not_reintroduce_study_unanimity():
    source = (ROOT / "src" / "leon.py").read_text(encoding="utf-8")

    assert 'and study_validation["approved"]' not in source
    assert 'ENTRADA BLOQUEADA:' in source


def test_executor_treats_m5_as_optional_refinement():
    source = (ROOT / "src" / "mt5_order_executor.py").read_text(encoding="utf-8")

    m5_block = 'return _bloqueio(\n                "M5_CONFIRMATION_REQUIRED"'
    assert m5_block not in source
    assert "M5 e refinamento opcional" in source
