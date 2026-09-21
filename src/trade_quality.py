"""Measurements only: no orders, stop changes or learning-score changes."""
import math


def number(value):
    try:
        value = float(value)
        return value if math.isfinite(value) else None
    except (TypeError, ValueError):
        return None


def execution_quality(direction, requested, entries, deals):
    fills = [(number(getattr(d, 'price', None)), number(getattr(d, 'volume', None))) for d in entries]
    fills = [(p, v) for p, v in fills if p is not None and v is not None and p > 0 and v > 0]
    volume = sum(v for _, v in fills)
    entry = sum(p*v for p, v in fills)/volume if volume else None
    requested = number(requested)
    sign = {'COMPRA': 1, 'VENDA': -1}.get(direction)
    costs = {k: sum(number(getattr(d, k, 0)) or 0 for d in deals) for k in ('commission', 'swap', 'fee')}
    return dict(actual_entry=entry, entry_volume=volume, **costs,
                adverse_slippage_price=(entry-requested)*sign if entry and requested and sign else None)


def quote_excursions(direction, entry, stop, target, start, end, ticks, after_ms=3600000):
    entry, stop, target = map(number, (entry, stop, target))
    buy = direction == 'COMPRA'
    if direction not in ('COMPRA', 'VENDA') or None in (entry, stop, target):
        raise ValueError('Invalid trade')
    if not (0 < stop < entry < target if buy else 0 < target < entry < stop) or end < start:
        raise ValueError('Invalid trade bounds')
    inside, after, spreads = [], [], []
    for tick in ticks:
        t, bid, ask = (number(tick.get(k)) for k in ('time_msc', 'bid', 'ask'))
        if None in (t, bid, ask) or bid <= 0 or ask < bid:
            continue
        price = bid if buy else ask
        if start <= t <= end:
            inside.append((t, price))
            spreads.append(ask-bid)
        elif end < t <= end+after_ms:
            after.append((t, price))
    signed = [(price-entry)*(1 if buy else -1) for _, price in inside]
    risk = abs(entry-stop)
    return {
        'status': 'OBSERVED_TICKS' if inside else 'NO_IN_TRADE_QUOTES',
        'quote_side': 'bid' if buy else 'ask', 'ticks': len(inside), 'post_exit_ticks': len(after),
        'mfe_r': max(0, max(signed))/risk if signed else None,
        'mae_r': max(0, -min(signed))/risk if signed else None,
        'spread_mean_price': sum(spreads)/len(spreads) if spreads else None,
        'first_tick_msc': min((t for t, _ in inside), default=None),
        'last_tick_msc': max((t for t, _ in inside), default=None),
        'target_seen_after_exit': any(p >= target if buy else p <= target for _, p in after) if after else None,
        'post_exit_window_ms': after_ms, 'complete_history_verified': False,
        'interpretation': 'Observed price excursion in initial price-risk units; excludes costs and is not executable profit.',
    }
