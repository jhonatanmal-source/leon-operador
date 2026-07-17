from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


def _source(name):
    return (SRC / name).read_text(encoding="utf-8")


def test_cycle_id_is_created_once_for_operator_cycle(monkeypatch):
    import leon_operator

    monkeypatch.delenv("LEON_CYCLE_ID", raising=False)
    monkeypatch.delenv("LEON_ANALYSIS_ID", raising=False)
    identity = leon_operator._iniciar_identidade_ciclo(nova_analise=True)
    assert identity["cycle_id"].startswith("CYCLE-")
    assert identity["analysis_id"].startswith("ANALYSIS-")


def test_analysis_id_is_propagated_to_subprocess_environment():
    source = _source("leon_operator.py")
    assert "ambiente = os.environ.copy()" in source
    assert 'os.environ["LEON_ANALYSIS_ID"]' in source


def test_canonical_agent_log_contains_all_identifiers(tmp_path, monkeypatch):
    import log_engine

    monkeypatch.setattr(log_engine, "LOG_PATHS", [tmp_path / "agent.log"])
    monkeypatch.setattr(log_engine, "AGENT_HEALTH_FILE", tmp_path / "health.json")
    result = log_engine.registrar_evento_agente(
        "SMC",
        cycle_id="CYCLE-1",
        analysis_id="ANALYSIS-1",
        pre_operation_id="PREOP-1",
        symbol="XAUUSD",
        decision="ANALYZED",
    )
    line = (tmp_path / "agent.log").read_text(encoding="utf-8")
    assert result["ok"] is True
    assert "cycle_id=CYCLE-1" in line
    assert "analysis_id=ANALYSIS-1" in line
    assert "pre_operation_id=PREOP-1" in line
    assert "symbol=XAUUSD" in line


def test_agent_health_records_error_or_blocked(tmp_path, monkeypatch):
    import log_engine

    monkeypatch.setattr(log_engine, "LOG_PATHS", [tmp_path / "agent.log"])
    monkeypatch.setattr(log_engine, "AGENT_HEALTH_FILE", tmp_path / "health.json")
    log_engine.registrar_evento_agente("CONTEXT", error="NO_DATA", state="ERROR")
    health = log_engine.obter_saude_agentes()["agents"]["CONTEXT"]
    assert health["state"] == "ERROR"
    assert health["error_count"] == 1
    assert health["last_error"] == "NO_DATA"


def test_identical_agent_events_are_rate_limited(tmp_path, monkeypatch):
    import log_engine

    monkeypatch.setattr(log_engine, "LOG_PATHS", [tmp_path / "agent.log"])
    monkeypatch.setattr(log_engine, "AGENT_HEALTH_FILE", tmp_path / "health.json")
    first = log_engine.registrar_evento_agente(
        "COLLECTOR", input_status="MARKET_CLOSED", output_status="WAITING_DATA",
        decision="WAIT", reason="weekend", state="WAITING_DATA",
    )
    second = log_engine.registrar_evento_agente(
        "COLLECTOR", input_status="MARKET_CLOSED", output_status="WAITING_DATA",
        decision="WAIT", reason="weekend", state="WAITING_DATA",
    )
    assert first["ok"] is True
    assert second["deduplicated"] is True
    assert (tmp_path / "agent.log").read_text(encoding="utf-8").count("AGENT_EVENT") == 1


def test_observability_failure_does_not_break_guards(tmp_path, monkeypatch):
    import log_engine

    monkeypatch.setattr(log_engine, "LOG_PATHS", [tmp_path / "agent.log"])
    monkeypatch.setattr(log_engine, "_salvar_saude_agentes", lambda payload: (_ for _ in ()).throw(OSError("disk")))
    assert log_engine.registrar_evento_agente("RISK", decision="BLOQUEADO")["ok"] is True


def test_analysis_uses_one_shared_context_envelope():
    source = _source("leon.py")
    assert "smc_context = {" in source
    for field in ["direction", "smc", "bos", "choch", "fvg", "fvg_zone"]:
        assert f'"{field}"' in source


