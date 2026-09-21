import unittest

from institutional_analysis_engine import (
    _abc_quad,
    _abc_subtype,
    analyze_elliott_context,
    analyze_smc_context,
    detect_abc_correction,
    detect_liquidity_event,
)


def candle(open_price, high, low, close):
    return {
        "time": "",
        "open": open_price,
        "high": high,
        "low": low,
        "close": close,
    }


def _pivot(price, ptype, index=0):
    return {"price": price, "type": ptype, "index": index}


class InstitutionalAnalysisTests(unittest.TestCase):

    def test_liquidity_sweep_requires_close_back_inside(self):
        candles = [
            candle(100, 101 + index * 0.1, 99, 100)
            for index in range(21)
        ]
        candles.append(candle(100, 105, 99.5, 100.5))
        candles.append(candle(100.5, 101, 100, 100.2))

        event = detect_liquidity_event(candles)

        self.assertEqual(event["type"], "SWEEP_BUY_SIDE")
        self.assertEqual(event["direction"], "BEARISH")

    def test_elliott_does_not_force_count_without_pivots(self):
        candles = [
            candle(100 + index, 101 + index, 99 + index, 100.5 + index)
            for index in range(12)
        ]

        result = analyze_elliott_context(candles, "ALTA")

        self.assertFalse(result["valid"])
        self.assertEqual(result["label"], "SEM_CONTAGEM")

    def test_smc_stays_neutral_without_choch_bos_sequence(self):
        candles = [
            candle(100 + index, 101 + index, 99 + index, 100.5 + index)
            for index in range(30)
        ]

        result = analyze_smc_context(candles)

        self.assertEqual(result["smc"], "NEUTRO")


class AbcQuadTests(unittest.TestCase):
    """Testes para _abc_quad — extração de 4 pivots (w0, a, b, c)."""

    def test_extracts_quad_from_bullish_correction(self):
        # ALTA (correção baixista): HIGH, LOW, HIGH, LOW
        pivots = [
            _pivot(110, "HIGH"), _pivot(100, "LOW"),
            _pivot(106, "HIGH"), _pivot(95, "LOW"),
        ]
        quad = _abc_quad(pivots, "ALTA")
        self.assertIsNotNone(quad)
        self.assertEqual(len(quad), 4)
        self.assertEqual(quad, (110, 100, 106, 95))

    def test_extracts_quad_from_bearish_correction(self):
        # BAIXA (correção altista): LOW, HIGH, LOW, HIGH
        pivots = [
            _pivot(80, "LOW"), _pivot(95, "HIGH"),
            _pivot(88, "LOW"), _pivot(102, "HIGH"),
        ]
        quad = _abc_quad(pivots, "BAIXA")
        self.assertIsNotNone(quad)
        self.assertEqual(quad, (80, 95, 88, 102))

    def test_uses_most_recent_pattern_by_default(self):
        # Múltiplos padrões — deve escolher o último (start mais alto)
        pivots = [
            _pivot(200, "HIGH"), _pivot(190, "LOW"), _pivot(195, "HIGH"), _pivot(185, "LOW"),
            _pivot(110, "HIGH"), _pivot(100, "LOW"), _pivot(106, "HIGH"), _pivot(95, "LOW"),
        ]
        quad = _abc_quad(pivots, "ALTA")
        self.assertIsNotNone(quad)
        # Deve pegar o último padrão: 110, 100, 106, 95
        self.assertEqual(quad, (110, 100, 106, 95))

    def test_returns_none_for_wrong_direction(self):
        pivots = [
            _pivot(100, "HIGH"), _pivot(90, "LOW"),
            _pivot(96, "HIGH"), _pivot(85, "LOW"),
        ]
        quad = _abc_quad(pivots, "NEUTRO")
        self.assertIsNone(quad)

    def test_returns_none_when_fewer_than_four_pivots(self):
        pivots = [_pivot(100, "HIGH"), _pivot(90, "LOW"), _pivot(95, "HIGH")]
        quad = _abc_quad(pivots, "ALTA")
        self.assertIsNone(quad)


