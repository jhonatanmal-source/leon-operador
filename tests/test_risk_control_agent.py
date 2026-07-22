import math

import pytest

from src.risk_control_agent import (
    _normalizar_lote,
    calcular_limite_perda_diaria,
    calcular_plano_risco,
)


# =============================================================================
# calcular_limite_perda_diaria — contract tests
# =============================================================================

class TestLimitePerdaDiaria:

    def test_risco_normal(self):
        result = calcular_limite_perda_diaria(
            saldo_atual=10000, resultado_realizado=-50, resultado_aberto=-20, limite_percentual=2.0
        )
        assert result["ok"] is True
        assert result["approved"] is True
        assert result["reason"] == "DAILY_LOSS_LIMIT_OK"

    def test_limite_diario_atingido(self):
        result = calcular_limite_perda_diaria(
            saldo_atual=9800, resultado_realizado=-200, resultado_aberto=0, limite_percentual=2.0
        )
        assert result["ok"] is True
        assert result["approved"] is False
        assert result["reason"] == "DAILY_LOSS_LIMIT_REACHED"

    def test_saldo_invalido(self):
        result = calcular_limite_perda_diaria(
            saldo_atual=0, resultado_realizado=0, resultado_aberto=0, limite_percentual=2.0
        )
        assert result["ok"] is False
        assert result["approved"] is False
        assert result["error"] == "INVALID_STARTING_BALANCE"

    def test_saldo_negativo(self):
        result = calcular_limite_perda_diaria(
            saldo_atual=-100, resultado_realizado=0, resultado_aberto=0, limite_percentual=2.0
        )
        assert result["ok"] is False

    def test_lucro_nao_bloqueia(self):
        result = calcular_limite_perda_diaria(
            saldo_atual=10200, resultado_realizado=200, resultado_aberto=50, limite_percentual=2.0
        )
        assert result["ok"] is True
        assert result["approved"] is True

    def test_limite_zero_rejeitado(self):
        result = calcular_limite_perda_diaria(
            saldo_atual=10000, resultado_realizado=0, resultado_aberto=0, limite_percentual=0.0
        )
        assert result["ok"] is False
        assert result["error"] == "INVALID_LOSS_LIMIT"

    def test_limite_negativo_rejeitado(self):
        result = calcular_limite_perda_diaria(
            saldo_atual=10000, resultado_realizado=0, resultado_aberto=0, limite_percentual=-1.0
        )
        assert result["ok"] is False
        assert result["error"] == "INVALID_LOSS_LIMIT"

    def test_saldo_infinito_rejeitado(self):
        result = calcular_limite_perda_diaria(
            saldo_atual=float("inf"), resultado_realizado=0, resultado_aberto=0, limite_percentual=2.0
        )
        assert result["ok"] is False
        assert result["error"] == "INVALID_STARTING_BALANCE"

    def test_saldo_nan_rejeitado(self):
        result = calcular_limite_perda_diaria(
            saldo_atual=float("nan"), resultado_realizado=0, resultado_aberto=0, limite_percentual=2.0
        )
        assert result["ok"] is False
        assert result["error"] == "INVALID_STARTING_BALANCE"

    def test_saldo_neg_infinito_rejeitado(self):
        result = calcular_limite_perda_diaria(
            saldo_atual=float("-inf"), resultado_realizado=0, resultado_aberto=0, limite_percentual=2.0
        )
        assert result["ok"] is False
        assert result["error"] == "INVALID_STARTING_BALANCE"

    def test_resultado_realizado_nao_finito_rejeitado(self):
        result = calcular_limite_perda_diaria(
            saldo_atual=10000, resultado_realizado=float("nan"), resultado_aberto=0, limite_percentual=2.0
        )
        assert result["ok"] is False
        assert result["error"] == "INVALID_RESULT"

    def test_resultado_aberto_nao_finito_rejeitado(self):
        result = calcular_limite_perda_diaria(
            saldo_atual=10000, resultado_realizado=0, resultado_aberto=float("inf"), limite_percentual=2.0
        )
        assert result["ok"] is False
        assert result["error"] == "INVALID_RESULT"

    def test_exposicao_existente_considerada(self):
        result = calcular_limite_perda_diaria(
            saldo_atual=10000, resultado_realizado=-100, resultado_aberto=-50, limite_percentual=1.0
        )
        assert result["approved"] is False

    def test_saldo_muito_grande(self):
        result = calcular_limite_perda_diaria(
            saldo_atual=1e12, resultado_realizado=-1e9, resultado_aberto=0, limite_percentual=2.0
        )
        assert result["ok"] is True
        assert result["approved"] is True

    def test_perda_zero_com_limite_positivo(self):
        result = calcular_limite_perda_diaria(
            saldo_atual=10000, resultado_realizado=0, resultado_aberto=0, limite_percentual=1.0
        )
        assert result["ok"] is True
        assert result["approved"] is True
        assert result["reason"] == "DAILY_LOSS_LIMIT_OK"


