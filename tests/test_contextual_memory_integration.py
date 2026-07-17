from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import sys

import pytest


ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR / "src"))

from contextual_memory import (
    ContextualMemoryRecord,
    ContextualMemoryStore,
    approved_lessons,
    legacy_record,
    record_cycle_memory,
)
from integrated_studies import (
    IntegratedStudyCoordinator,
    StudyIdentity,
    StudyOutput,
    adapt_elliott_fibonacci_study,
    adapt_smc_study,
    adapt_top_down_study,
    consolidate_studies,
)
from operational_study_engine import (
    validate_setup_a_plus,
    validate_study_operational_entry,
)


@pytest.fixture
def identity():
    return StudyIdentity(
        cycle_id="CYCLE-1",
        analysis_id="ANALYSIS-1",
        pre_operation_id="PREOP-1",
        symbol="XAUUSD",
        timeframe="M15",
        candle_timestamp="2026-07-12T19:45:00+00:00",
    )


def test_memory_types_are_separate_and_keep_same_identity(tmp_path):
    store = ContextualMemoryStore(tmp_path / "memory.jsonl")
    saved = record_cycle_memory(
        store,
        identity={
            "cycle_id": "CYCLE-1",
            "analysis_id": "ANALYSIS-1",
            "pre_operation_id": "PREOP-1",
            "symbol": "XAUUSD",
            "timeframe": "M15",
        },
        observation={"current_price": 4100.0},
        context={"market_phase": "CORRECAO"},
        decision={"decision": "AGUARDAR"},
        result={"executed": False},
    )
    assert [item["record_type"] for item in saved] == [
        "OBSERVATION", "CONTEXT", "DECISION", "RESULT"
    ]
    assert {item["pre_operation_id"] for item in saved} == {"PREOP-1"}
    assert {item["cycle_id"] for item in saved} == {"CYCLE-1"}


def test_memory_is_always_reference_only(tmp_path):
    store = ContextualMemoryStore(tmp_path / "memory.jsonl")
    item = store.append(ContextualMemoryRecord(record_type="CONTEXT", symbol="XAUUSD"))
    assert item["reference_only"] is True
    assert item["can_authorize_operation"] is False


def test_legacy_adapter_marks_incomplete_informational_record():
    item = legacy_record(
        "trade_memory.csv",
        {"data": "2026-06-01", "ativo": "XAUUSD", "score": "100"},
    )
    assert item["legacy_record"] is True
    assert item["quality"] == "INFORMATIONAL"
    assert item["context"]["data_incomplete"] is True
    assert item["can_authorize_operation"] is False


def test_query_filters_symbol_timeframe_and_pre_operation(tmp_path):
    store = ContextualMemoryStore(tmp_path / "memory.jsonl")
    store.append(ContextualMemoryRecord(record_type="DECISION", symbol="XAUUSD", timeframe="M15", pre_operation_id="P1"))
    store.append(ContextualMemoryRecord(record_type="DECISION", symbol="EURUSD", timeframe="M5", pre_operation_id="P2"))
    found = store.query(symbol="XAUUSD", timeframe="M15", pre_operation_id="P1")
    assert len(found) == 1
    assert found[0]["current_context_required"] is True


def test_old_memory_is_excluded_by_age(tmp_path):
    store = ContextualMemoryStore(tmp_path / "memory.jsonl")
    old = (datetime.now(timezone.utc) - timedelta(days=60)).isoformat()
    store.append(ContextualMemoryRecord(record_type="CONTEXT", symbol="XAUUSD", timestamp=old))
    assert store.query(symbol="XAUUSD", max_age_days=7) == []


def test_openrouter_lesson_requires_human_review(tmp_path):
    store = ContextualMemoryStore(tmp_path / "memory.jsonl")
    item = store.append(
        ContextualMemoryRecord(
            record_type="LESSON",
            lesson={
                "status": "APPROVED",
                "created_by": "OPENROUTER",
                "evidence": "relatorio tecnico",
            },
        )
    )
    assert item["lesson"]["status"] == "REVIEW_REQUIRED"
    assert item["lesson"]["approved_for_reference"] is False
    assert store.query(record_type="LESSON") == []


def test_approved_lesson_requires_evidence():
    with pytest.raises(ValueError, match="evidencia"):
        ContextualMemoryRecord(
            record_type="LESSON",
            lesson={"status": "APPROVED", "created_by": "HUMAN"},
        ).normalize()


def test_rejected_lesson_is_not_returned_by_default(tmp_path):
    store = ContextualMemoryStore(tmp_path / "memory.jsonl")
    store.append(ContextualMemoryRecord(record_type="LESSON", lesson={"status": "REJECTED"}))
    assert store.query(record_type="LESSON") == []


def test_approved_lesson_is_reference_only(tmp_path):
    store = ContextualMemoryStore(tmp_path / "memory.jsonl")
    saved = store.append(
        ContextualMemoryRecord(
            record_type="LESSON",
            lesson={"status": "APPROVED", "evidence": "PREOP-1 revisada", "created_by": "HUMAN"},
        )
    )
    found = approved_lessons(store.records())
    assert found[0]["record_id"] == saved["record_id"]
    assert found[0]["can_authorize_operation"] is False


