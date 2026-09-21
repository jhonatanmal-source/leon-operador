"""Prospective attribution, not a claim about untraded alternatives."""
from src.opportunity_learning import POLICY


def evaluate(records):
    groups = {'changed_choice': [], 'unchanged_choice': []}
    for row in records:
        if row.get('source') != 'MT5_DEMO_REAL':
            continue
        stats = row.get('selection_statistics_at_entry') or {}
        decision = stats.get('decision') or {}
        if stats.get('method') != POLICY or decision.get('policy') != POLICY:
            continue
        changed = decision.get('changed_choice')
        if not isinstance(changed, bool):
            continue
        groups['changed_choice' if changed else 'unchanged_choice'].append(row)
    result = {}
    for name, rows in groups.items():
        pnl = {}
        for row in rows:
            currency = row.get('currency') or 'UNKNOWN'
            pnl[currency] = round(pnl.get(currency, 0)+float(row['actual_profit']), 2)
        result[name] = {'closed_trades': len(rows), 'net_profit_by_currency': pnl}
    return {'policy': POLICY, 'cohorts': result, 'validated_improvement': False,
            'status': 'AWAITING_PROSPECTIVE_OUTCOMES' if not any(groups.values()) else 'DESCRIPTIVE_ONLY',
            'limitation': 'Different opportunities are not randomized comparable controls. Unselected outcomes are unknown.'}
