import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.top_down_agent import _bias


def candle(open_, high, low, close):
    return {"time": "", "open": open_, "high": high, "low": low, "close": close}


class TopDownBiasTests(unittest.TestCase):
    """Testes para o _bias() reescrito com médias vs estrutura."""

    def test_menos_de_5_candles_retorna_sem_dados(self):
        candles = [candle(100, 101, 99, 100) for _ in range(3)]
        self.assertEqual(_bias(candles), "SEM DADOS")

    def test_sma5_acima_sma20_retorna_alta(self):
        # Preço sobe consistentemente: SMA5 > SMA20
        candles = [candle(100 + i * 0.5, 101 + i * 0.5, 99 + i * 0.5, 100.5 + i * 0.5) for i in range(25)]
        self.assertEqual(_bias(candles), "ALTA")

    def test_sma5_abaixo_sma20_retorna_baixa(self):
        # Preço cai consistentemente: SMA5 < SMA20
        candles = [candle(100 - i * 0.5, 101 - i * 0.5, 99 - i * 0.5, 100.5 - i * 0.5) for i in range(25)]
        self.assertEqual(_bias(candles), "BAIXA")

    def test_higher_highs_sem_lower_lows_retorna_alta(self):
        # SMA5 ~ SMA20 (flat), mas estrutura mostra HH
        candles = []
        for i in range(25):
            base = 100.0
            close = base + (i * 0.01)  # sobe muito lentamente
            high = base + 0.5 + (i * 0.5)  # HH claro
            low = base - 0.5 + (i * 0.05)  # não cai
            candles.append(candle(close - 0.1, high, low, close))
        self.assertEqual(_bias(candles), "ALTA")

    def test_lower_lows_sem_higher_highs_retorna_baixa(self):
        # SMA5 ~ SMA20 (flat), mas estrutura mostra LL
        candles = []
        for i in range(25):
            base = 100.0
            close = base - (i * 0.01)
            high = base + 0.5 - (i * 0.05)
            low = base - 0.5 - (i * 0.5)  # LL claro
            candles.append(candle(close + 0.1, high, low, close))
        self.assertEqual(_bias(candles), "BAIXA")

    def test_sem_tendencia_clara_retorna_lateral(self):
        # Preço oscila sem direção
        candles = []
        for i in range(25):
            base = 100.0 + (i % 5)  # oscila 0-4
            candles.append(candle(base, base + 0.5, base - 0.5, base))
        self.assertEqual(_bias(candles), "LATERAL")

    def test_exatamente_5_candles_funciona(self):
        candles = [candle(100 + i, 101 + i, 99 + i, 100.5 + i) for i in range(5)]
        result = _bias(candles)
        self.assertIn(result, ("ALTA", "BAIXA", "LATERAL"))


if __name__ == "__main__":
    unittest.main()
