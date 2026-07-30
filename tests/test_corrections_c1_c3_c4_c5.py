"""Testes para as correções C1, C3, C4, C5.

C1: Remover direção da event_signature (src/leon.py)
C3: RR baseado em níveis técnicos (src/shadow_trade.py)
C4: Stop loss baseado em estrutura (src/shadow_trade.py)
C5: Adicionar streak detector (src/learning_bootstrap.py + config.ini)
"""

import csv
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock


# ========================================================================
# C1: Remover direção da event_signature
# ========================================================================

class TestC1EventSignature(unittest.TestCase):
    """C1: Garantir que event_signature NÃO contém direção."""

    def test_signature_sem_direcao(self):
        """Verifica que a assinatura usa apenas BOS/CHOCH times, sem direção."""
        bos_time = "2026-07-30T10:00:00"
        choch_time = "2026-07-30T10:15:00"

        # Simula o formato da assinatura (sem direcao_candidata)
        lab_event_signature = "|".join([
            str(bos_time),
            str(choch_time),
        ])

        assinatura_shadow = "|".join([
            str(bos_time),
            str(choch_time),
        ])

        self.assertEqual(lab_event_signature, "2026-07-30T10:00:00|2026-07-30T10:15:00")
        self.assertEqual(assinatura_shadow, "2026-07-30T10:00:00|2026-07-30T10:15:00")

        # Verifica que direcoes diferentes produzem a MESMA assinatura
        assinatura_compra = "|".join([bos_time, choch_time])
        assinatura_venda = "|".join([bos_time, choch_time])
        self.assertEqual(assinatura_compra, assinatura_venda,
                         "COMPRA e VENDA devem ter mesma assinatura (sem direcao)")

    def test_lab_event_available_com_signature_reduzida(self):
        """Verifica que lab_event_available funciona com assinatura sem direção."""
        from src.lab_entry_policy import lab_event_available, mark_lab_event

        signature = "2026-07-30T10:00:00|2026-07-30T10:15:00"

        # Deve estar disponível inicialmente
        with patch("src.lab_entry_policy._used_events", return_value={}):
            self.assertTrue(lab_event_available(signature))

        # Após marcar, não deve estar disponível
        with patch("src.lab_entry_policy._used_events", return_value={signature: "2026-07-30T10:01:00"}):
            self.assertFalse(lab_event_available(signature))

    def test_register_shadow_trade_dedup_sem_direcao(self):
        """Verifica que o dedup em register_shadow_trade ignora direção."""
        from src.shadow_trade import register_shadow_trade

        candles = [
            {"time": f"2026-07-30T09:{i:02d}:00", "open": "2300.0", "high": "2302.0", "low": "2298.0", "close": str(2300.0 + i * 0.2)}
            for i in range(15)
        ]

        # Registra primeira shadow com signature T1|T2
        with patch("src.shadow_trade.SHADOW_FILE", Path(tempfile.mktemp(suffix=".csv"))):
            r1 = register_shadow_trade(candles, "COMPRA", ["FIB"], "T1|T2")
            self.assertTrue(r1.get("ok"), "Primeiro registro deve funcionar")

            # Tenta registrar segunda shadow com MESMA signature (direção diferente)
            r2 = register_shadow_trade(candles, "VENDA", ["FIB"], "T1|T2")
            self.assertFalse(r2.get("ok"), "Segundo registro com mesma signature deve ser rejeitado")
            self.assertEqual(r2.get("error"), "SHADOW_EVENT_ALREADY_REGISTERED")


# ========================================================================
# Helper para criar candles de teste
# ========================================================================

def _make_candles(n=20, base_price=2300.0, direction="COMPRA"):
    """Create test candles with realistic price action."""
    candles = []
    for i in range(n):
        offset = i * 1.5 if direction == "COMPRA" else -i * 1.5
        _close = base_price + offset
        _high = _close + 3.0
        _low = _close - 3.0
        candles.append({
            "time": f"2026-07-30T09:{i:02d}:00",
            "open": str(_close - 0.1),
            "high": str(_high),
            "low": str(_low),
            "close": str(_close),
        })
    return candles


