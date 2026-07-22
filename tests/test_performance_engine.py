import os
from pathlib import Path

import pytest

from src.performance_engine import (
    METRIC_INSUFFICIENT_DATA,
    METRIC_NOT_AVAILABLE,
    analisar_performance,
)

DATA = Path(__file__).resolve().parent.parent / "data"
CSV = DATA / "pre_operation_trades.csv"


def _escrever_csv(linhas: list[list[str]]):
    DATA.mkdir(parents=True, exist_ok=True)
    cabecalho = [
        "id", "data_abertura", "data_fechamento", "ativo", "direcao",
        "status_setup", "metodo_risco", "context_mode", "entrada", "stop",
        "tp1", "tp2", "rr", "smc", "elliott", "bos", "choch", "confianca",
        "brain_score", "status", "resultado", "observacao",
        "region_id", "structural_gate_version", "structural_gate_timestamp",
        "structural_gate_result", "origin",
    ]
    with CSV.open("w", encoding="utf-8", newline="") as f:
        f.write(";".join(cabecalho) + "\n")
        for linha in linhas:
            f.write(";".join(linha) + "\n")


def _limpar_csv():
    if CSV.exists():
        CSV.unlink()


def test_conjunto_vazio():
    _limpar_csv()
    r = analisar_performance()
    assert r["total_trades"] == 0
    assert r["win_rate"] == METRIC_INSUFFICIENT_DATA
    assert r["expectativa"] == METRIC_INSUFFICIENT_DATA


def test_um_trade_vencedor():
    _escrever_csv([
        ["PREOP-001", "2026-07-20T10:00:00", "2026-07-20T11:00:00", "XAUUSD",
         "COMPRA", "COMPLETO", "", "TENDENCIA", "2300.0", "2295.0",
         "2310.0", "2320.0", "2.0", "OK", "", "BOS", "", "85",
         "80", "FECHADO", "WIN_TP1", ""],
    ])
    r = analisar_performance()
    assert r["total_trades"] == 1
    assert r["wins"] == 1
    assert r["losses"] == 0
    assert r["win_rate"] == 100.0


def test_um_trade_perdedor():
    _escrever_csv([
        ["PREOP-002", "2026-07-20T10:00:00", "2026-07-20T11:00:00", "XAUUSD",
         "COMPRA", "COMPLETO", "", "TENDENCIA", "2300.0", "2295.0",
         "2310.0", "2320.0", "2.0", "OK", "", "BOS", "", "85",
         "80", "FECHADO", "LOSS", ""],
    ])
    r = analisar_performance()
    assert r["total_trades"] == 1
    assert r["wins"] == 0
    assert r["losses"] == 1
    assert r["win_rate"] == 0.0


def test_breakeven():
    _escrever_csv([
        ["PREOP-003", "2026-07-20T10:00:00", "2026-07-20T11:00:00", "XAUUSD",
         "COMPRA", "COMPLETO", "", "TENDENCIA", "2300.0", "2295.0",
         "2310.0", "2320.0", "2.0", "OK", "", "BOS", "", "85",
         "80", "FECHADO", "BREAK_EVEN", ""],
    ])
    r = analisar_performance()
    assert r["breakeven"] == 1


def test_profit_factor_sem_perdas():
    _escrever_csv([
        ["PREOP-004", "2026-07-20T10:00:00", "2026-07-20T11:00:00", "XAUUSD",
         "COMPRA", "COMPLETO", "", "TENDENCIA", "2300.0", "2295.0",
         "2310.0", "2320.0", "2.0", "OK", "", "BOS", "", "85",
         "80", "FECHADO", "WIN_TP1", ""],
    ])
    r = analisar_performance()
    assert r["total_trades"] == 1
    assert r["profit_factor"] == METRIC_NOT_AVAILABLE


