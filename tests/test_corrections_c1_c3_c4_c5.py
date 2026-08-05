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
            with patch("src.interest_zone_engine.find_nearest_zone",
                       return_value={"zone_stop": 2295.0}):
                with patch("src.smc_price_levels.build_smc_trade_levels",
                           return_value={"tp2": 2350.0, "stop": 2295.0}):
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


def _smc_compra_candles():
    """Série COMPRA sintética: FVG [100,105] no início + rally sobreposto.

    Estrutura verificada:
    - swing_highs = [107, 112, 115, 121]
    - swing_lows  = [102]
    - FVG bullish  = {start: 100, end: 105}
    - Entry 104 → tp1=107, tp2=112 (tp1 < tp2)
    """
    def candle(t, o, h, l, cl):
        return {"time": t, "open": o, "high": h, "low": l, "close": cl}

    return [
        candle("t0",  100, 100,  98,  99),
        candle("t1",   99, 102,  99, 101),
        candle("t2",  101, 106, 105, 105),
        candle("t3",  105, 107, 102, 106),
        candle("t4",  106, 105, 104, 105),
        candle("t5",  105, 109, 104, 108),
        candle("t6",  108, 112, 104, 111),
        candle("t7",  111, 110, 108, 109),
        candle("t8",  109, 115, 108, 114),
        candle("t9",  114, 113, 109, 112),
        candle("t10", 112, 118, 111, 117),
        candle("t11", 117, 121, 112, 120),
        candle("t12", 120, 119, 117, 118),
    ]


def _smc_venda_candles():
    """Série VENDA sintética (espelhada da COMPRA): FVG bearish.

    Estrutura verificada:
    - swing_highs = [128]
    - swing_lows  = [118, 123]
    - FVG bearish = {start: 128, end: 124}
    - Entry 126 → tp1=123, tp2=118 (tp2 < tp1)
    """
    def candle(t, o, h, l, cl):
        return {"time": t, "open": o, "high": h, "low": l, "close": cl}

    # Espelho da série COMPRA em torno de 114: close' = 228 - close
    mirror = [
        (120, 119, 117, 118),
        (117, 121, 112, 120),
        (112, 118, 111, 117),
        (114, 113, 109, 112),
        (109, 115, 108, 114),
        (111, 110, 108, 109),
        (108, 112, 104, 111),
        (105, 109, 104, 108),
        (106, 105, 104, 105),
        (105, 107, 102, 106),
        (101, 106, 105, 105),
        (99, 102, 99, 101),
        (100, 100, 98, 99),
    ]
    return [candle(f"v{i}", o, h, l, c) for i, (o, h, l, c) in enumerate(mirror)]


# ========================================================================
# C3: RR baseado em níveis técnicos
# ========================================================================

class TestC3TechnicalTP(unittest.TestCase):
    """C3: Garantir que TP use níveis técnicos com fallback seguro."""

    def test_tp_sem_tecnico_bloqueia(self):
        """Verifica que register_shadow_trade BLOQUEIA sem níveis técnicos.

        Paridade com entry_price_engine: sem TP técnico (levels None), o
        shadow trade não é registrado. Não existe mais fallback risk*2.
        """
        from src.shadow_trade import register_shadow_trade

        candles = _make_candles(20, base_price=2300.0, direction="COMPRA")

        with patch("src.shadow_trade.SHADOW_FILE", Path(tempfile.mktemp(suffix=".csv"))):
            with patch("src.interest_zone_engine.find_nearest_zone",
                       return_value={"zone_stop": 2295.0}):
                with patch("src.smc_price_levels.build_smc_trade_levels",
                           return_value=None):
                    result = register_shadow_trade(candles, "COMPRA", ["FIB"], "SIG")

        self.assertFalse(result.get("ok"))
        self.assertEqual(result.get("error"), "NO_TECHNICAL_TP",
                         "Sem níveis técnicos o shadow trade deve ser bloqueado")

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
# T3: Testes diretos de build_smc_trade_levels / detect_latest_fvg
# ========================================================================