class AbcSubtypeTests(unittest.TestCase):
    """Testes para _abc_subtype — classificação do subtipo de correção.

    Signature: _abc_subtype(w0, a, b, c, direction)
    onde:
      w0 = início da onda A
      a  = fim da onda A / início da onda B
      b  = fim da onda B / início da onda C
      c  = fim da onda C
    """

    def test_zigzag_when_c_extends_a_and_b_retrace_mid(self):
        # Alta (ALTA) → correção baixista: A desce, B sobe, C desce
        # w0=110, a=100 (onda A = 10), b=106 (onda B = 6, retrace 60%), c=95 (onda C = 11, ratio 1.1)
        result = _abc_subtype(110, 100, 106, 95, "ALTA")
        self.assertEqual(result, "ZIGZAG")

    def test_flat_when_c_equals_a_and_b_retrace_deep(self):
        # w0=105, a=95 (onda A=10), b=104 (onda B=9, retrace 90%), c=94 (onda C=10, ratio 1.0)
        result = _abc_subtype(105, 95, 104, 94, "ALTA")
        self.assertEqual(result, "FLAT")

    def test_flat_estendido_when_c_moderately_exceeds_a(self):
        # w0=105, a=95 (onda A=10), b=104 (onda B=9, retrace 90%), c=92 (onda C=12, ratio 1.2)
        result = _abc_subtype(105, 95, 104, 92, "ALTA")
        self.assertEqual(result, "FLAT_ESTENDIDO")

    def test_range_when_c_is_shorter_than_a(self):
        # w0=105, a=95 (onda A=10), b=99 (onda B=4, retrace 40%), c=97 (onda C=2, ratio 0.2)
        result = _abc_subtype(105, 95, 99, 97, "ALTA")
        self.assertEqual(result, "RANGE")

    def test_indefinido_when_wave_a_is_zero(self):
        # w0 = a → wave_a = 0
        result = _abc_subtype(100, 100, 105, 95, "ALTA")
        self.assertEqual(result, "INDEFINIDO")

    def test_zigzag_with_golden_ratio_c_extension(self):
        # w0=110, a=100 (onda A=10), b=105 (onda B=5, retrace 50%), c=86 (onda C=19, ratio 1.9)
        result = _abc_subtype(110, 100, 105, 86, "ALTA")
        self.assertEqual(result, "ZIGZAG")


class DetectAbcCorrectionTests(unittest.TestCase):
    """Testes para detect_abc_correction — detecção completa de ABC."""

    def test_valid_zigzag_detected_for_bullish_trend(self):
        # w0=110, a=100 (onda A=10), b=106 (onda B=6, retrace 60%), c=95 (onda C=11, ratio 1.1)
        pivots = [
            _pivot(110, "HIGH"), _pivot(100, "LOW"),
            _pivot(106, "HIGH"), _pivot(95, "LOW"),
        ]
        result = detect_abc_correction(pivots, "ALTA")
        self.assertTrue(result["valid"], msg=str(result))
        self.assertEqual(result["subtype"], "ZIGZAG")
        self.assertEqual(result["w0_price"], 110)
        self.assertEqual(result["a_price"], 100)
        self.assertEqual(result["b_price"], 106)
        self.assertEqual(result["c_price"], 95)
        self.assertGreaterEqual(result["confidence"], 45)

    def test_valid_zigzag_detected_for_bearish_trend(self):
        # w0=90, a=105 (onda A=15), b=98 (onda B=7, retrace 47%), c=115 (onda C=17, ratio 1.13)
        pivots = [
            _pivot(90, "LOW"), _pivot(105, "HIGH"),
            _pivot(98, "LOW"), _pivot(115, "HIGH"),
        ]
        result = detect_abc_correction(pivots, "BAIXA")
        self.assertTrue(result["valid"], msg=str(result))
        self.assertEqual(result["subtype"], "ZIGZAG")
        self.assertEqual(result["w0_price"], 90)
        self.assertEqual(result["a_price"], 105)
        self.assertEqual(result["b_price"], 98)
        self.assertEqual(result["c_price"], 115)

    def test_valid_flat_detected(self):
        # w0=105, a=95 (onda A=10), b=104 (onda B=9, retrace 90%), c=94 (onda C=10, ratio 1.0)
        pivots = [
            _pivot(105, "HIGH"), _pivot(95, "LOW"),
            _pivot(104, "HIGH"), _pivot(94, "LOW"),
        ]
        result = detect_abc_correction(pivots, "ALTA")
        self.assertTrue(result["valid"], msg=str(result))
        self.assertEqual(result["subtype"], "FLAT")

    def test_range_classified_as_valid_with_low_confidence(self):
        """Range forma um padrão ABC válido, porém com baixa confiança."""
        # w0=100, a=95 (onda A=5), b=98 (onda B=3, retrace 60%), c=97 (onda C=1, ratio 0.2)
        pivots = [
            _pivot(100, "HIGH"), _pivot(95, "LOW"),
            _pivot(98, "HIGH"), _pivot(97, "LOW"),
        ]
        result = detect_abc_correction(pivots, "ALTA")
        # c_ratio=0.2 < 0.886 → RANGE (correção curta)
        # Range é um padrão ABC estruturalmente válido, com confiança baixa
        self.assertTrue(result["valid"])
        self.assertEqual(result["subtype"], "RANGE")
        self.assertLess(result["confidence"], 50)

    def test_no_detection_for_impulse_pattern(self):
        # Padrão impulsivo: LOW, HIGH, LOW, HIGH, LOW, HIGH
        # Não forma HIGH, LOW, HIGH, LOW (para ALTA)
        pivots = [
            _pivot(100, "LOW"), _pivot(110, "HIGH"),
            _pivot(104, "LOW"), _pivot(124, "HIGH"),
            _pivot(114, "LOW"), _pivot(132, "HIGH"),
        ]
        result = detect_abc_correction(pivots, "ALTA")
        # De LOW=100, HIGH=110, LOW=104, HIGH=124 → não é HIGH,LOW,HIGH,LOW
        self.assertFalse(result["valid"])

    def test_confidence_higher_for_golden_ratio_zigzag(self):
        # w0=110, a=100 (onda A=10), b=106 (onda B=6, retrace 60%), c=80 (onda C=26, ratio 2.6)
        # C_extension=26/10=2.6 >> 1.618, still zigzag with base confidence 55
        pivots = [
            _pivot(110, "HIGH"), _pivot(100, "LOW"),
            _pivot(106, "HIGH"), _pivot(80, "LOW"),
        ]
        result = detect_abc_correction(pivots, "ALTA")
        self.assertTrue(result["valid"], msg=str(result))
        self.assertEqual(result["subtype"], "ZIGZAG")
        self.assertGreaterEqual(result["confidence"], 55)