def test_atomic_write_preserves_previous_file_when_replace_fails(tmp_path, monkeypatch):
    path = tmp_path / "memory.jsonl"
    store = ContextualMemoryStore(path)
    first = store.append(ContextualMemoryRecord(record_type="OBSERVATION", symbol="XAUUSD"))
    original = path.read_text(encoding="utf-8")

    def fail_replace(*_args):
        raise OSError("replace failed")

    monkeypatch.setattr("contextual_memory.os.replace", fail_replace)
    with pytest.raises(OSError):
        store.append(ContextualMemoryRecord(record_type="CONTEXT", symbol="XAUUSD"))
    assert path.read_text(encoding="utf-8") == original
    assert json.loads(original)["record_id"] == first["record_id"]


def test_smc_adapter_produces_structured_region(identity):
    output = adapt_smc_study(
        identity,
        {
            "direction": "COMPRA",
            "smc": "ALTA",
            "bos": "BULLISH_BOS",
            "choch": "SEM_CHOCH",
            "fvg": "BULLISH_FVG",
            "fvg_zone": {"start": 4090, "end": 4095},
            "liquidity": {"type": "SELL_SIDE_SWEEP", "direction": "COMPRA", "swept": True},
        },
    )
    assert output["status"] == "REGION_DETECTED"
    assert output["findings"]["region_detected"] is True
    assert output["findings"]["liquidity_swept"] is True


def test_elliott_and_fibonacci_adapter_is_hypothesis(identity):
    output = adapt_elliott_fibonacci_study(
        identity,
        {
            "label": "ABC_CORRECTION",
            "phase": "CORRECAO",
            "valid": True,
            "fibonacci_setup": {"valid": True, "retracement": "0.618"},
        },
    )
    assert output["status"] == "SCENARIO_POSSIBLE"
    assert output["findings"]["scenario_present"] is True
    assert output["findings"]["fib_confluence"] is True


def test_top_down_missing_data_has_explicit_state(identity):
    output = adapt_top_down_study(identity, None)
    assert output["status"] == "WAITING_DATA"
    assert output["next_required_event"] == "CONSOLIDAR_CONTEXTO"


def test_text_only_study_is_rejected_without_crashing_cycle(identity):
    coordinator = IntegratedStudyCoordinator({"smc": lambda _snapshot: "texto solto"})
    output = coordinator.run(identity, {"candles": [1, 2, 3]})["smc"]
    assert output["status"] == "STUDY_FAILED"
    assert "estruturada" in output["error"]


def test_disconnected_study_does_not_crash_other_studies(identity):
    coordinator = IntegratedStudyCoordinator(
        {
            "broken": lambda _snapshot: (_ for _ in ()).throw(RuntimeError("offline")),
            "healthy": lambda _snapshot: {"status": "COMPLETED", "findings": {"ok": True}},
        }
    )
    outputs = coordinator.run(identity, {"snapshot_id": "S1"})
    assert outputs["broken"]["status"] == "STUDY_FAILED"
    assert outputs["healthy"]["findings"]["ok"] is True


def test_all_studies_receive_same_snapshot_object(identity):
    seen = []

    def study(snapshot):
        seen.append(id(snapshot))
        return {"status": "COMPLETED", "findings": {"snapshot_id": snapshot["snapshot_id"]}}

    outputs = IntegratedStudyCoordinator({"a": study, "b": study}).run(identity, {"snapshot_id": "S1"})
    assert seen[0] == seen[1]
    assert outputs["a"]["findings"]["snapshot_id"] == "S1"


def test_all_agents_keep_same_cycle_and_analysis(identity):
    output = IntegratedStudyCoordinator(
        {"smc": lambda _snapshot: {"status": "COMPLETED", "findings": {}}}
    ).run(identity, {})["smc"]
    assert output["cycle_id"] == "CYCLE-1"
    assert output["analysis_id"] == "ANALYSIS-1"
    assert output["pre_operation_id"] == "PREOP-1"


def test_study_output_requires_structured_findings(identity):
    with pytest.raises(TypeError):
        StudyOutput(
            study_name="SMC",
            cycle_id=identity.cycle_id,
            analysis_id=identity.analysis_id,
            symbol=identity.symbol,
            timeframe="M15",
            timestamp="now",
            status="OK",
            findings="texto",
        ).as_dict()


def test_consolidation_rejects_mixed_cycles(identity):
    top = adapt_top_down_study(identity, {})
    smc = adapt_smc_study(identity, {})
    elliott = adapt_elliott_fibonacci_study(identity, {})
    smc["cycle_id"] = "OTHER"
    with pytest.raises(ValueError, match="outro ciclo"):
        consolidate_studies(identity, snapshot={}, top_down=top, smc=smc, elliott_fibonacci=elliott)