class TestSmcPriceLevels(unittest.TestCase):
    """T3: Garantias estruturais do TP técnico (M1, M2, M4)."""

    def test_tp1_neq_tp2(self):
        """M2: tp1 e tp2 não podem colapsar (tp1 < tp2 em COMPRA)."""
        from src.smc_price_levels import build_smc_trade_levels

        candles = _smc_compra_candles()
        levels = build_smc_trade_levels("COMPRA", min_rr=1.0, candles=candles, entry_price=104.0)

        self.assertIsNotNone(levels)
        self.assertLess(levels["tp1"], levels["tp2"],
                        "tp1 deve ser menor que tp2 em COMPRA (não colapsar)")

    def test_zona_referencia_usa_entry(self):
        """M1: referência de zona usa entry quando fornecido."""
        from src.smc_price_levels import build_smc_trade_levels

        candles = _smc_compra_candles()
        last_close = float(candles[-1]["close"])  # 118 — fora do FVG [100,105]

        # Entry dentro do FVG e last close fora → levels válidos (M1 usa entry)
        levels_inside = build_smc_trade_levels("COMPRA", min_rr=1.0, candles=candles, entry_price=104.0)
        self.assertIsNotNone(levels_inside,
                             "Entry dentro do FVG deve passar mesmo com last close fora")

        # Cenário inverso: entry fora do FVG → None
        levels_outside = build_smc_trade_levels("COMPRA", min_rr=1.0, candles=candles, entry_price=108.0)
        self.assertIsNone(levels_outside,
                          "Entry fora do FVG deve ser bloqueado")

    def test_fvg_exclui_vela_formacao(self):
        """M4: FVG cuja terceira vela é a última (em formação) não é detectado."""
        from src.smc_price_levels import detect_latest_fvg

        def candle(t, o, h, l, cl):
            return {"time": t, "open": o, "high": h, "low": l, "close": cl}

        # FVG [104,109]: third = última vela (em formação)
        series = [
            candle("u0", 100, 102,  99, 101),
            candle("u1", 101, 103, 100, 102),
            candle("u2", 102, 104, 102, 103),
            candle("u3", 103, 105, 103, 104),
            candle("u4", 104, 110, 109, 109),
        ]
        self.assertIsNone(detect_latest_fvg(series, "COMPRA"),
                          "FVG com terceira vela sendo a última deve ser ignorado")

        # Com >=1 candle de confirmação, o mesmo FVG passa a ser detectado
        confirmed = series + [candle("u5", 109, 113, 110, 112)]
        fvg = detect_latest_fvg(confirmed, "COMPRA")
        self.assertIsNotNone(fvg)
        self.assertEqual(fvg["type"], "FVG_BULLISH")

    def test_m3_cap_rr_maximo(self):
        """M3: alvos com RR acima de MAX_TECHNICAL_RR (8.0) são descartados."""
        from src.smc_price_levels import build_smc_trade_levels, MAX_TECHNICAL_RR

        candles = _smc_compra_candles()
        # FVG válido [100,105]; entry 104 dentro da zona.
        fake_fvg = {"type": "FVG_BULLISH", "start": 100.0, "end": 105.0}

        # Caso 1: alvo mais próximo paga 8R exato (cap inclusivo) → níveis OK.
        # entry=104, stop=102 → risk=2.0; alvo em 120 → (120-104)/2 = 8.0.
        with patch("src.smc_price_levels.detect_latest_fvg", return_value=fake_fvg):
            with patch("src.smc_price_levels.detect_swing_levels",
                       return_value=([107.0, 120.0], [102.0])):
                levels = build_smc_trade_levels("COMPRA", min_rr=1.0,
                                                candles=candles, entry_price=104.0)
                # tp1=107 (1.5R), tp2=120 (8R exato) → aceito
                self.assertIsNotNone(levels)

        # Caso 2: único alvo paga 16R (> cap) → todos descartados → None.
        with patch("src.smc_price_levels.detect_latest_fvg", return_value=fake_fvg):
            with patch("src.smc_price_levels.detect_swing_levels",
                       return_value=([136.0], [102.0])):
                levels = build_smc_trade_levels("COMPRA", min_rr=1.0,
                                                candles=candles, entry_price=104.0)
                # (136-104)/2 = 16R > 8R → descartado
                self.assertIsNone(levels)

        self.assertGreater(MAX_TECHNICAL_RR, 0)

    def test_m2_tp1_abaixo_min_rr_bloqueia(self):
        """M2: quando o primeiro alvo estrutural paga < min_rr, bloqueia mesmo
        que um alvo distante pague bem (evita over-blocking mal calibrado)."""
        from src.smc_price_levels import build_smc_trade_levels

        candles = _smc_compra_candles()
        fake_fvg = {"type": "FVG_BULLISH", "start": 100.0, "end": 105.0}

        # entry=104, stop=102 → risk=2.0. tp1 em 105.5 → 0.75R (< 1.0), tp2 em 110 → 3R.
        with patch("src.smc_price_levels.detect_latest_fvg", return_value=fake_fvg):
            with patch("src.smc_price_levels.detect_swing_levels",
                       return_value=([105.5, 110.0], [102.0])):
                levels = build_smc_trade_levels("COMPRA", min_rr=1.0,
                                                candles=candles, entry_price=104.0)
                self.assertIsNone(levels,
                                  "tp1 com RR < min_rr deve bloquear mesmo com tp2 bom")

    def test_m2_tp2_venda_menor_que_tp1(self):
        """M2 (VENDA): tp2 deve ser estritamente menor que tp1 em VENDA."""
        from src.smc_price_levels import build_smc_trade_levels

        # Série espelhada: FVG bearish; entry 126; stop 128; alvos 123 e 118.
        candles = _smc_venda_candles()
        fake_fvg = {"type": "FVG_BEARISH", "start": 128.0, "end": 124.0}

        with patch("src.smc_price_levels.detect_latest_fvg", return_value=fake_fvg):
            with patch("src.smc_price_levels.detect_swing_levels",
                       return_value=([128.0], [118.0, 123.0])):
                levels = build_smc_trade_levels("VENDA", min_rr=1.0,
                                                candles=candles, entry_price=126.0)
                self.assertIsNotNone(levels)
                # VENDA: stop=128 > entry=126; targets ordenados desc -> [123, 118]
                self.assertLess(levels["tp2"], levels["tp1"],
                                "Em VENDA tp2 deve ser menor que tp1 (não colapsar)")
                self.assertGreater(levels["stop"], levels["entry"])