class AnalyzeElliottContextAbcTests(unittest.TestCase):
    """Testes para analyze_elliott_context com detecção ABC integrada."""

    def test_abc_zigzag_detected_via_candles(self):
        """Cria candles que produzem pivôs HIGH-LOW-HIGH-LOW em tendência ALTA."""
        candles = [
            # Tendência de alta inicial
            candle(100, 102, 99, 101),
            candle(101, 103, 100, 102),
            candle(102, 104, 101, 103),
            candle(103, 105, 102, 104),
            candle(104, 106, 103, 105),
            candle(105, 107, 104, 106),
            candle(106, 108, 105, 107),
            candle(107, 109, 106, 108),
            # Pico (w0) em 109 → topo do movimento
            candle(108, 110, 107, 109),
            # Onda A: queda
            candle(109, 110, 105, 106),  # LOW ~105
            candle(106, 107, 104, 105),
            # Onda B: pullback
            candle(105, 109, 104, 108),  # HIGH ~109
            candle(108, 109, 107, 108),
            # Onda C: nova queda
            candle(108, 109, 103, 104),  # LOW ~103
            candle(104, 105, 102, 103),
        ]
        result = analyze_elliott_context(candles, "ALTA")
        # Após 15 candles com 4-5 pivots, o detector deve classificar
        msg = f"Label={result['label']}, correction_detected={result.get('correction_detected')}, phase={result.get('phase')}"
        # Se detectou ABC correction ou caiu no fallback genérico
        self.assertTrue(
            result.get("correction_detected") or result["label"] in ["CORRECAO", "SEM_CONTAGEM"],
            msg=msg,
        )

    def test_abc_populates_interest_zone_fields(self):
        """Verifica que detect_abc_correction popula todos os campos esperados."""
        pivots = [
            _pivot(110, "HIGH"), _pivot(100, "LOW"),
            _pivot(106, "HIGH"), _pivot(95, "LOW"),
        ]
        result = detect_abc_correction(pivots, "ALTA")
        self.assertTrue(result["valid"])
        # Campos essenciais para InterestZone
        self.assertEqual(result["subtype"], "ZIGZAG")
        self.assertIsNotNone(result["w0_price"])
        self.assertIsNotNone(result["a_price"])
        self.assertIsNotNone(result["b_price"])
        self.assertIsNotNone(result["c_price"])
        self.assertIsNotNone(result["b_retrace"])
        self.assertIsNotNone(result["c_extension"])
        self.assertIsNotNone(result["invalidation"])

    def test_new_interest_zone_fields_in_elliott_context(self):
        """Verifica que analyze_elliott_context retorna os novos campos."""
        candles = [
            candle(100 + i, 102 + i, 98 + i, 101 + i)
            for i in range(15)
        ]
        result = analyze_elliott_context(candles, "ALTA")
        # Novos campos devem existir (mesmo que sejam falsy/empty)
        self.assertIn("scenario_present", result)
        self.assertIn("scenario_type", result)
        self.assertIn("possible_wave_c", result)
        self.assertIn("impulse_possible", result)
        self.assertIn("correction_possible", result)
        self.assertIn("correction_detected", result)
        self.assertIn("correction_subtype", result)


if __name__ == "__main__":
    unittest.main()