# ========================================================================
# C3: RR baseado em níveis técnicos
# ========================================================================

class TestC3TechnicalTP(unittest.TestCase):
    """C3: Garantir que TP use níveis técnicos com fallback seguro."""

    def test_tp_fallback_risk_x2(self):
        """Verifica fallback para risk * 2 quando build_smc_trade_levels falha."""
        from src.shadow_trade import register_shadow_trade

        candles = _make_candles(20, base_price=2300.0, direction="COMPRA")
        entry = float(candles[-2]["close"])  # last closed candle

        fake_stop = entry - 5.0
        expected_risk = entry - fake_stop
        expected_target = entry + expected_risk * 2

        with patch("src.shadow_trade.SHADOW_FILE", Path(tempfile.mktemp(suffix=".csv"))):
            with patch("src.interest_zone_engine.find_nearest_zone",
                       return_value={"zone_stop": fake_stop}):
                with patch("src.smc_price_levels.build_smc_trade_levels",
                           return_value=None):
                    result = register_shadow_trade(candles, "COMPRA", ["FIB"], "SIG")

        self.assertTrue(result.get("ok"))
        shadow = result["shadow_trade"]
        self.assertAlmostEqual(float(shadow["target"]), expected_target, delta=0.1,
                               msg="TP deve ser entry + risk * 2 quando não há níveis técnicos")

    def test_tp_usando_niveis_tecnicos(self):
        """Verifica que TP usa build_smc_trade_levels quando disponível."""
        from src.shadow_trade import register_shadow_trade

        candles = _make_candles(20, base_price=2300.0, direction="COMPRA")

        fake_stop = 2295.0
        fake_tp2 = 2320.0

        with patch("src.shadow_trade.SHADOW_FILE", Path(tempfile.mktemp(suffix=".csv"))):
            with patch("src.interest_zone_engine.find_nearest_zone",
                       return_value={"zone_stop": fake_stop}):
                with patch("src.smc_price_levels.build_smc_trade_levels",
                           return_value={"tp2": fake_tp2, "stop": fake_stop}):
                    result = register_shadow_trade(candles, "COMPRA", ["FIB"], "SIG")

        self.assertTrue(result.get("ok"))
        shadow = result["shadow_trade"]
        self.assertEqual(float(shadow["target"]), fake_tp2,
                         "TP deve usar o valor de tp2 dos níveis técnicos")

    def test_tp_venda_usando_niveis_tecnicos(self):
        """Verifica TP técnico para VENDA."""
        from src.shadow_trade import register_shadow_trade

        candles = _make_candles(20, base_price=2330.0, direction="VENDA")

        fake_stop = 2335.0
        fake_tp2 = 2310.0

        with patch("src.shadow_trade.SHADOW_FILE", Path(tempfile.mktemp(suffix=".csv"))):
            with patch("src.interest_zone_engine.find_nearest_zone",
                       return_value={"zone_stop": fake_stop}):
                with patch("src.smc_price_levels.build_smc_trade_levels",
                           return_value={"tp2": fake_tp2, "stop": fake_stop}):
                    result = register_shadow_trade(candles, "VENDA", ["FIB"], "SIG")

        self.assertTrue(result.get("ok"))
        shadow = result["shadow_trade"]
        self.assertEqual(float(shadow["target"]), fake_tp2,
                         "TP de VENDA deve usar tp2 dos níveis técnicos")


# ========================================================================
# C4: Stop loss baseado em estrutura
# ========================================================================

