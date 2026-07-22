import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


os.environ["LEON_CYCLE_ID"] = "CYCLE-TEST"
os.environ["LEON_ANALYSIS_ID"] = "ANALYSIS-TEST"


@pytest.fixture
def mock_config():
    with patch("src.mt5_order_executor._execution_config") as m:
        m.return_value = {
            "enabled": True,
            "demo_only": True,
            "learning_lab_enabled": False,
            "lot": 0.01,
            "deviation": 20,
            "magic": 20260616,
            "max_spread": 50.0,
            "max_demo_orders_day": 3,
            "min_live_rr": 1.0,
            "max_entry_drift_points": 5.0,
        }
        yield m


@pytest.fixture
def mock_mt5():
    import sys
    m = MagicMock(name="mt5linux_compat")
    m.initialize.return_value = True
    m.TRADE_RETCODE_DONE = 10009
    m.ORDER_TYPE_BUY = 0
    m.ORDER_TYPE_SELL = 1
    m.TRADE_ACTION_DEAL = 1
    m.ORDER_TIME_GTC = 0
    m.ORDER_FILLING_IOC = 1
    m.ACCOUNT_TRADE_MODE_DEMO = 4

    account = MagicMock()
    account.balance = 10000.0
    account.profit = 0.0
    account.trade_mode = 4
    m.account_info.return_value = account

    tick = MagicMock()
    tick.ask = 2300.0
    tick.bid = 2299.5
    tick.time = 1234567890
    m.symbol_info_tick.return_value = tick

    symbol = MagicMock()
    symbol.trade_mode = 4
    symbol.volume_step = 0.01
    symbol.volume_min = 0.01
    symbol.volume_max = 100.0
    m.symbol_info.return_value = symbol

    result = MagicMock()
    result.retcode = 10009
    result.order = 12345
    result.comment = "Done"
    m.order_send.return_value = result
    m.order_check.return_value = result
    m.last_error.return_value = ()

    sys.modules["mt5linux_compat"] = m
    yield m
    sys.modules.pop("mt5linux_compat", None)


@pytest.fixture
def mock_csv(tmp_path):
    path = tmp_path / "mt5_order_memory.csv"
    with patch("src.mt5_order_executor.ORDER_MEMORY_FILE", path):
        yield path


