import json

import pytest

import src.ftmo_guard as ftmo_guard
from src.ftmo_guard import (
    avaliar_conformidade_ftmo,
    registrar_perfil_conta,
    _ftmo_config,
)


@pytest.fixture(autouse=True)
def _isolar_estado(tmp_path, monkeypatch):
    """Isola o arquivo de contas FTMO em tmp_path (nunca toca data/ real)."""
    fake = tmp_path / "ftmo_accounts.json"
    monkeypatch.setattr(ftmo_guard, "DATA_DIR", tmp_path)
    monkeypatch.setattr(ftmo_guard, "FTMO_ACCOUNTS_FILE", fake)
    return fake


def _cfg(**over):
    base = {
        "enabled": True,
        "daily_loss_percent": 5.0,
        "max_drawdown_percent": 10.0,
        "daily_buffer_percent": 2.0,
        "drawdown_buffer_percent": 6.0,
        "min_trading_days": 4,
        "profit_target_percent": 8.0,
    }
    base.update(over)
    return base


# =============================================================================
# avaliar_conformidade_ftmo — calculo puro (percentual, independe do tamanho)
# =============================================================================

class TestConformidadePura:

    def test_conta_saudavel_aprovada(self):
        r = avaliar_conformidade_ftmo(
            baseline_balance=100000,
            equity_atual=100500,
            resultado_dia=500,
            config=_cfg(),
        )
        assert r["ok"] is True
        assert r["approved"] is True
        assert r["reason"] == "FTMO_GUARD_OK"
        assert r["drawdown_percent"] == 0.0

    def test_perda_diaria_atinge_buffer_bloqueia(self):
        # 100k, perda de 2000 = 2% do dia = buffer interno
        r = avaliar_conformidade_ftmo(
            baseline_balance=100000,
            equity_atual=98000,
            resultado_dia=-2000,
            config=_cfg(),
        )
        assert r["approved"] is False
        assert "DAILY_LOSS_BUFFER_REACHED" in r["reasons"]

    def test_drawdown_atinge_buffer_bloqueia(self):
        # equity 6% abaixo do baseline = drawdown buffer
        r = avaliar_conformidade_ftmo(
            baseline_balance=100000,
            equity_atual=94000,
            resultado_dia=-100,
            config=_cfg(),
        )
        assert r["approved"] is False
        assert "DRAWDOWN_BUFFER_REACHED" in r["reasons"]

    def test_tamanho_pequeno_mesma_regra_percentual(self):
        # conta 10k: 2% dia = 200 -> deve bloquear igual a conta 100k
        r = avaliar_conformidade_ftmo(
            baseline_balance=10000,
            equity_atual=9800,
            resultado_dia=-200,
            config=_cfg(),
        )
        assert r["approved"] is False
        assert "DAILY_LOSS_BUFFER_REACHED" in r["reasons"]
        assert r["daily_loss_percent"] == pytest.approx(2.0)

    def test_tamanho_grande_mesma_regra_percentual(self):
        # conta 200k: 2% dia = 4000 -> bloqueia; 3000 (1.5%) nao
        ok = avaliar_conformidade_ftmo(
            baseline_balance=200000,
            equity_atual=197000,
            resultado_dia=-3000,
            config=_cfg(),
        )
        assert ok["approved"] is True
        bloq = avaliar_conformidade_ftmo(
            baseline_balance=200000,
            equity_atual=196000,
            resultado_dia=-4000,
            config=_cfg(),
        )
        assert bloq["approved"] is False

    def test_violacao_real_ftmo_daily_sinalizada(self):
        r = avaliar_conformidade_ftmo(
            baseline_balance=100000,
            equity_atual=94500,
            resultado_dia=-5500,  # 5.5% > 5% FTMO
            config=_cfg(),
        )
        assert r["approved"] is False
        assert r["ftmo_daily_violated"] is True
        assert "FTMO_DAILY_LIMIT_VIOLATED" in r["reasons"]

    def test_violacao_real_drawdown_sinalizada(self):
        r = avaliar_conformidade_ftmo(
            baseline_balance=100000,
            equity_atual=89000,  # 11% drawdown > 10% FTMO
            resultado_dia=-500,
            config=_cfg(),
        )
        assert r["approved"] is False
        assert r["ftmo_drawdown_violated"] is True
        assert "FTMO_MAX_DRAWDOWN_VIOLATED" in r["reasons"]

    def test_lucro_no_dia_nao_conta_como_perda(self):
        r = avaliar_conformidade_ftmo(
            baseline_balance=100000,
            equity_atual=103000,
            resultado_dia=3000,
            config=_cfg(),
        )
        assert r["approved"] is True
        assert r["daily_loss_percent"] == 0.0

    def test_baseline_invalido_rejeitado(self):
        r = avaliar_conformidade_ftmo(0, 100, -1, config=_cfg())
        assert r["ok"] is False
        assert r["error"] == "INVALID_BASELINE_BALANCE"

    def test_equity_nao_finito_rejeitado(self):
        r = avaliar_conformidade_ftmo(
            100000, float("nan"), -1, config=_cfg()
        )
        assert r["ok"] is False
        assert r["error"] == "INVALID_EQUITY"

    def test_resultado_dia_nao_finito_rejeitado(self):
        r = avaliar_conformidade_ftmo(
            100000, 100000, float("inf"), config=_cfg()
        )
        assert r["ok"] is False
        assert r["error"] == "INVALID_DAILY_RESULT"