def test_confluence_is_textual_boolean_and_never_authorizes(identity):
    top = adapt_top_down_study(identity, {"m15_gatilho": None})
    smc = adapt_smc_study(identity, {"direction": "COMPRA", "liquidity": {"type": "SEM_EVENTO"}})
    elliott = adapt_elliott_fibonacci_study(identity, {"label": "SEM_CONTAGEM"})
    result = consolidate_studies(
        identity,
        snapshot={"snapshot_id": "S1"},
        top_down=top,
        smc=smc,
        elliott_fibonacci=elliott,
    )
    assert result["historical_memory_can_authorize"] is False
    assert result["score_legacy_only"] is True
    assert result["momentum_legacy_only"] is True
    assert "score" not in result
    assert "confidence" not in result


def test_low_legacy_poi_score_does_not_block_complete_context():
    result = validate_study_operational_entry(
        {
            "direction": "COMPRA",
            "smc": "BULLISH",
            "bos": "BOS_BULLISH",
            "choch": "CHOCH_BULLISH",
            "fvg": "FVG_BULLISH",
            "liquidity_event": "SWEEP_SELL_SIDE",
            "liquidity_direction": "BULLISH",
            "poi_score": 1,
            "top_down_confirmed": True,
            "elliott_valid": False,
            "elliott_direction": "",
            "rr": 2,
            "high_impact_news": False,
        }
    )
    assert result["approved"] is True
    assert result["score_legacy_only"] is True


def test_high_legacy_poi_score_does_not_release_incomplete_context():
    result = validate_study_operational_entry(
        {
            "direction": "COMPRA",
            "smc": "NEUTRO",
            "bos": "SEM_BOS",
            "choch": "SEM_CHOCH",
            "fvg": "SEM_FVG_CONFIRMADO",
            "liquidity_event": "SEM_EVENTO",
            "poi_score": 100,
            "top_down_confirmed": False,
            "rr": 2,
            "high_impact_news": False,
        }
    )
    assert result["approved"] is False
    assert result["hard_blocks"] == []
    assert "smc_confirmado" in result["context_observations"]
    assert result["minimum_context_present"] is False


def test_momentum_does_not_block_complete_a_plus_context():
    result = validate_setup_a_plus(
        {
            "direction": "VENDA",
            "trend": "BAIXA",
            "momentum": "ALTA",
            "liquidity_event": "SWEEP_CONFIRMADO",
            "bos": "BOS_BEARISH",
            "choch": "CHOCH_BEARISH",
            "fvg": "FVG_BEARISH",
            "poi_score": 0,
            "top_down": "ALINHADO",
            "session": "LONDRES",
            "rr": 3,
            "high_impact_news": False,
            "market_state": "TENDENCIA",
        }
    )
    assert result["approved"] is True


def test_live_analysis_wires_contextual_memory_without_score_threshold():
    source = (ROOT_DIR / "src" / "leon.py").read_text(encoding="utf-8")
    study_source = (ROOT_DIR / "src" / "operational_study_engine.py").read_text(encoding="utf-8")
    institutional_source = (ROOT_DIR / "src" / "institutional_analysis_engine.py").read_text(encoding="utf-8")
    assert "salvar_memoria_trade(" in source
    assert "score_threshold_atual" not in source
    assert "poi_score >= 70" not in study_source
    assert 'poi_score >= 70' not in institutional_source


def test_operator_records_blocked_decision_and_non_executed_result(tmp_path, monkeypatch):
    import leon_operator

    store = ContextualMemoryStore(tmp_path / "operator-memory.jsonl")
    monkeypatch.setattr(leon_operator, "CONTEXTUAL_MEMORY", store)
    monkeypatch.setattr(leon_operator, "_CONTEXTUAL_MEMORY_EVENTS", set())
    monkeypatch.setattr(leon_operator, "registrar_log", lambda *_args, **_kwargs: True)
    monkeypatch.setenv("LEON_CYCLE_ID", "CYCLE-TEST")
    monkeypatch.setenv("LEON_ANALYSIS_ID", "ANALYSIS-TEST")
    monkeypatch.setenv("LEON_SYMBOL", "XAUUSD")

    decision = leon_operator._registrar_decisao_contextual_execucao(
        {
            "pre_operation_id": "PREOP-TEST",
            "ok": False,
            "error": "RISK_CONTROL_BLOCKED",
            "operational_state": "PRE_TRADE_VALID",
        }
    )
    result = leon_operator._registrar_resultado_contextual(
        {
            "pre_operation_id": "PREOP-TEST",
            "resultado": "INVALIDADO",
            "motivo": "Regiao perdida",
        },
        executed=False,
    )

    assert decision["ok"] is True
    assert result["ok"] is True
    records = store.records()
    assert [item["record_type"] for item in records] == ["DECISION", "RESULT", "LESSON"]
    assert records[1]["result"]["executed"] is False
    assert records[2]["lesson"]["status"] == "CANDIDATE"
    assert records[2]["can_authorize_operation"] is False