def test_drawdown():
    _escrever_csv([
        ["PREOP-005", "2026-07-20T10:00:00", "2026-07-20T11:00:00", "XAUUSD",
         "COMPRA", "COMPLETO", "", "TENDENCIA", "2300.0", "2295.0",
         "2310.0", "2320.0", "2.0", "OK", "", "BOS", "", "85",
         "80", "FECHADO", "LOSS", ""],
        ["PREOP-006", "2026-07-20T12:00:00", "2026-07-20T13:00:00", "XAUUSD",
         "VENDA", "COMPLETO", "", "TENDENCIA", "2310.0", "2315.0",
         "2300.0", "2290.0", "2.0", "OK", "", "BOS", "", "85",
         "80", "FECHADO", "LOSS", ""],
    ])
    r = analisar_performance()
    assert r["losses"] == 2
    assert r["drawdown_maximo"] > 0


def test_sequencia_perdas():
    _escrever_csv([
        ["PREOP-007", "2026-07-20T10:00:00", "2026-07-20T11:00:00", "XAUUSD",
         "COMPRA", "COMPLETO", "", "TENDENCIA", "2300.0", "2295.0",
         "2310.0", "2320.0", "2.0", "OK", "", "BOS", "", "85",
         "80", "FECHADO", "LOSS", ""],
        ["PREOP-008", "2026-07-20T11:00:00", "2026-07-20T12:00:00", "XAUUSD",
         "COMPRA", "COMPLETO", "", "TENDENCIA", "2300.0", "2295.0",
         "2310.0", "2320.0", "2.0", "OK", "", "BOS", "", "85",
         "80", "FECHADO", "LOSS", ""],
        ["PREOP-009", "2026-07-20T12:00:00", "2026-07-20T13:00:00", "XAUUSD",
         "COMPRA", "COMPLETO", "", "TENDENCIA", "2300.0", "2295.0",
         "2310.0", "2320.0", "2.0", "OK", "", "BOS", "", "85",
         "80", "FECHADO", "WIN_TP1", ""],
    ])
    r = analisar_performance()
    assert r["sequencia_maxima_perdas"] == 2


def test_registros_invalidos_ignorados():
    _escrever_csv([
        ["PREOP-010", "2026-07-20T10:00:00", "2026-07-20T11:00:00", "XAUUSD",
         "COMPRA", "COMPLETO", "", "TENDENCIA", "2300.0", "2295.0",
         "2310.0", "2320.0", "", "OK", "", "BOS", "", "85",
         "80", "FECHADO", "WIN_TP1", ""],
    ])
    r = analisar_performance()
    assert r["resultado_por_direcao"]["COMPRA"]["wins"] == 1


def test_campos_ausentes():
    _escrever_csv([
        ["PREOP-011", "", "", "XAUUSD",
         "", "", "", "", "", "",
         "", "", "", "", "", "", "", "",
         "", "FECHADO", "WIN_TP1", ""],
    ])
    r = analisar_performance()
    assert r["total_trades"] == 1


def test_divisao_por_zero():
    _limpar_csv()
    r = analisar_performance()
    assert r["win_rate"] == METRIC_INSUFFICIENT_DATA
    assert r["expectativa"] == METRIC_INSUFFICIENT_DATA


def test_ordenacao_temporal():
    _escrever_csv([
        ["PREOP-012", "2026-07-20T10:00:00", "2026-07-20T11:00:00", "XAUUSD",
         "COMPRA", "COMPLETO", "", "TENDENCIA", "2300.0", "2295.0",
         "2310.0", "2320.0", "2.0", "OK", "", "BOS", "", "85",
         "80", "FECHADO", "WIN_TP1", ""],
    ])
    r = analisar_performance()
    assert not isinstance(r["resultado_em_r"], str)


def test_dados_reais_sem_mutacao():
    _escrever_csv([
        ["PREOP-013", "2026-07-20T10:00:00", "2026-07-20T11:00:00", "XAUUSD",
         "COMPRA", "COMPLETO", "", "TENDENCIA", "2300.0", "2295.0",
         "2310.0", "2320.0", "2.0", "OK", "", "BOS", "", "85",
         "80", "FECHADO", "WIN_TP1", ""],
    ])
    original = CSV.read_text(encoding="utf-8")
    analisar_performance()
    assert CSV.read_text(encoding="utf-8") == original
    _limpar_csv()