def test_candle_snapshot_is_correlated_to_analysis_cycle():
    source = _source("leon.py")
    assert "from candle_reader import ler_candle_m15" in source
    assert "from mt5_execution_refiner import load_execution_candles" in source


def test_symbol_is_not_replaced_between_agents():
    source = _source("leon.py")
    assert '"XAUUSD"' in source
    assert 'symbol="XAUUSD"' in source


def test_council_and_executor_use_explicit_same_pre_operation_id():
    source = _source("mt5_order_executor.py")
    call = "avaliar_conselho_operadores(\n        pre_operation_id=pre_operation_id,\n        pre_operation=pre_operacao,"
    assert call in source


def test_observed_does_not_replace_active_opportunity():
    source = _source("pre_operation_engine.py")
    assert "Uma observacao posterior nao substitui" in source
    assert "registro = registro_ativo" in source


def test_executor_cannot_reach_send_before_council_and_risk():
    body = _source("mt5_order_executor.py").split("def executar_ordem_mt5_pre_operacao", 1)[1]
    council = body.index("conselho = avaliar_conselho_operadores")
    risk = body.index("plano_risco = calcular_plano_risco", council)
    ready = body.index('"READY_TO_EXECUTE"', risk)
    send = body.index("_order_send_with_connection_retry", ready)
    assert council < risk < ready < send


def test_openrouter_does_not_call_order_send():
    for name in ["openrouter_client.py", "openrouter_brain.py", "ai_manager.py", "model_router.py"]:
        assert "order_send(" not in _source(name)


def test_smc_agents_do_not_call_order_send():
    for name in ["institutional_analysis_engine.py", "smc_entry_guard.py", "smc_engine.py", "smc_study_engine.py"]:
        assert "order_send(" not in _source(name)


def test_elliott_agents_do_not_call_order_send():
    for name in ["institutional_analysis_engine.py", "elliott_engine.py", "elliott_study_engine.py"]:
        assert "order_send(" not in _source(name)


def test_risk_agent_does_not_create_signal_or_send_order():
    source = _source("risk_control_agent.py")
    assert "order_send(" not in source
    assert "gerar_sinal" not in source


def test_disconnected_demo_executor_is_not_in_main_import_graph():
    source = _source("leon_operator.py") + _source("leon.py")
    assert "from demo_execution_engine" not in source
    assert "import demo_execution_engine" not in source


def test_only_canonical_operational_executor_is_imported_by_operator():
    source = _source("leon_operator.py")
    assert "from mt5_order_executor import" in source
    assert "executar_ordem_mt5_pre_operacao" in source


def test_openrouter_failure_cannot_bypass_execution_guards():
    source = _source("mt5_order_executor.py")
    assert "openrouter" not in source.lower()
    assert "validate_account_for_demo_trade" in source
    assert "avaliar_limite_perda_diaria" in source


def test_engineering_auto_fix_is_disabled_during_operation():
    config = (ROOT / "config.ini").read_text(encoding="utf-8")
    assert "support_programmer_auto_fix = false" in config
    source = _source("leon_operator.py")
    assert '"support_programmer_auto_fix": False' in source


def test_momentum_remains_disabled_and_non_mandatory():
    source = _source("leon.py")
    assert '"DESATIVADO"' in source
    assert "momentum_reader" not in source


def test_score_is_legacy_telemetry_without_operational_threshold():
    source = _source("leon.py")
    assert 'score = calcular_market_score(tendencia)' in source
    assert "score_threshold_atual" not in source
    assert "score_minimo_entrada_demo =" not in source


def test_real_account_remains_blocked_by_canonical_executor():
    source = _source("mt5_order_executor.py")
    assert "validate_account_for_demo_trade" in source
    assert 'execution_mode != "DEMO_REAL"' in source


def test_pre_operation_lifecycle_module_is_not_bypassed():
    source = _source("mt5_order_executor.py")
    assert "selecionar_pre_operacao_ativa()" in source
    assert '"PRE_TRADE_VALID"' in source
    assert '"RISK_APPROVED"' in source
    assert '"READY_TO_EXECUTE"' in source