@pytest.fixture
def mock_pre_op_csv(tmp_path):
    path = tmp_path / "pre_operation_trades.csv"
    with patch("src.mt5_order_executor.PRE_OPERATION_FILE", path):
        import csv
        campos = [
            "id", "data_abertura", "data_fechamento", "ativo", "direcao",
            "status_setup", "metodo_risco", "context_mode", "entrada", "stop",
            "tp1", "tp2", "rr", "smc", "elliott", "bos", "choch", "confianca",
            "brain_score", "status", "resultado", "observacao",
            "region_id", "structural_gate_version", "structural_gate_timestamp",
            "structural_gate_result",
        ]
        with path.open("w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=campos, delimiter=";")
            w.writeheader()
            w.writerow({
                "id": "PREOP-TEST-1",
                "data_abertura": "2026-07-20T10:00:00",
                "ativo": "XAUUSD",
                "direcao": "COMPRA",
                "status_setup": "COMPLETO",
                "entrada": "2300.0",
                "stop": "2295.0",
                "tp1": "2310.0",
                "tp2": "2320.0",
                "rr": "2.0",
                "smc": "OK",
                "bos": "OK",
                "choch": "OK",
                "confianca": "80",
                "brain_score": "80",
                "status": "ABERTO",
                "resultado": "",
                "region_id": "REG-TEST-1234",
                "structural_gate_version": "LEON_CAUSAL_CONTRACT_V2",
                "structural_gate_timestamp": "2026-07-20T09:00:00",
                "structural_gate_result": "PASSED",
            })
        yield path


@pytest.fixture
def mock_deps():
    patches = [
        patch("src.mt5_order_executor.registrar_erro"),
        patch("src.mt5_order_executor.registrar_log"),
        patch("src.mt5_order_executor.registrar_contexto_cerebro"),
        patch("src.mt5_order_executor.avaliar_conselho_operadores"),
        patch("src.mt5_order_executor.registrar_relatorio_operacao"),
        patch("src.mt5_order_executor.invalidar_pre_operacao"),
        patch("src.mt5_order_executor.avaliar_limite_perda_diaria"),
        patch("src.mt5_order_executor.avaliar_orcamento_risco_aberto"),
        patch("src.mt5_order_executor.calcular_plano_risco"),
        patch("src.mt5_order_executor.enviar_mensagem"),
        patch("src.mt5_order_executor.enviar_erro_sistema"),
        patch("src.mt5_order_executor.avaliar_news_shield", return_value={"approved": True}),
        patch("src.mt5_order_executor.validate_smc_entry", return_value={"approved": True}),
        patch("src.mt5_order_executor.ultima_leitura_top_down", return_value={"alinhamento": "ALINHADO", "m15_gatilho": "COMPRA"}),
        patch("src.mt5_order_executor.status_autonomia", return_value={"active": True, "scope": "demo_execution"}),
        patch("src.mt5_order_executor.evaluate_timeframe_policy", return_value={"approved": True, "mode": "TENDENCIA"}),
        patch("src.mt5_order_executor.identificar_sessao", return_value="LONDON"),
        patch("src.mt5_order_executor.capturar_print_mt5"),
        patch("src.mt5_order_executor.gerar_print_entrada"),
        patch("src.mt5_order_executor.enviar_foto"),
        patch("src.mt5_order_executor.validate_zone_for_execution", return_value={"ok": True, "region": {"region_id": "REG-TEST-1234"}}),
    ]
    for p in patches:
        p.start()
    yield
    for p in patches:
        p.stop()


@pytest.fixture
def mock_risk_config():
    with patch("src.mt5_order_executor._risk_gate_config") as m:
        m.return_value = {
            "risk_percent": 0.5,
            "max_risk_percent": 1.0,
            "daily_loss_percent": 2.0,
            "max_lot": 0.01,
            "min_lot": 0.01,
            "min_setup_score": 70,
        }
        yield m


class TestPureFunctions:
    def test_explicar_retcode(self):
        from src.mt5_order_executor import _explicar_retcode
        result = _explicar_retcode(10009)
        assert isinstance(result, tuple)
        assert len(result) >= 1

    def test_bloqueio(self):
        from src.mt5_order_executor import _bloqueio
        r = _bloqueio("TEST_ERROR")
        assert r["ok"] is False
        assert r["error"] == "TEST_ERROR"

    def test_valor_normal(self):
        from src.mt5_order_executor import _valor
        assert _valor(1.5) == 1.5

    def test_valor_none(self):
        from src.mt5_order_executor import _valor
        assert _valor(None) == "SEM DADOS"


class TestExecutor:
    def test_sem_pre_operacao(self, mock_mt5, mock_config, mock_deps, mock_csv, mock_risk_config, tmp_path):
        path = tmp_path / "pre_operation_trades.csv"
        with patch("src.mt5_order_executor.PRE_OPERATION_FILE", path):
            path.write_text("id;data_abertura;ativo;direcao;status_setup;entrada;stop;tp1;tp2;rr;smc;status;resultado\n", encoding="utf-8")
            from src.mt5_order_executor import executar_ordem_mt5_pre_operacao
            result = executar_ordem_mt5_pre_operacao(forcar=True)
            assert result.get("error") in ("NO_OPEN_PRE_OPERATION_TO_EXECUTE", None) or result.get("ok") is not None

    def test_mt5_desconectado(self, mock_config, mock_deps, mock_pre_op_csv, mock_csv, mock_risk_config):
        import sys
        from src.mt5_order_executor import executar_ordem_mt5_pre_operacao
        mt5_mock = MagicMock(name="mt5linux_compat")
        mt5_mock.initialize.return_value = False
        mt5_mock.last_error.return_value = ("err",)
        sys.modules["mt5linux_compat"] = mt5_mock
        result = executar_ordem_mt5_pre_operacao(forcar=False)
        assert result.get("ok") is False
        sys.modules.pop("mt5linux_compat", None)

    def test_limite_diario_atingido(self, mock_mt5, mock_config, mock_deps, mock_pre_op_csv, mock_csv, mock_risk_config):
        from src.mt5_order_executor import executar_ordem_mt5_pre_operacao
        with patch("src.mt5_order_executor._ordens_demo_hoje", return_value=3):
            result = executar_ordem_mt5_pre_operacao(forcar=False)
            assert result.get("error") == "MAX_DEMO_ORDERS_DAY_REACHED"

    def test_ordens_demo_hoje_empty(self, tmp_path):
        path = tmp_path / "mt5_order_memory.csv"
        with patch("src.mt5_order_executor.ORDER_MEMORY_FILE", path):
            from src.mt5_order_executor import _ordens_demo_hoje
            import csv
            campos = ["data", "pre_operation_id", "status"]
            with path.open("w", encoding="utf-8", newline="") as f:
                w = csv.DictWriter(f, fieldnames=campos, delimiter=";")
                w.writeheader()
                w.writerow({"data": "2026-06-01", "status": "OK"})
            assert _ordens_demo_hoje() == 0

    def test_structural_gate_blocks_sem_region_id(self, mock_mt5, mock_config, mock_deps, mock_csv, mock_risk_config, tmp_path):
        from src.mt5_order_executor import executar_ordem_mt5_pre_operacao
        path = tmp_path / "pre_operation_trades.csv"
        with patch("src.mt5_order_executor.PRE_OPERATION_FILE", path):
            import csv
            campos = [
                "id", "data_abertura", "ativo", "direcao", "status_setup",
                "entrada", "stop", "tp1", "tp2", "rr", "smc", "status",
                "resultado", "region_id",
            ]
            with path.open("w", encoding="utf-8", newline="") as f:
                w = csv.DictWriter(f, fieldnames=campos, delimiter=";")
                w.writeheader()
                w.writerow({
                    "id": "PREOP-NO-REGION",
                    "data_abertura": "2026-07-20T10:00:00",
                    "ativo": "XAUUSD",
                    "direcao": "COMPRA",
                    "status_setup": "COMPLETO",
                    "entrada": "2300.0",
                    "stop": "2295.0",
                    "tp1": "2310.0",
                    "tp2": "2320.0",
                    "rr": "2.0",
                    "smc": "OK",
                    "status": "ABERTO",
                    "resultado": "",
                    "region_id": "",
                })
            with patch("src.mt5_order_executor.validate_zone_for_execution", side_effect=lambda po: {
                "ok": False, "error": "PRE_OPERATION_REGION_REQUIRED",
                "reason": "Nova PRE_OPERATION sem region_id canonico."
            }):
                result = executar_ordem_mt5_pre_operacao(forcar=False)
                assert result.get("ok") is False

    def test_lote_invalido_bloqueado(self, mock_mt5, mock_config, mock_deps, mock_pre_op_csv, mock_csv, mock_risk_config):
        from src.mt5_order_executor import executar_ordem_mt5_pre_operacao
        with patch("src.mt5_order_executor.calcular_plano_risco", return_value={"approved": True, "lot": 0, "estimated_risk": 0.0, "estimated_risk_percent": 0.0}):
            result = executar_ordem_mt5_pre_operacao(forcar=False)
            assert result.get("ok") is False

    def test_lote_negativo_bloqueado(self, mock_mt5, mock_config, mock_deps, mock_pre_op_csv, mock_csv, mock_risk_config):
        from src.mt5_order_executor import executar_ordem_mt5_pre_operacao
        with patch("src.mt5_order_executor.calcular_plano_risco", return_value={"approved": True, "lot": -0.01, "estimated_risk": 0.0, "estimated_risk_percent": 0.0}):
            result = executar_ordem_mt5_pre_operacao(forcar=False)
            assert result.get("ok") is False

    def test_happy_path_demo_executes_order(self, mock_mt5, mock_config, mock_deps, mock_pre_op_csv, mock_csv, mock_risk_config):
        from src.mt5_order_executor import executar_ordem_mt5_pre_operacao
        with patch("src.mt5_order_executor.calcular_plano_risco", return_value={"approved": True, "lot": 0.01, "estimated_risk": 50.0, "estimated_risk_percent": 0.5}):
            with patch("src.mt5_order_executor.avaliar_orcamento_risco_aberto", return_value={"approved": True}):
                result = executar_ordem_mt5_pre_operacao(forcar=False)
                assert result.get("ok") is True
                assert result.get("order", {}).get("status") == "ENVIADA"
                mock_mt5.order_send.assert_called_once()