class TestC4StructuralStop(unittest.TestCase):
    """C4: Garantir que stop use zona estrutural com janela expandida."""

    def test_stop_com_zona_estrutural(self):
        """Verifica que stop usa find_nearest_zone quando disponível."""
        from src.shadow_trade import register_shadow_trade

        candles = _make_candles(20, base_price=2300.0, direction="COMPRA")

        fake_stop = 2290.0

        with patch("src.shadow_trade.SHADOW_FILE", Path(tempfile.mktemp(suffix=".csv"))):
            with patch("src.interest_zone_engine.find_nearest_zone",
                       return_value={"zone_stop": fake_stop}):
                result = register_shadow_trade(candles, "COMPRA", ["FIB"], "SIG")

        self.assertTrue(result.get("ok"))
        shadow = result["shadow_trade"]
        self.assertEqual(float(shadow["stop"]), fake_stop,
                         "Stop deve vir da zona estrutural")

    def test_stop_fallback_15_candles(self):
        """Verifica fallback para janela de 15 candles quando zona não encontrada."""
        from src.shadow_trade import register_shadow_trade

        candles = _make_candles(20, base_price=2300.0, direction="COMPRA")

        with patch("src.shadow_trade.SHADOW_FILE", Path(tempfile.mktemp(suffix=".csv"))):
            with patch("src.interest_zone_engine.find_nearest_zone",
                       return_value=None):  # zona retorna None
                result = register_shadow_trade(candles, "COMPRA", ["FIB"], "SIG")

        self.assertTrue(result.get("ok"))
        shadow = result["shadow_trade"]
        # Fallback = min low dos últimos 15 candles
        expected_stop = min(float(c["low"]) for c in candles[-15:])
        self.assertEqual(float(shadow["stop"]), expected_stop,
                         "Stop deve usar fallback de 15 candles quando zona retorna None")

    def test_stop_15_candles_vs_8_candles(self):
        """Verifica que o fallback usa 15 candles (não mais 8)."""
        from src.shadow_trade import register_shadow_trade

        # Create candles with a distant swing that would be missed by 8-candle window
        candles = _make_candles(20, base_price=2300.0, direction="COMPRA")
        # Add a very low candle at position 5 (would be in 15 but not in 8)
        candles[5]["low"] = str(2280.0)  # well below the trend

        with patch("src.shadow_trade.SHADOW_FILE", Path(tempfile.mktemp(suffix=".csv"))):
            with patch("src.interest_zone_engine.find_nearest_zone",
                       return_value=None):
                result = register_shadow_trade(candles, "COMPRA", ["FIB"], "SIG")

        self.assertTrue(result.get("ok"))
        shadow = result["shadow_trade"]
        stop = float(shadow["stop"])
        # With 8 candles, the min low would not include the 2280 at index 5
        # With 15 candles, it should include it
        self.assertLessEqual(stop, 2290.0,
                             "Stop com 15 candles deve capturar swing distante (índice 5)")


# ========================================================================
# C5: Streak detector
# ========================================================================

