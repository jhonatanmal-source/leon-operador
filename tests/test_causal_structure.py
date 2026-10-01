import random

import pytest

from src.institutional_analysis_engine import (
    analyze_smc_context, detect_pivots, detect_structure_events,
    detect_structure_pivots,
)


def candles_from_rows(rows):
    return [dict(zip(('open', 'high', 'low', 'close'), row), time=i)
            for i, row in enumerate(rows)]


def regression_candles():
    return candles_from_rows([
        (100,106,99,103), (103,104,98,101), (101,102,99,100),
        (100,103,95,97), (97,102,94,99), (99,102,95,97),
        (97,100,95,98), (98,102,96,100), (100,105,99,102),
        (102,107,101,104), (104,107,101,102), (102,105,100,101),
        (101,102,98,99), (99,102,98,101), (101,103,96,98),
        (98,104,96,101), (101,102,99,100), (100,103,97,99),
        (99,104,98,102), (102,106,100,105), (105,111,102,108),
        (108,110,105,106), (106,109,103,108), (108,110,105,106),
        (106,107,102,103), (103,106,99,102), (102,106,100,104),
        (104,106,98,101), (101,104,98,100), (100,103,96,99),
    ])


def assert_prefix_invariant(candles):
    full = detect_structure_events(candles)
    for count in range(1, len(candles)):
        partial = detect_structure_events(candles[:count])
        assert partial == [event for event in full if event['index'] < count - 1]


def test_future_extreme_does_not_erase_bos_at_19():
    candles = regression_candles()
    events = detect_structure_events(candles)
    assert any(e['index'] == 19 and e['type'] == 'BOS_BULLISH' and e['level'] == 104
               for e in events)
    assert_prefix_invariant(candles)
    # Public institutional path uses the same causal stream.
    context = analyze_smc_context(candles)
    assert context['events'] == events


def test_many_prefixes_preserve_historical_events():
    rng = random.Random(7)
    for _ in range(20):
        price = 100
        rows = []
        for _ in range(40):
            op = price
            price += rng.choice((-3, -2, -1, 1, 2, 3))
            rows.append((op, max(op, price) + rng.randint(1, 3),
                         min(op, price) - rng.randint(1, 3), price))
        assert_prefix_invariant(candles_from_rows(rows))


def test_confirmation_delay_and_elliott_contract():
    candles = candles_from_rows([(5,6,4,5),(5,7,4,6),(6,10,5,8),
                                (8,9,5,6),(6,8,5,7),(7,8,6,7)])
    assert detect_structure_pivots(candles[:5]) == []
    assert detect_structure_pivots(candles)[0]['confirmed_index'] == 4
    assert detect_pivots(candles) == [dict(index=2, type='HIGH', price=10, time=2)]


@pytest.mark.parametrize('direction', [1, -1])
def test_wick_is_not_break_and_live_candle_ignored(direction):
    rows = [(5,6,4,5),(5,7,4,6),(6,10,5,8),(8,9,5,6),
            (6,8,5,7),(7,12,6,9),(9,13,8,11)]
    def mirror(row):
        o,h,l,c = row
        return (-o,-l,-h,-c) if direction == -1 else row
    candles = candles_from_rows([mirror(row) for row in rows])
    assert detect_structure_events(candles) == []
    candles.append(dict(candles[-1], time=7))
    events = detect_structure_events(candles)
    assert len(events) == 1
    assert events[0]['type'] == ('BOS_BULLISH' if direction == 1 else 'BOS_BEARISH')


def test_explicit_pivot_not_available_until_confirmation():
    candles = candles_from_rows([(10,12,9,11)] * 7)
    pivot = dict(index=1, confirmed_index=4, type='HIGH', price=10)
    events = detect_structure_events(candles, [pivot])
    assert [event['index'] for event in events] == [4]


def test_opposite_break_is_choch_and_repeated_level_is_not_reemitted():
    candles = candles_from_rows([(10,12,8,10),(10,12,8,10),
                                (10,12,8,10),(10,14,9,13),
                                (13,14,6,7),(7,9,5,6),(6,7,5,6)])
    pivots = [dict(index=0, confirmed_index=2, type='HIGH', price=12),
              dict(index=1, confirmed_index=3, type='LOW', price=8)]
    assert [e['type'] for e in detect_structure_events(candles, pivots)] == [
        'BOS_BULLISH', 'CHOCH_BEARISH']


@pytest.mark.parametrize('window', [0, -1, True, 1.5])
def test_invalid_window_rejected(window):
    with pytest.raises(ValueError):
        detect_structure_pivots([], window)