def _trade(**kw):
    base = {
        "id": "PREOP-T",
        "data_abertura": "2026-07-20T10:00:00",
        "data_fechamento": "2026-07-20T11:00:00",
        "ativo": "XAUUSD",
        "direcao": "COMPRA",
        "rr": "2.0",
        "status": "FECHADO",
        "resultado": "WIN_TP1",
    }
    base.update(kw)
    return base


def test_profit_factor_sem_ganhos():
    r = analisar_performance(registros=[
        _trade(resultado="LOSS", rr="1.0"),
    ])
    assert r["profit_factor"] == 0.0


def test_expectativa():
    r = analisar_performance(registros=[
        _trade(id="T1", resultado="LOSS", rr="1.0"),
        _trade(id="T2", resultado="WIN_TP1", rr="2.0"),
    ])
    assert isinstance(r["expectativa"], float)
    assert r["expectativa"] > 0


def test_sequencia_maxima_ganhos():
    r = analisar_performance(registros=[
        _trade(id="T1", resultado="WIN_TP1", rr="1.0"),
        _trade(id="T2", resultado="WIN_TP1", rr="1.0"),
        _trade(id="T3", resultado="LOSS", rr="1.0"),
    ])
    assert r["sequencia_maxima_ganhos"] == 2
    assert r["sequencia_maxima_perdas"] == 1


def test_trade_aberto_excluido():
    r = analisar_performance(registros=[
        _trade(id="T1", resultado="WIN_TP1", status="ABERTO"),
    ])
    assert r["total_trades"] == 0
    assert r["total_abertos"] == 1


def test_registro_sem_resultado():
    r = analisar_performance(registros=[
        _trade(id="T1", resultado=""),
    ])
    assert r["total_trades"] == 0
    assert r["discarded"] == 1


def test_resultado_nan():
    r = analisar_performance(registros=[
        _trade(id="T1", resultado="NaN"),
    ])
    assert r["total_trades"] == 0


def test_resultado_infinito():
    r = analisar_performance(registros=[
        _trade(id="T1", resultado="inf"),
    ])
    assert r["total_trades"] == 0


def test_resultado_formato_invalido():
    r = analisar_performance(registros=[
        _trade(id="T1", resultado="GARBAGE"),
    ])
    assert r["total_trades"] == 0
    assert r["discarded"] == 1
    assert r["discarded_details"][0]["reason"] == "UNKNOWN_RESULT_GARBAGE"


def test_campo_ausente_varios():
    r = analisar_performance(registros=[
        {"id": "T1", "status": "FECHADO", "resultado": "WIN_TP1"},
    ])
    assert r["total_trades"] == 1
    assert r["wins"] == 1


def test_origens_diferentes():
    r = analisar_performance(registros=[
        _trade(id="T1", origin="DEMO", resultado="WIN_TP1"),
        _trade(id="T2", origin="REPLAY", resultado="LOSS"),
    ])
    assert r["total_trades"] == 2
    assert "DEMO" in r["origens"]
    assert "REPLAY" in r["origens"]

    r_demo = analisar_performance(registros=[
        _trade(id="T1", origin="DEMO", resultado="WIN_TP1"),
        _trade(id="T2", origin="REPLAY", resultado="LOSS"),
    ], origem="DEMO")
    assert r_demo["total_trades"] == 1
    assert r_demo["wins"] == 1


def test_reproduzivel():
    registros = [
        _trade(id="T1", resultado="WIN_TP1", rr="2.0"),
        _trade(id="T2", resultado="LOSS", rr="1.0"),
    ]
    r1 = analisar_performance(registros=registros)
    r2 = analisar_performance(registros=registros)
    assert r1 == r2


def test_zero_real_vs_not_available():
    r = analisar_performance(registros=[])
    assert r["win_rate"] == METRIC_INSUFFICIENT_DATA
    assert r["win_rate"] != 0.0
    assert r["total_trades"] == 0