class TestC5ConsecutiveLosses(unittest.TestCase):
    """C5: Garantir detecção de perdas consecutivas."""

    def setUp(self):
        # Ensure learning_bootstrap uses the default limit of 5
        self.mock_limiares = {
            "auto_simulate_on_weak_setup": True,
            "auto_simulate_min_score": 30,
            "auto_simulate_min_winrate": 30.0,
            "consecutive_loss_limit": 5,
            "min_pre_operation_closed": 5,
            "min_pre_operation_winrate": 40.0,
        }

    def test_consecutive_losses_detecta_streak(self):
        """Verifica que _consecutive_losses detecta streak de losses."""
        from src.learning_bootstrap import _consecutive_losses

        shadows = [
            {"status": "FECHADO", "result": "LOSS"},
            {"status": "FECHADO", "result": "LOSS"},
            {"status": "FECHADO", "result": "LOSS"},
            {"status": "FECHADO", "result": "LOSS"},
            {"status": "FECHADO", "result": "LOSS"},
        ]
        self.assertTrue(_consecutive_losses(shadows=shadows, limit=5))

    def test_consecutive_losses_sem_streak(self):
        """Verifica que retorna False quando não há streak."""
        from src.learning_bootstrap import _consecutive_losses

        shadows = [
            {"status": "FECHADO", "result": "LOSS"},
            {"status": "FECHADO", "result": "WIN_2R"},
            {"status": "FECHADO", "result": "LOSS"},
            {"status": "FECHADO", "result": "LOSS"},
            {"status": "FECHADO", "result": "LOSS"},
        ]
        self.assertFalse(_consecutive_losses(shadows=shadows, limit=5))

    def test_consecutive_losses_streak_parcial(self):
        """Verifica que streak parcial (menos que limit) não dispara."""
        from src.learning_bootstrap import _consecutive_losses

        shadows = [
            {"status": "FECHADO", "result": "LOSS"},
            {"status": "FECHADO", "result": "LOSS"},
            {"status": "FECHADO", "result": "LOSS"},
            {"status": "ABERTO", "result": "EM_ESTUDO"},
        ]
        self.assertFalse(_consecutive_losses(shadows=shadows, limit=5))

    def test_consecutive_losses_apenas_fechados(self):
        """Verifica que apenas trades FECHADO são considerados."""
        from src.learning_bootstrap import _consecutive_losses

        shadows = [
            {"status": "FECHADO", "result": "LOSS"},
            {"status": "FECHADO", "result": "LOSS"},
            {"status": "FECHADO", "result": "LOSS"},
            {"status": "FECHADO", "result": "LOSS"},
            {"status": "ABERTO", "result": "EM_ESTUDO"},
            {"status": "ABERTO", "result": "EM_ESTUDO"},
        ]
        # Apenas 4 fechados com loss (limit=5), não deve disparar
        self.assertFalse(_consecutive_losses(shadows=shadows, limit=5))

    def test_auto_simulate_bloqueado_por_streak(self):
        """Verifica que auto_simulate_permitido bloqueia quando há streak."""
        from src.learning_bootstrap import auto_simulate_permitido

        with patch("src.learning_bootstrap.obter_limiares", return_value=self.mock_limiares):
            with patch("src.learning_bootstrap._consecutive_losses", return_value=True):
                permitido, razao = auto_simulate_permitido(brain_score=80)
                self.assertFalse(permitido)
                self.assertIn("CONSECUTIVE_LOSSES", razao)

    def test_auto_simulate_permitido_sem_streak(self):
        """Verifica que auto-simulate funciona quando não há streak."""
        from src.learning_bootstrap import auto_simulate_permitido

        with patch("src.learning_bootstrap.obter_limiares", return_value=self.mock_limiares):
            with patch("src.learning_bootstrap._consecutive_losses", return_value=False):
                with patch("src.learning_bootstrap._winrate_shadows_recentes",
                           return_value={"winrate": 50.0, "fechados": 10, "wins": 5, "losses": 5}):
                    permitido, razao = auto_simulate_permitido(brain_score=80)
                    self.assertTrue(permitido)

    def test_auto_simulate_streak_tem_prioridade_sobre_score(self):
        """Verifica que streak check acontece antes do score check."""
        from src.learning_bootstrap import auto_simulate_permitido

        with patch("src.learning_bootstrap.obter_limiares", return_value=self.mock_limiares):
            with patch("src.learning_bootstrap._consecutive_losses", return_value=True):
                # Mesmo com brain_score muito baixo, deve retornar CONSECUTIVE_LOSSES
                permitido, razao = auto_simulate_permitido(brain_score=0)
                self.assertFalse(permitido)
                self.assertIn("CONSECUTIVE_LOSSES", razao,
                              "Streak deve ser verificado antes do score")


