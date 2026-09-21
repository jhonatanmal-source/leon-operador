"""Read-only statistics over independent, broker-confirmed demo opportunities."""
import math
from statistics import mean, median, stdev

POLICY = 'smc_opportunity_v1'


def learning_key(row):
    # Elliott labels describe context; they do not split every wave into a new model.
    return '|'.join(str(row.get(k) or 'UNSPECIFIED') for k in
                    ('ativo', 'direcao', 'entry_model', 'context_mode'))


def opportunity_statistics(candidate, records, version):
    key = learning_key(candidate)
    groups, seen = {}, set()
    trades = missing = 0
    for row in records:
        if (row.get('source') != 'MT5_DEMO_REAL' or row.get('setup_version') != version
                or learning_key(row) != key):
            continue
        try:
            value = float(row['realized_r'])
        except (KeyError, ValueError, TypeError):
            continue
        if not math.isfinite(value):
            continue
        account, position, region = (str(row.get(k) or '').strip()
                                     for k in ('account_key', 'position_id', 'region_id'))
        identity = (account, position)
        if account and position and identity in seen:
            continue
        if account and position:
            seen.add(identity)
        trades += 1
        if not account or not position or not region:
            missing += 1
            continue
        groups.setdefault((account, region), []).append(value)
    values = [mean(group) for group in groups.values()]
    n = len(values)
    average = mean(values) if values else 0.0
    identified_model = (candidate.get('entry_model') not in (None, '', 'UNSPECIFIED')
                        and candidate.get('context_mode') not in (None, '', 'UNSPECIFIED'))
    eligible = n >= 4 and identified_model
    return {
        'pattern': key, 'method': POLICY, 'samples': n, 'trade_count': trades,
        'unidentified_opportunity_trades': missing,
        'duplicate_region_trades': trades - missing - n,
        'aggregation': 'mean_ticket_r_per_account_region_not_account_return',
        'mean_r': average, 'median_r': median(values) if values else None,
        'standard_error_r': stdev(values) / math.sqrt(n) if n > 1 else None,
        'selection_score': average * n / (n + 20) if eligible else 0.0,
        'status': 'EXPLORATORY' if eligible else 'INSUFFICIENT_SAMPLE' if identified_model else 'MODEL_UNIDENTIFIED',
        'validated_edge': False,
    }


def learning_summary(records, version):
    rows = [r for r in records if r.get('source') == 'MT5_DEMO_REAL' and r.get('setup_version') == version]
    candidates = {learning_key(r): r for r in rows}
    groups = {k: opportunity_statistics(r, rows, version) for k, r in candidates.items()}
    opportunities = {(r.get('account_key'), r.get('region_id')) for r in rows
                     if r.get('account_key') and r.get('region_id') and r.get('position_id')}
    decisions = [(r.get('selection_statistics_at_entry') or {}).get('decision') or {} for r in rows]
    attributed = [d for d in decisions if d.get('policy') == POLICY]
    return {'policy': POLICY, 'confirmed_trades': len(rows),
            'independent_opportunities': len(opportunities), 'groups': groups,
            'selection_attribution': {'closed_trades_with_decision': len(attributed),
                                      'changed_choice': sum(d.get('changed_choice') is True for d in attributed),
                                      'limitation': 'Choice attribution only; no counterfactual profit claim.'},
            'validated_edge': False}


def select_ranked_candidate(candidates):
    if not candidates:
        return None, None
    baseline = max(candidates, key=lambda r: r.get('data_abertura', ''))
    chosen = max(candidates, key=lambda r: (r['_selection']['selection_score'], r.get('data_abertura', '')))
    audit = {'policy': POLICY, 'baseline': 'latest_valid_candidate',
             'baseline_id': baseline['id'], 'selected_id': chosen['id'],
             'changed_choice': chosen['id'] != baseline['id'],
             'candidate_count': len(candidates), 'validated_edge': False,
             'candidates': [{'id': r['id'], 'region_id': r.get('region_id'),
                             'statistics': r['_selection']} for r in candidates]}
    return chosen, audit
