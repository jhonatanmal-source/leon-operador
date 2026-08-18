#!/usr/bin/env python3
"""
Testes de regressão — Bug #12 (MCP market cego por _MT5_AVAILABLE importado por valor).

Causa raiz: `leon_market_mcp.py` importava `_MT5_AVAILABLE` por valor (cópia `False`
no import). A flag só é atualizada dentro de `mt5_safe._ensure_initialized()`, então
os handlers checavam uma cópia estática que NUNCA vira True — todos os tools de
mercado retornavam "MT5 não disponível" mesmo com MT5 saudável.

Correção: os handlers agora usam `_mt5_disponivel()` → `check_mt5().get("available")`,
que dispara a inicialização lazy e retorna o status REAL.

Estes testes verificam o contrato sem depender de MT5 real:
  - quando `check_mt5` diz disponível, os handlers NÃO retornam "MT5 não disponível"
  - quando `check_mt5` diz indisponível, os handlers retornam o erro esperado
  - o helper `_mt5_disponivel` reflete o status real
"""

import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "src"))
sys.path.insert(0, str(PROJECT_ROOT / "src" / "mcp"))

from leon_market_mcp import MarketMCPHandler, _mt5_disponivel  # noqa: E402
from leon_backtest_mcp import BacktestMCPHandler  # noqa: E402


@pytest.fixture
def market_handler():
    return MarketMCPHandler()


@pytest.fixture
def backtest_handler():
    return BacktestMCPHandler()


@pytest.fixture(autouse=True)
def _isolar_check_mt5(monkeypatch):
    """Isola `check_mt5` por padrão (indisponível).

    - `leon_market_mcp.check_mt5`: importado no topo do módulo → mock no módulo.
    - `leon_backtest_mcp`: importa `check_mt5` DENTRO da função → mock em `mt5_safe`.
    """
    import leon_market_mcp
    import mt5_safe

    def _fake_check(available: bool):
        def _check() -> dict:
            return {
                "available": available,
                "error": "" if available else "simulado indisponível",
                "import_error": "",
                "note": "mock de teste",
            }
        return _check

    monkeypatch.setattr(leon_market_mcp, "check_mt5", _fake_check(False))
    monkeypatch.setattr(mt5_safe, "check_mt5", _fake_check(False))
    yield
    # Restaura para o estado original (função real de mt5_safe)
    monkeypatch.undo()


def _set_mt5_available(monkeypatch, available: bool):
    """Liga/desliga a disponibilidade simulada nos módulos sob teste."""
    import leon_market_mcp
    import mt5_safe

    def _check() -> dict:
        return {
            "available": available,
            "error": "" if available else "simulado indisponível",
            "import_error": "",
            "note": "mock de teste",
        }

    monkeypatch.setattr(leon_market_mcp, "check_mt5", _check)
    monkeypatch.setattr(mt5_safe, "check_mt5", _check)


# ─────────────────────────────────────────────────────────────
# Helper _mt5_disponivel
# ─────────────────────────────────────────────────────────────

def test_mt5_disponivel_reflete_status_real(monkeypatch):
    """O helper deve refletir o status REAL retornado por check_mt5()."""
    import leon_market_mcp

    monkeypatch.setattr(
        leon_market_mcp, "check_mt5",
        lambda: {"available": True, "error": "", "import_error": "", "note": ""}
    )
    assert _mt5_disponivel() is True

    monkeypatch.setattr(
        leon_market_mcp, "check_mt5",
        lambda: {"available": False, "error": "off", "import_error": "", "note": ""}
    )
    assert _mt5_disponivel() is False


# ─────────────────────────────────────────────────────────────
# Market MCP — handlers com MT5 disponível
# ─────────────────────────────────────────────────────────────

def test_market_get_current_price_nao_finge_indisponivel(monkeypatch, market_handler):
    """Com MT5 disponível, get_current_price NÃO deve retornar 'MT5 não disponível'."""
    _set_mt5_available(monkeypatch, True)
    import leon_market_mcp

    monkeypatch.setattr(leon_market_mcp, "safe_symbol_info_tick",
                        lambda s: {"symbol": s, "bid": 2500.0, "ask": 2500.5})
    result = market_handler.handle_get_current_price("XAUUSD")
    assert "MT5 não disponível" not in str(result)
    assert result["bid"] == 2500.0


def test_market_get_account_info_nao_finge_indisponivel(monkeypatch, market_handler):
    """Com MT5 disponível, get_account_info NÃO deve retornar 'MT5 não disponível'."""
    _set_mt5_available(monkeypatch, True)
    import leon_market_mcp

    monkeypatch.setattr(leon_market_mcp, "safe_account_info",
                        lambda: {"login": 12345, "balance": 10000.0, "equity": 10050.0})
    result = market_handler.handle_get_account_info()
    assert "MT5 não disponível" not in str(result)
    assert result["login"] == 12345


