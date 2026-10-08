from unittest.mock import patch
from src import institutional_analysis_engine as engine


def test_elliott_unrecognized_correction_returns_invalid_context():
    pivots=[{'price':p,'type':t} for p,t in [(100,'HIGH'),(99,'LOW'),(100,'HIGH'),(99,'LOW')]]
    with patch.object(engine,'detect_pivots',return_value=pivots), patch.object(engine,'analyze_fibonacci_wave_setup',return_value={'valid':False}), patch.object(engine,'detect_abc_correction',return_value={'valid':False}):
        result=engine.analyze_elliott_context([], 'ALTA')
    assert result['label']=='CORRECAO'
    assert result['valid'] is False


def test_no_candles_does_not_write_or_raise():
    from src import candle_reader
    with patch.object(candle_reader,'mt5') as mt5, patch.object(candle_reader,'registrar_candle') as record:
        mt5.copy_rates_from_pos.return_value=None
        candle_reader.ler_candle_m15()
        record.assert_not_called()
        mt5.shutdown.assert_called_once()
