from unittest.mock import patch

import pytest
from src import institutional_analysis_engine as engine
from src import top_down_agent
from src.operational_evidence import select_elliott_entry, setup_decision


def event(index, kind, direction):
    return dict(index=index, type=kind + '_' + direction, direction=direction)


@pytest.mark.parametrize('bull,bear', [('BULLISH', 'BEARISH'), ('BEARISH', 'BULLISH')])
def test_opposite_choch_invalidates_previous_pair(bull, bear):
    old = [event(1, 'CHOCH', bull), event(2, 'BOS', bull)]
    change = event(3, 'CHOCH', bear)
    assert engine._event_pair(old + [change]) == (change, None)
    new = event(4, 'BOS', bear)
    assert engine._event_pair(old + [change, new]) == (change, new)


def test_latest_bos_beats_old_complete_pair():
    latest = event(4, 'BOS', 'BEARISH')
    assert engine._event_pair([event(1, 'CHOCH', 'BULLISH'), event(2, 'BOS', 'BULLISH'), latest]) == (None, latest)


def test_does_not_pair_across_opposite_leg():
    latest = event(4, 'BOS', 'BULLISH')
    assert engine._event_pair([event(1, 'CHOCH', 'BULLISH'), event(2, 'CHOCH', 'BEARISH'), latest]) == (None, latest)


def test_pending_change_is_visible_not_smc_approved():
    change = event(3, 'CHOCH', 'BEARISH')
    with patch.object(engine, 'detect_pivots', return_value=[]), patch.object(engine, 'detect_structure_events', return_value=[change]):
        result = engine.analyze_smc_context([])
    assert result['smc'] == 'NEUTRO'
    assert result['choch_event'] == change
    assert result['reason'] == 'CHOCH_AGUARDANDO_BOS'


@pytest.mark.parametrize('direction,bias', [('COMPRA', 'ALTA'), ('VENDA', 'BAIXA')])
def test_micro_entry_reachable_with_higher_context(direction, bias):
    h1 = dict(valid=False, entry_eligible=False, direction=bias)
    m15 = dict(valid=True, entry_eligible=True, direction=bias, label='ONDA 3')
    selected = select_elliott_entry(h1, m15, direction, bias)
    assert selected['entry_timeframe'] == 'M15'
    assert setup_decision(direction, selected, True, True, True)['approved']
    assert not setup_decision(direction, selected, True, True, False)['approved']
    assert not setup_decision(direction, selected, True, False, True)['approved']
    assert 'entry_timeframe' not in m15


@pytest.mark.parametrize('h1_bias', ['BAIXA', 'SEM DADOS', None])
def test_micro_cannot_bypass_opposite_or_missing_h1(h1_bias):
    m15 = dict(valid=True, entry_eligible=True, direction='ALTA')
    assert not select_elliott_entry({}, m15, 'COMPRA', h1_bias)['entry_eligible']


@pytest.mark.parametrize('valid,eligible,direction', [(False, True, 'ALTA'), (True, False, 'ALTA'), (True, True, 'BAIXA')])
def test_micro_requires_valid_aligned_entry(valid, eligible, direction):
    m15 = dict(valid=valid, entry_eligible=eligible, direction=direction)
    assert not select_elliott_entry({}, m15, 'COMPRA', 'LATERAL')['entry_eligible']


def test_h1_entry_keeps_priority():
    h1 = dict(valid=True, entry_eligible=True, direction='ALTA')
    assert select_elliott_entry(h1, h1, 'COMPRA', 'ALTA')['entry_timeframe'] == 'H1'


def test_forming_candles_cannot_change_top_down(tmp_path, monkeypatch):
    monkeypatch.setattr(top_down_agent, 'DATA_DIR', tmp_path)
    monkeypatch.setattr(top_down_agent, 'TOP_DOWN_FILE', tmp_path / 'top.csv')
    closed = [dict(close=100 + i, high=101 + i, low=99 + i) for i in range(40)]
    first = closed + [dict(close=1, high=1, low=1)]
    second = closed + [dict(close=10000, high=10000, low=10000)]
    a = top_down_agent.gerar_leitura_top_down(first, first, first)
    b = top_down_agent.gerar_leitura_top_down(second, second, second)
    for key in ('macro_semanal', 'h4_bias', 'h1_contexto', 'm15_gatilho'):
        assert a[key] == b[key]