def test_market_get_ohlc_nao_finge_indisponivel(monkeypatch, market_handler):
    """Com MT5 disponível, get_ohlc NÃO deve retornar 'MT5 não disponível'."""
    _set_mt5_available(monkeypatch, True)
    import leon_market_mcp

    monkeypatch.setattr(
        leon_market_mcp, "safe_copy_rates_from_pos",
        lambda s, tf, sp, c: {"symbol": s, "rates": [{"time": 1, "open": 1.0}]}
    )
    result = market_handler.handle_get_ohlc("XAUUSD", 15, 5)
    assert "MT5 não disponível" not in str(result)
    assert result["rates"]


def test_market_list_symbols_nao_finge_indisponivel(monkeypatch, market_handler):
    """Com MT5 disponível, list_symbols NÃO deve retornar 'MT5 não disponível'."""
    _set_mt5_available(monkeypatch, True)
    import leon_market_mcp

    monkeypatch.setattr(leon_market_mcp, "safe_symbols_get",
                        lambda: {"symbols": [{"name": "XAUUSD"}], "count": 1})
    result = market_handler.handle_list_symbols()
    assert "MT5 não disponível" not in str(result)
    assert result["count"] == 1


def test_market_get_market_snapshot_nao_finge_indisponivel(monkeypatch, market_handler):
    """Com MT5 disponível, get_market_snapshot NÃO deve retornar 'MT5 não disponível'."""
    _set_mt5_available(monkeypatch, True)
    import leon_market_mcp

    monkeypatch.setattr(leon_market_mcp, "detectar_ativo", lambda: "XAUUSD")
    monkeypatch.setattr(leon_market_mcp, "safe_symbol_info_tick",
                        lambda s: {"symbol": s, "bid": 2500.0})
    monkeypatch.setattr(leon_market_mcp, "safe_symbol_info",
                        lambda s: {"symbol": s, "digits": 2})
    monkeypatch.setattr(leon_market_mcp, "safe_copy_rates_from_pos",
                        lambda s, tf, sp, c: {"rates": [{"time": 1}]})
    monkeypatch.setattr(leon_market_mcp, "safe_account_info",
                        lambda: {"login": 12345})

    result = market_handler.handle_get_market_snapshot()
    assert "MT5 não disponível" not in str(result)
    assert "XAUUSD" in result["symbols"]


# ─────────────────────────────────────────────────────────────
# Market MCP — handlers com MT5 indisponível (comportamento de segurança)
# ─────────────────────────────────────────────────────────────

def test_market_get_current_price_indisponivel(monkeypatch, market_handler):
    """Com MT5 indisponível, get_current_price retorna o erro de disponibilidade."""
    _set_mt5_available(monkeypatch, False)
    result = market_handler.handle_get_current_price("XAUUSD")
    assert result.get("error") == "MT5 não disponível"


def test_market_get_account_info_indisponivel(monkeypatch, market_handler):
    """Com MT5 indisponível, get_account_info retorna o erro de disponibilidade."""
    _set_mt5_available(monkeypatch, False)
    result = market_handler.handle_get_account_info()
    assert result.get("error") == "MT5 não disponível"


def test_market_get_ohlc_indisponivel(monkeypatch, market_handler):
    """Com MT5 indisponível, get_ohlc retorna o erro de disponibilidade."""
    _set_mt5_available(monkeypatch, False)
    result = market_handler.handle_get_ohlc("XAUUSD", 15, 5)
    assert result.get("error") == "MT5 não disponível"


# ─────────────────────────────────────────────────────────────
# Backtest MCP — usa o mesmo padrão
# ─────────────────────────────────────────────────────────────

def test_backtest_usa_check_mt5_e_nao_flag_estatica(monkeypatch, backtest_handler):
    """Backtest deve consultar check_mt5() real — não uma flag importada por valor.

    Com MT5 disponível e dados retornados, o resultado deve marcar
    'Backtest executado com dados MT5 reais' (sem cair na simulação).
    """
    _set_mt5_available(monkeypatch, True)
    import mt5_safe

    monkeypatch.setattr(
        mt5_safe, "safe_copy_rates_from_pos",
        lambda s, tf, sp, c: {
            "rates": [
                {"time": i, "open": 2500 + i, "close": 2501 + i,
                 "high": 2502 + i, "low": 2499 + i}
                for i in range(30)
            ]
        }
    )
    result = backtest_handler.handle_run_backtest("XAUUSD", 15, 5)
    note = result.get("result", {}).get("note", "")
    assert "Backtest executado com dados MT5 reais" in str(note)


def test_backtest_cai_em_simulacao_quando_indisponivel(monkeypatch, backtest_handler):
    """Com MT5 indisponível, backtest deve cair na simulação estrutural."""
    _set_mt5_available(monkeypatch, False)
    result = backtest_handler.handle_run_backtest("XAUUSD", 15, 5)
    note = result.get("result", {}).get("note", "")
    assert "simulação" in str(note).lower()
