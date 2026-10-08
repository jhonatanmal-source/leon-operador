from pathlib import Path

from src import decision_diagnostic as diagnostic
from src import top_down_agent as top_down
from src.operator_council import avaliar_conselho_operadores
from src.timeframe_policy import evaluate_timeframe_policy


def candle(value=100.0):
    return {
        "data": "2026-10-07T12:00:00",
        "ativo": "XAUUSD",
        "open": value,
        "high": value + 0.2,
        "low": value - 0.2,
        "close": value,
    }


def test_lateral_candles_are_wait_not_missing_data(tmp_path, monkeypatch):
    memory = tmp_path / "top_down.csv"
    monkeypatch.setattr(top_down, "TOP_DOWN_FILE", memory)
    monkeypatch.setattr(top_down, "DATA_DIR", tmp_path)
    monkeypatch.setattr(top_down, "CANDLE_HISTORY_FILE", tmp_path / "missing.csv")

    result = top_down.gerar_leitura_top_down(
        [candle() for _ in range(120)],
        [candle() for _ in range(30)],
        [candle() for _ in range(24)],
    )

    assert result["alinhamento"] == "LATERAL"
    assert "entrada nao liberada" in result["resumo"].lower()


def test_missing_candles_remain_missing_data(tmp_path, monkeypatch):
    memory = tmp_path / "top_down.csv"
    monkeypatch.setattr(top_down, "TOP_DOWN_FILE", memory)
    monkeypatch.setattr(top_down, "DATA_DIR", tmp_path)
    monkeypatch.setattr(top_down, "CANDLE_HISTORY_FILE", tmp_path / "missing.csv")

    result = top_down.gerar_leitura_top_down([], [], [])

    assert result["alinhamento"] == "SEM DADOS"


def test_aligned_and_mixed_contracts_are_unchanged(tmp_path, monkeypatch):
    memory = tmp_path / "top_down.csv"
    monkeypatch.setattr(top_down, "TOP_DOWN_FILE", memory)
    monkeypatch.setattr(top_down, "DATA_DIR", tmp_path)
    monkeypatch.setattr(top_down, "CANDLE_HISTORY_FILE", tmp_path / "missing.csv")

    rising = [candle(100 + index) for index in range(120)]
    falling = [candle(220 - index) for index in range(30)]
    aligned = top_down.gerar_leitura_top_down(rising, rising[-30:], rising[-24:])
    mixed = top_down.gerar_leitura_top_down(rising, falling, rising[-24:])

    assert aligned["alinhamento"] == "ALINHADO"
    assert mixed["alinhamento"] == "MISTO"


def test_lateral_is_not_approved_by_timeframe_policy():
    top_down_reading = {
        "macro_semanal": "LATERAL",
        "h4_bias": "LATERAL",
        "h1_contexto": "LATERAL",
        "m15_gatilho": "LATERAL",
    }

    assert not evaluate_timeframe_policy(top_down_reading, "COMPRA")["approved"]
    assert not evaluate_timeframe_policy(top_down_reading, "VENDA")["approved"]


def test_council_blocks_lateral_top_down(monkeypatch):
    base_status = {
        "operators": {
            "collector": {"status": "OK", "summary": "ok"},
            "alignment": {"status": "ALINHADO", "summary": "ok"},
            "setup": {"status": "PRONTO", "direcao": "COMPRA"},
        }
    }
    monkeypatch.setattr("src.operator_council.obter_status_operadores", lambda: base_status)
    monkeypatch.setattr("src.operator_council.resumo_pre_operacao", lambda: {"ultimo": None})
    monkeypatch.setattr("src.operator_council.avaliar_prontidao_operacional", lambda: {"nivel": "LIBERADO_PARA_REVISAO", "resumo": "ok"})
    monkeypatch.setattr("src.operator_council.resumo_risco", lambda: {})
    monkeypatch.setattr(
        "src.operator_council.ultima_leitura_top_down",
        lambda: {"alinhamento": "LATERAL", "resumo": "Aguardar confirmacao."},
    )

    council = avaliar_conselho_operadores()

    assert council["decision"] == "BLOQUEADO"
    top_down_vote = next(vote for vote in council["votes"] if vote["operator"] == "Top-Down")
    assert top_down_vote["decision"] == "BLOQUEIA"


def test_diagnostics_classify_wait_fail_and_never_authorize(tmp_path, monkeypatch):
    status_file = tmp_path / "decision_diagnostic.json"
    monkeypatch.setattr(diagnostic, "STATUS_FILE", status_file)

    wait = diagnostic.record("analysis", {"ok": True}, ["TOP_DOWN_M15_NOT_ALIGNED"])
    failure = diagnostic.record("execution", {"ok": False, "error": "MT5_ACCOUNT_NOT_AVAILABLE"})
    persisted = diagnostic.read_status()

    assert wait["category"] == "WAIT"
    assert failure["category"] == "FAIL"
    assert persisted["analysis"]["code"] == "CYCLE_COMPLETED"
    assert "execution_allowed" not in persisted["analysis"]
    assert "execution_allowed" not in persisted["execution"]