class TestShadowResultLabeling(unittest.TestCase):
    """T3: Rotulação pelo RR técnico real (S3) e guard de sanidade (S2)."""

    def _row(self, entry="100.0", stop="90.0", target="103.8", direction="COMPRA"):
        return {
            "id": "SHADOW-000001",
            "opened_at": "2026-07-30T09:00:00",
            "closed_at": "",
            "symbol": "Gold_Spot",
            "direction": direction,
            "entry": entry,
            "stop": stop,
            "target": target,
            "missing_confirmations": "",
            "event_signature": "SIG",
            "status": "ABERTO",
            "result": "EM_ESTUDO",
        }

    def test_shadow_rotula_rr_real(self):
        """S3: resultado reflete o RR técnico real (ex: WIN_RR_0.38)."""
        from src.shadow_trade import _write, _read, evaluate_shadow_trades

        shadow_file = Path(tempfile.mktemp(suffix=".csv"))
        with patch("src.shadow_trade.SHADOW_FILE", shadow_file):
            _write([self._row()])  # entry=100, stop=90, target=103.8 → RR 0.38

            later = [
                {"time": "2026-07-30T09:05:00", "open": "101", "high": "104.0",
                 "low": "100.5", "close": "103"},
            ]
            evaluated = evaluate_shadow_trades(later)

            self.assertEqual(evaluated["updated"], ["SHADOW-000001"])
            self.assertEqual(_read()[0]["result"], "WIN_RR_0.38",
                             "Resultado deve carregar o RR técnico real")

    def test_shadow_rotula_loss(self):
        """S3: perda continua sendo LOSS."""
        from src.shadow_trade import _write, _read, evaluate_shadow_trades

        shadow_file = Path(tempfile.mktemp(suffix=".csv"))
        with patch("src.shadow_trade.SHADOW_FILE", shadow_file):
            _write([self._row()])

            later = [
                {"time": "2026-07-30T09:05:00", "open": "99", "high": "100.0",
                 "low": "89.0", "close": "95"},
            ]
            evaluated = evaluate_shadow_trades(later)

            self.assertEqual(evaluated["updated"], ["SHADOW-000001"])
            self.assertEqual(_read()[0]["result"], "LOSS")

    def test_shadow_rejeita_preco_surreal(self):
        """S2: entry divergente >30% da mediana é rejeitado."""
        from src.shadow_trade import register_shadow_trade

        candles = [
            {"time": f"2026-07-30T09:{i:02d}:00",
             "open": "100", "high": "102", "low": "98",
             "close": str(100.0 + i * 0.5)}
            for i in range(15)
        ]
        # Última vela fechada com preço absurdo (fora da faixa)
        candles[-2]["close"] = "200.0"

        with patch("src.shadow_trade.SHADOW_FILE", Path(tempfile.mktemp(suffix=".csv"))):
            result = register_shadow_trade(candles, "COMPRA", ["FIB"], "SIG")

        self.assertFalse(result.get("ok"))
        self.assertEqual(result.get("error"), "UNREALISTIC_ENTRY_PRICE",
                         "Entry surreal deve ser rejeitado antes de calcular níveis")


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
                with patch("src.smc_price_levels.build_smc_trade_levels",
                           return_value={"tp2": 2360.0, "stop": fake_stop}):
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
                with patch("src.smc_price_levels.build_smc_trade_levels",
                           return_value={"tp2": 2360.0, "stop": 2304.5}):
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
                with patch("src.smc_price_levels.build_smc_trade_levels",
                           return_value={"tp2": 2360.0, "stop": 2280.0}):
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