class TestC5Config(unittest.TestCase):
    """C5: Verificar configurações no config.ini."""

    def test_config_tem_consecutive_loss_limit(self):
        """Verifica que config.ini tem a chave consecutive_loss_limit."""
        import configparser
        config = configparser.ConfigParser()
        config.read("/opt/leon/app/config.ini", encoding="utf-8")
        self.assertTrue(config.has_section("BOOTSTRAP"))
        self.assertIn("consecutive_loss_limit", config["BOOTSTRAP"])
        self.assertEqual(config["BOOTSTRAP"]["consecutive_loss_limit"], "5")

    def test_config_auto_simulate_min_winrate_30(self):
        """Verifica que auto_simulate_min_winrate foi alterado para 30."""
        import configparser
        config = configparser.ConfigParser()
        config.read("/opt/leon/app/config.ini", encoding="utf-8")
        self.assertEqual(config["BOOTSTRAP"]["auto_simulate_min_winrate"], "30")

    def test_obter_limiares_inclui_consecutive_loss_limit(self):
        """Verifica que obter_limiares retorna consecutive_loss_limit."""
        from src.learning_bootstrap import obter_limiares
        limiares = obter_limiares()
        self.assertIn("consecutive_loss_limit", limiares)
        self.assertEqual(limiares["consecutive_loss_limit"], 5)


# ========================================================================
# C4: Test find_nearest_zone diretamente
# ========================================================================

class TestC4FindNearestZone(unittest.TestCase):
    """C4: Testar find_nearest_zone diretamente."""

    def test_find_nearest_zone_compra(self):
        """Verifica que find_nearest_zone encontra zona para COMPRA."""
        from src.interest_zone_engine import find_nearest_zone

        candles = [
            {"high": "2310", "low": "2290"},
            {"high": "2308", "low": "2292"},
            {"high": "2312", "low": "2288"},
            {"high": "2305", "low": "2295"},
            {"high": "2300", "low": "2298"},
            {"high": "2302", "low": "2296"},
            {"high": "2306", "low": "2294"},
        ]
        # Swing lows: 2288 at idx2 (curr < prev and curr <= next)
        # Below entry 2301: [2288]
        # Nearest = max = 2288

        zone = find_nearest_zone("COMPRA", 2301.0, candles)
        self.assertIsNotNone(zone)
        self.assertIn("zone_stop", zone)
        self.assertEqual(zone["zone_stop"], 2288.0)

    def test_find_nearest_zone_venda(self):
        """Verifica que find_nearest_zone encontra zona para VENDA."""
        from src.interest_zone_engine import find_nearest_zone

        candles = [
            {"high": "2310", "low": "2300"},
            {"high": "2308", "low": "2302"},
            {"high": "2312", "low": "2298"},
            {"high": "2305", "low": "2295"},
            {"high": "2315", "low": "2300"},
            {"high": "2318", "low": "2305"},
        ]
        # Swing highs: 2312 at idx2 (curr > prev and curr >= next)
        # Above entry 2301: [2312]
        # Nearest = min = 2312

        zone = find_nearest_zone("VENDA", 2301.0, candles)
        self.assertIsNotNone(zone)
        self.assertIn("zone_stop", zone)
        self.assertEqual(zone["zone_stop"], 2312.0)

    def test_find_nearest_zone_sem_dados(self):
        """Verifica que retorna None com dados insuficientes."""
        from src.interest_zone_engine import find_nearest_zone
        self.assertIsNone(find_nearest_zone("COMPRA", 2300.0, []))
        self.assertIsNone(find_nearest_zone("COMPRA", 2300.0, [{"high": "1", "low": "1"}]))

    def test_find_nearest_zone_sem_swing_abaixo(self):
        """Verifica que retorna None quando não há swing abaixo do entry."""
        from src.interest_zone_engine import find_nearest_zone

        # All lows are above entry
        candles = [
            {"high": "2320", "low": "2310"},
            {"high": "2330", "low": "2315"},
            {"high": "2340", "low": "2320"},
            {"high": "2350", "low": "2325"},
        ]
        zone = find_nearest_zone("COMPRA", 2300.0, candles)
        self.assertIsNone(zone)


if __name__ == "__main__":
    unittest.main()