# =============================================================================
# calcular_plano_risco — contract tests
# =============================================================================

class TestPlanoRisco:

    MIN_PRE_OP = {
        "entrada": "2000.0",
        "stop": "1990.0",
        "metodo_risco": "managed",
        "context_mode": "TENDENCIA",
    }

    def test_plano_valido(self):
        result = calcular_plano_risco(dict(self.MIN_PRE_OP), saldo=10000)
        assert result["ok"] is True
        assert result["approved"] in (True, False)

    def test_stop_zero_rejeitado(self):
        pre = dict(self.MIN_PRE_OP)
        pre["entrada"] = "2000.0"
        pre["stop"] = "2000.0"
        result = calcular_plano_risco(pre, saldo=10000)
        assert result["ok"] is False
        assert result["error"] == "INVALID_STOP_DISTANCE"

    def test_stop_acima_entrada_eh_valido_para_venda(self):
        pre = dict(self.MIN_PRE_OP)
        pre["entrada"] = "2000.0"
        pre["stop"] = "2010.0"
        result = calcular_plano_risco(pre, saldo=10000)
        assert result["ok"] is True
        assert result["stop_distance"] == 10.0

    def test_stop_valido_compra(self):
        pre = dict(self.MIN_PRE_OP)
        pre["entrada"] = "2000.0"
        pre["stop"] = "1990.0"
        result = calcular_plano_risco(pre, saldo=10000)
        assert result["ok"] is True
        assert result["stop_distance"] == 10.0

    def test_stop_valido_venda(self):
        pre = dict(self.MIN_PRE_OP)
        pre["entrada"] = "2000.0"
        pre["stop"] = "2010.0"
        result = calcular_plano_risco(pre, saldo=10000)
        assert result["ok"] is True
        assert result["stop_distance"] == 10.0

    def test_entrada_igual_stop_rejeitado(self):
        pre = dict(self.MIN_PRE_OP)
        pre["entrada"] = "2000.0"
        pre["stop"] = "2000.0"
        result = calcular_plano_risco(pre, saldo=10000)
        assert result["ok"] is False
        assert result["error"] == "INVALID_STOP_DISTANCE"

    def test_saldo_zero_rejeitado(self):
        result = calcular_plano_risco(self.MIN_PRE_OP, saldo=0)
        assert result["ok"] is False
        assert result["error"] == "INVALID_BALANCE"

    def test_saldo_negativo_rejeitado(self):
        result = calcular_plano_risco(self.MIN_PRE_OP, saldo=-500)
        assert result["ok"] is False
        assert result["error"] == "INVALID_BALANCE"

    def test_saldo_infinito_rejeitado(self):
        result = calcular_plano_risco(self.MIN_PRE_OP, saldo=float("inf"))
        assert result["ok"] is False
        assert result["error"] == "INVALID_BALANCE"

    def test_saldo_nan_rejeitado(self):
        result = calcular_plano_risco(self.MIN_PRE_OP, saldo=float("nan"))
        assert result["ok"] is False
        assert result["error"] == "INVALID_BALANCE"

    def test_entrada_nan_rejeitada(self):
        pre = dict(self.MIN_PRE_OP)
        pre["entrada"] = "nan"
        result = calcular_plano_risco(pre, saldo=10000)
        assert result["ok"] is False
        assert result["error"] == "INVALID_PRE_OPERATION_PRICE"

    def test_stop_nan_rejeitado(self):
        pre = dict(self.MIN_PRE_OP)
        pre["stop"] = "nan"
        result = calcular_plano_risco(pre, saldo=10000)
        assert result["ok"] is False
        assert result["error"] == "INVALID_PRE_OPERATION_PRICE"

    def test_sem_entrada_rejeitado(self):
        result = calcular_plano_risco({"stop": "1990"}, saldo=10000)
        assert result["ok"] is False
        assert result["error"] == "INVALID_PRE_OPERATION_PRICE"

    def test_sem_stop_rejeitado(self):
        result = calcular_plano_risco({"entrada": "2000"}, saldo=10000)
        assert result["ok"] is False
        assert result["error"] == "INVALID_PRE_OPERATION_PRICE"

    def test_lote_abaixo_minimo_bloqueia_quando_excede_risco(self):
        pre = dict(self.MIN_PRE_OP)
        pre["stop"] = "1900.0"
        result = calcular_plano_risco(pre, saldo=100)
        assert result["ok"] is False
        assert result["error"] == "LOT_BELOW_MINIMUM_EXCEEDS_RISK"

    # --- itens 1-5: normalizacao conservadora (especificacao B04-02 Fase 5) ---

    def test_item1_lote_016_step_01_resultado_01(self):
        pre = dict(self.MIN_PRE_OP)
        pre["entrada"] = "2000.0"
        pre["stop"] = "1900.0"
        result = calcular_plano_risco(pre, saldo=32000, especificacoes={"contract_size": 100, "volume_step": 0.01})
        assert result["ok"] is True
        assert result["calculated_lot"] == 0.016
        assert result["lot"] == 0.01

    def test_item2_lote_019_step_01_resultado_01(self):
        pre = dict(self.MIN_PRE_OP)
        pre["entrada"] = "2000.0"
        pre["stop"] = "1900.0"
        result = calcular_plano_risco(pre, saldo=38000, especificacoes={"contract_size": 100, "volume_step": 0.01})
        assert result["ok"] is True
        assert result["calculated_lot"] == 0.019
        assert result["lot"] == 0.01

    def test_item3_lote_020_step_01_resultado_02(self):
        pre = dict(self.MIN_PRE_OP)
        pre["entrada"] = "2000.0"
        pre["stop"] = "1900.0"
        result = calcular_plano_risco(pre, saldo=40000, especificacoes={"contract_size": 100, "volume_step": 0.01})
        assert result["ok"] is True
        assert result["lot"] == 0.02
        assert result["calculated_lot"] == 0.02

    def test_item4_normalizacao_step01(self):
        assert _normalizar_lote(0.26, 0.1) == 0.2

    def test_item5_normalizacao_step10(self):
        assert _normalizar_lote(1.9, 1.0) == 1.0

    def test_item13_lote_nunca_maior_que_calculado_exceto_min_lot(self):
        pre = dict(self.MIN_PRE_OP)
        pre["entrada"] = "2000.0"
        pre["stop"] = "1900.0"
        result = calcular_plano_risco(pre, saldo=50000, especificacoes={"contract_size": 100, "volume_step": 0.01})
        if result["ok"] and result["lot"] > result["volume_min"]:
            assert result["lot"] <= result["calculated_lot"]

    def test_volume_step_zero_rejeitado(self):
        result = calcular_plano_risco(self.MIN_PRE_OP, saldo=10000, especificacoes={"volume_step": 0})
        assert result["ok"] is False
        assert result["error"] == "INVALID_VOLUME_STEP"

    def test_volume_step_negativo_rejeitado(self):
        result = calcular_plano_risco(self.MIN_PRE_OP, saldo=10000, especificacoes={"volume_step": -0.01})
        assert result["ok"] is False
        assert result["error"] == "INVALID_VOLUME_STEP"

    def test_volume_step_nan_rejeitado(self):
        result = calcular_plano_risco(self.MIN_PRE_OP, saldo=10000, especificacoes={"volume_step": float("nan")})
        assert result["ok"] is False
        assert result["error"] == "INVALID_VOLUME_STEP"

    def test_volume_min_maior_que_max_rejeitado(self):
        result = calcular_plano_risco(self.MIN_PRE_OP, saldo=10000, especificacoes={"volume_min": 10, "volume_max": 1})
        assert result["ok"] is False
        assert result["error"] == "INVALID_VOLUME_LIMITS"

    def test_lote_minimo_dentro_risco_permitido(self):
        pre = dict(self.MIN_PRE_OP)
        pre["entrada"] = "2000.0"
        pre["stop"] = "1950.0"
        result = calcular_plano_risco(pre, saldo=100000,
                                       especificacoes={"contract_size": 100, "volume_step": 0.01, "volume_min": 0.01, "volume_max": 100})
        assert result["ok"] is True

    def test_lote_minimo_excedendo_risco_bloqueado(self):
        pre = dict(self.MIN_PRE_OP)
        pre["entrada"] = "2000.0"
        pre["stop"] = "1999.0"
        result = calcular_plano_risco(pre, saldo=50,
                                       especificacoes={"contract_size": 100, "volume_step": 0.01, "volume_min": 0.01, "volume_max": 100})
        assert result["ok"] is False
        assert result["error"] == "LOT_BELOW_MINIMUM_EXCEEDS_RISK"

    def test_lote_maximo_aplicado_risco_recalculado(self):
        pre = dict(self.MIN_PRE_OP)
        pre["entrada"] = "2000.0"
        pre["stop"] = "1995.0"
        result = calcular_plano_risco(pre, saldo=1000000,
                                       especificacoes={"contract_size": 100, "volume_step": 0.01, "volume_max": 1.0})
        assert result["ok"] is True
        assert result["lot"] <= 1.0
        assert result["estimated_risk_percent"] <= 1.0

    def test_risco_efetivo_apos_normalizacao_nao_excede_maximo(self):
        for saldo in [1000, 5000, 10000, 50000]:
            pre = dict(self.MIN_PRE_OP)
            pre["entrada"] = "2000.0"
            pre["stop"] = "1950.0"
            result = calcular_plano_risco(pre, saldo=saldo,
                                           especificacoes={"contract_size": 100, "volume_step": 0.01})
            if result["ok"]:
                assert result["estimated_risk_percent"] <= 1.0, \
                    f"saldo={saldo}: risk={result['estimated_risk_percent']}% > 1.0%"

    def test_precisao_decimal_estavel(self):
        pre = dict(self.MIN_PRE_OP)
        pre["entrada"] = "2000.0"
        pre["stop"] = "1950.0"
        result = calcular_plano_risco(pre, saldo=10000,
                                       especificacoes={"contract_size": 100, "volume_step": 0.01})
        if result["ok"]:
            lot_str = f"{result['lot']:.10f}"
            assert "999999" not in lot_str and "000001" not in lot_str

    def test_lote_com_especificacoes_personalizadas(self):
        pre = dict(self.MIN_PRE_OP)
        pre["entrada"] = "2000.0"
        pre["stop"] = "1900.0"
        esp = {
            "contract_size": 100,
            "volume_step": 0.1,
            "volume_min": 0.1,
            "volume_max": 10.0,
        }
        result = calcular_plano_risco(pre, saldo=10000, especificacoes=esp)
        assert result["ok"] is True
        assert result["contract_size"] == 100
        assert result["volume_step"] == 0.1
        assert result["volume_min"] == 0.01  # min(config["min_lot"], esp["volume_min"])
        assert result["volume_max"] == 0.1  # min(config["max_lot"], esp["volume_max"])

    def test_sem_chamada_real_mt5(self):
        pre = dict(self.MIN_PRE_OP)
        result = calcular_plano_risco(pre, saldo=10000)
        assert result["ok"] is True

    def test_sem_order_send(self):
        pre = dict(self.MIN_PRE_OP)
        result = calcular_plano_risco(pre, saldo=10000)
        assert "order_send" not in result

    def test_contrato_ok_approved_mantem_campos_essenciais(self):
        result = calcular_plano_risco(self.MIN_PRE_OP, saldo=10000)
        if result["ok"]:
            assert "lot" in result
            assert "stop_distance" in result
            assert "risk_value" in result
            assert result["lot"] > 0
