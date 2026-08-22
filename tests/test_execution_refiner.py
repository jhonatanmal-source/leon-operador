"""Testes do gatilho M5 de reteste (anti viés comprar topo / vender fundo).

Cobre a correção da pendência #10 (MISSION-20260818-CORRECAO-ENTRADA-SMC,
opção A): _micro_trigger não pode confirmar por rompimento de estrutura.
A confirmação exige sweep de liquidez + reclaim + deslocamento, sem romper
o extremo recente na direção da operação.
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from mt5_execution_refiner import _micro_trigger, refine_m15_m5


def _candle(o, h, l, c, t="2026-08-18T10:00:00"):
    return {"open": o, "high": h, "low": l, "close": c, "time": t}


def _base_recent():
    """4 candles fechados de referência: swing_high=101.0, swing_low=98.0."""
    return [
        _candle(100.0, 101.0, 98.0, 100.5),
        _candle(100.5, 100.8, 98.2, 99.0),
        _candle(99.0, 100.9, 98.1, 100.0),
        _candle(100.0, 101.0, 98.0, 99.5),
    ]


def _wrap(recent, current):
    """Monta a lista que o _micro_trigger recebe.

    _micro_trigger descarta o último candle (considera não fechado), então
    adiciona-se um candle dummy no final para que `recent + current` sejam os
    5 candles fechados analisados.
    """
    dummy_open = current["close"]
    return recent + [current] + [_candle(dummy_open, dummy_open + 0.1, dummy_open - 0.1, dummy_open)]


# ── Regressão do bug: rompimento NÃO confirma ────────────────────────────

def test_compra_rompimento_topo_nao_confirma():
    """COMPRA em rompimento de topo (sem sweep) NÃO deve confirmar (bug #10)."""
    recent = _base_recent()  # swing_high=101.0, swing_low=98.0
    # Candle que rompe o topo para cima, sem varrer liquidez abaixo.
    current = _candle(o=100.5, h=102.5, l=100.2, c=102.2)
    result = _micro_trigger(_wrap(recent, current), "COMPRA")
    assert result["confirmed"] is False
    assert result["structure_break"] is True
    assert result["sweep"] is False
    assert result["reason"] == "M5_AGUARDANDO_RETESTE"


def test_venda_rompimento_fundo_nao_confirma():
    """VENDA em rompimento de fundo (sem sweep) NÃO deve confirmar (bug #10)."""
    recent = _base_recent()
    current = _candle(o=99.0, h=99.3, l=96.5, c=96.8)
    result = _micro_trigger(_wrap(recent, current), "VENDA")
    assert result["confirmed"] is False
    assert result["structure_break"] is True
    assert result["sweep"] is False
    assert result["reason"] == "M5_AGUARDANDO_RETESTE"


# ── Confirmação por sweep + reclaim ──────────────────────────────────────

def test_compra_sweep_reclaim_confirma():
    """COMPRA: varre liquidez abaixo, reclaim acima do low, sem romper topo."""
    recent = _base_recent()  # swing_low=98.0, swing_high=101.0
    # low varre 98.0; close reclaim acima; high < 101.0 (não rompe topo);
    # corpo/range = (100.8-98.0)/(100.9-97.5)=2.8/3.4=0.82 (displacement ok)
    current = _candle(o=98.0, h=100.9, l=97.5, c=100.8)
    result = _micro_trigger(_wrap(recent, current), "COMPRA")
    assert result["sweep"] is True
    assert result["reclaim"] is True
    assert result["structure_break"] is False
    assert result["displacement"] is True
    assert result["confirmed"] is True
    assert result["reason"] == "M5_RETESTE_SWEEP_RECLAIM_CONFIRMADO"
    assert result["trigger_price"] == 100.8


def test_compra_close_exatamente_no_swing_low_nao_confirma():
    """COMPRA: close == swing_low não conta como reclaim (semântica estrita >)."""
    recent = _base_recent()  # swing_low=98.0
    current = _candle(o=97.5, h=99.5, l=96.0, c=98.0)  # close == swing_low
    result = _micro_trigger(_wrap(recent, current), "COMPRA")
    assert result["sweep"] is True
    assert result["reclaim"] is False  # 98.0 > 98.0 é False
    assert result["confirmed"] is False


def test_venda_sweep_reclaim_confirma():
    """VENDA: varre liquidez acima, reclaim abaixo do high, sem romper fundo."""
    recent = _base_recent()  # swing_high=101.0, swing_low=98.0
    # high varre 101.0; close reclaim abaixo; low > 98.0 (não rompe fundo);
    # corpo/range = (101.0-99.6)/(101.5-99.5)=1.4/2.0=0.7 (displacement ok)
    current = _candle(o=101.0, h=101.5, l=99.5, c=99.6)
    result = _micro_trigger(_wrap(recent, current), "VENDA")
    assert result["sweep"] is True
    assert result["reclaim"] is True
    assert result["structure_break"] is False
    assert result["displacement"] is True
    assert result["confirmed"] is True
    assert result["reason"] == "M5_RETESTE_SWEEP_RECLAIM_CONFIRMADO"


# ── Casos negativos ──────────────────────────────────────────────────────

def test_compra_sweep_sem_reclaim_nao_confirma():
    """COMPRA: varre o low mas fecha abaixo dele (continuou caindo) → sem entrada."""
    recent = _base_recent()  # swing_low=98.0
    current = _candle(o=98.5, h=98.7, l=96.5, c=96.9)  # close 96.9 < 98.0
    result = _micro_trigger(_wrap(recent, current), "COMPRA")
    assert result["sweep"] is True
    assert result["reclaim"] is False
    assert result["confirmed"] is False


def test_compra_reclaim_sem_sweep_nao_confirma():
    """COMPRA: candle forte de alta mas sem varrer liquidez abaixo → sem entrada."""
    recent = _base_recent()  # swing_low=98.0
    current = _candle(o=99.0, h=100.9, l=98.5, c=100.7)  # low 98.5 > 98.0
    result = _micro_trigger(_wrap(recent, current), "COMPRA")
    assert result["sweep"] is False
    assert result["confirmed"] is False


def test_sweep_reclaim_sem_displacement_nao_confirma():
    """Sweep + reclaim porém candle fraco (corpo/range < 0.55) → sem entrada."""
    recent = _base_recent()  # swing_low=98.0, swing_high=101.0
    # low varre 98.0, close reclaim, mas corpo pequeno:
    # corpo/range = (99.0-98.8)/(100.5-97.6)=0.2/2.9=0.069
    current = _candle(o=98.8, h=100.5, l=97.6, c=99.0)
    result = _micro_trigger(_wrap(recent, current), "COMPRA")
    assert result["sweep"] is True
    assert result["reclaim"] is True
    assert result["displacement"] is False
    assert result["confirmed"] is False


def test_poucos_candles_retorna_sem_dados():
    result = _micro_trigger([_candle(1, 2, 0.5, 1.5)], "COMPRA")
    assert result["confirmed"] is False
    assert result["reason"] == "M5_SEM_CANDLES_FECHADOS"


def test_contrato_de_retorno_preserva_chaves():
    recent = _base_recent()
    current = _candle(o=98.0, h=100.9, l=97.5, c=100.8)
    result = _micro_trigger(_wrap(recent, current), "COMPRA")
    for chave in (
        "confirmed", "structure_break", "reaction", "displacement",
        "trigger_price", "trigger_time", "reason",
    ):
        assert chave in result


# ── Integração leve: refine_m15_m5 propaga o trigger ─────────────────────

def test_refine_propaga_trigger(monkeypatch):
    recent = _base_recent()
    current = _candle(o=98.0, h=100.9, l=97.5, c=100.8)
    m5 = _wrap(recent, current)
    fake_market = {"ok": True, "m15": m5, "m5": m5, "h1": m5, "h4": m5}
    monkeypatch.setattr(
        "mt5_execution_refiner.load_execution_candles",
        lambda *a, **k: fake_market,
    )
    out = refine_m15_m5("COMPRA")
    assert out["ok"] is True
    assert out["trigger"]["confirmed"] is True
    assert out["trigger"]["reason"] == "M5_RETESTE_SWEEP_RECLAIM_CONFIRMADO"


def test_refine_repassa_erro_de_mercado(monkeypatch):
    monkeypatch.setattr(
        "mt5_execution_refiner.load_execution_candles",
        lambda *a, **k: {"ok": False, "error": "MT5_INITIALIZE_FAILED"},
    )
    out = refine_m15_m5("COMPRA")
    assert out["ok"] is False
    assert out["error"] == "MT5_INITIALIZE_FAILED"


# ── Propagação de símbolo (correção B1 — bug do default XAUUSD) ───────────

def test_refine_propaga_simbolo_para_load(monkeypatch):
    """refine_m15_m5 deve repassar o símbolo recebido a load_execution_candles.

    Regressão do bug B1: a corretora usa 'Gold_Spot', mas o default 'XAUUSD'
    fazia load_execution_candles retornar 0 candles -> INSUFFICIENT_EXECUTION_CANDLES
    em todo ciclo. O símbolo real precisa chegar até o carregador.
    """
    capturado = {}

    def _fake_load(symbol="XAUUSD", **kwargs):
        capturado["symbol"] = symbol
        return {"ok": True, "m15": [], "m5": [], "h1": [], "h4": []}

    monkeypatch.setattr(
        "mt5_execution_refiner.load_execution_candles", _fake_load
    )
    refine_m15_m5("COMPRA", symbol="Gold_Spot")
    assert capturado["symbol"] == "Gold_Spot"


def test_calcular_entrada_propaga_simbolo(monkeypatch):
    """calcular_entrada(symbol=...) deve chegar a refine_m15_m5 com o símbolo.

    Garante que o caller (leon.py passa symbol=ativo) não caia no default
    XAUUSD dentro do entry_price_engine.
    """
    import entry_price_engine

    capturado = {}

    def _fake_refine(direction, symbol="XAUUSD"):
        capturado["symbol"] = symbol
        # Sem trigger confirmado: interrompe cedo, basta validar a propagação.
        return {"ok": True, "m15": [], "m5": [], "trigger": {"confirmed": False, "reason": "X"}}

    monkeypatch.setattr(entry_price_engine, "refine_m15_m5", _fake_refine)
    entry_price_engine.calcular_entrada("COMPRA", 100.0, 98.0, symbol="Gold_Spot")
    assert capturado["symbol"] == "Gold_Spot"


def test_calcular_entrada_sem_simbolo_usa_default(monkeypatch):
    """Sem symbol explícito, mantém compatibilidade (default do refinador)."""
    import entry_price_engine

    capturado = {}

    def _fake_refine(direction, symbol="XAUUSD"):
        capturado["symbol"] = symbol
        return {"ok": True, "m15": [], "m5": [], "trigger": {"confirmed": False, "reason": "X"}}

    monkeypatch.setattr(entry_price_engine, "refine_m15_m5", _fake_refine)
    entry_price_engine.calcular_entrada("COMPRA", 100.0, 98.0)
    assert capturado["symbol"] == "XAUUSD"