# =============================================================================
# registrar_perfil_conta — deteccao automatica + baseline por login
# =============================================================================

class TestPerfilConta:

    def test_primeiro_connect_grava_baseline(self, _isolar_estado):
        perfil = registrar_perfil_conta(
            login=12345, server="FTMO-Demo", currency="USD",
            balance=100000.0, trade_mode_demo=True,
        )
        assert perfil["login"] == "12345"
        assert perfil["baseline_balance"] == 100000.0
        assert perfil["is_demo"] is True
        # persistido
        data = json.loads(_isolar_estado.read_text(encoding="utf-8"))
        assert "12345" in data

    def test_segundo_connect_preserva_baseline(self):
        registrar_perfil_conta(
            login=999, server="FTMO", currency="USD",
            balance=25000.0, trade_mode_demo=True,
        )
        # balance mudou (lucro), baseline deve permanecer o original
        perfil = registrar_perfil_conta(
            login=999, server="FTMO", currency="USD",
            balance=27000.0, trade_mode_demo=True,
        )
        assert perfil["baseline_balance"] == 25000.0

    def test_multiplas_contas_tamanhos_diferentes(self):
        p10k = registrar_perfil_conta(
            login=1, server="S", currency="USD",
            balance=10000.0, trade_mode_demo=True,
        )
        p100k = registrar_perfil_conta(
            login=2, server="S", currency="USD",
            balance=100000.0, trade_mode_demo=True,
        )
        assert p10k["baseline_balance"] == 10000.0
        assert p100k["baseline_balance"] == 100000.0

    def test_login_none_retorna_none(self):
        assert registrar_perfil_conta(
            login=None, server="S", currency="USD",
            balance=100.0, trade_mode_demo=True,
        ) is None

    def test_balance_invalido_retorna_none(self):
        assert registrar_perfil_conta(
            login=5, server="S", currency="USD",
            balance=float("nan"), trade_mode_demo=True,
        ) is None


# =============================================================================
# Config — defaults FTMO padrao
# =============================================================================

class TestConfig:

    def test_defaults_percentuais_ftmo(self):
        cfg = _ftmo_config()
        assert cfg["daily_loss_percent"] == 5.0
        assert cfg["max_drawdown_percent"] == 10.0
        # buffers internos mais conservadores
        assert cfg["daily_buffer_percent"] <= cfg["daily_loss_percent"]
        assert cfg["drawdown_buffer_percent"] <= cfg["max_drawdown_percent"]