def test_ratio_win_loss():
    r = analisar_performance(registros=[
        _trade(id="T1", resultado="WIN_TP1", rr="1.0"),
        _trade(id="T2", resultado="WIN_TP1", rr="1.0"),
        _trade(id="T3", resultado="LOSS", rr="1.0"),
        _trade(id="T4", resultado="LOSS", rr="1.0"),
    ])
    assert r["ratio_win_loss"] == 1.0


def test_media_r_vencedores_perdedores():
    r = analisar_performance(registros=[
        _trade(id="T1", resultado="WIN_TP1", rr="2.0"),
        _trade(id="T2", resultado="WIN_TP2", rr="2.0"),
        _trade(id="T3", resultado="LOSS", rr="1.0"),
    ])
    assert r["media_r_vencedores"] == 3.0
    assert r["media_r_perdedores"] == 1.0


def test_data_inicio_fim():
    r = analisar_performance(registros=[
        _trade(id="T1", data_fechamento="2026-07-20T10:00:00"),
        _trade(id="T2", data_fechamento="2026-07-21T10:00:00"),
    ])
    assert "2026-07-20" in str(r["data_inicio"])
    assert "2026-07-21" in str(r["data_fim"])


def test_discarded_details():
    r = analisar_performance(registros=[
        _trade(id="T1", resultado=""),
        _trade(id="T2", resultado="WIN_TP1"),
    ])
    assert r["discarded"] == 1
    assert len(r["discarded_details"]) == 1
    assert r["discarded_details"][0]["id"] == "T1"
    assert r["discarded_details"][0]["reason"] == "NO_RESULT"


def test_loss_rate():
    r = analisar_performance(registros=[
        _trade(id="T1", resultado="WIN_TP1"),
        _trade(id="T2", resultado="LOSS"),
    ])
    assert r["loss_rate"] == 50.0


def test_rr_invalido_nao_afeta_r_metrics():
    r = analisar_performance(registros=[
        _trade(id="T1", resultado="WIN_TP1", rr="2.0"),
        _trade(id="T2", resultado="WIN_TP1", rr=""),
        _trade(id="T3", resultado="LOSS", rr="1.0"),
    ])
    assert r["total_trades"] == 3
    assert r["total_com_r_valido"] == 2
    assert r["total_sem_r_valido"] == 1
    assert r["cobertura_r_percentual"] == 66.67
    assert r["resultado_em_r"] == 1.0
    assert r["media_r"] == 0.5
    assert r["wins"] == 2
    assert r["win_rate"] == 66.67


def test_sem_chamada_mt5():
    import src.performance_engine as pe
    source = open(pe.__file__, encoding="utf-8").read()
    assert "order_send" not in source
    assert "mt5" not in source.lower()


def test_cenario_a_win_tp1_rr2_loss_rr1():
    r = analisar_performance(registros=[
        _trade(id="T1", resultado="WIN_TP1", rr="2.0"),
        _trade(id="T2", resultado="LOSS", rr="1.0"),
    ])
    assert r["total_trades"] == 2
    assert r["total_com_r_valido"] == 2
    assert r["resultado_em_r"] == 1.0
    assert r["media_r"] == 0.5
    assert r["expectativa"] == 0.5
    assert r["profit_factor"] == 2.0
    assert r["wins"] == 1
    assert r["losses"] == 1
    assert r["win_rate"] == 50.0


def test_cenario_b_win_tp2_rr2_loss_rr1():
    r = analisar_performance(registros=[
        _trade(id="T1", resultado="WIN_TP2", rr="2.0"),
        _trade(id="T2", resultado="LOSS", rr="1.0"),
    ])
    assert r["total_trades"] == 2
    assert r["total_com_r_valido"] == 2
    assert r["resultado_em_r"] == 3.0
    assert r["media_r"] == 1.5
    assert r["expectativa"] == 1.5
    assert r["profit_factor"] == 4.0
