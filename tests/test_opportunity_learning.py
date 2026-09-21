import copy
import csv
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from src import operational_evidence as evidence
from src.opportunity_learning import learning_key, learning_summary, opportunity_statistics, select_ranked_candidate


def outcome(n=1, **kwargs):
    row = dict(source='MT5_DEMO_REAL', setup_version=evidence.VERSION,
               account_key='DEMO:1', position_id=n, region_id=f'R{n}',
               ativo='XAUUSD', direcao='COMPRA', smc='BULLISH', elliott='ONDA 3',
               entry_model='ORDER_BLOCK_RETEST', context_mode='TENDENCIA',
               realized_r=1.0, actual_profit=10, currency='USD', data_fechamento='2026-09-20T10:00:00')
    row.update(kwargs)
    return row


class OpportunityLearningTests(unittest.TestCase):
    def stats(self, rows, candidate=None):
        return opportunity_statistics(candidate or outcome(), rows, evidence.VERSION)

    def test_same_region_is_one_observation(self):
        rows = [outcome(n, region_id='ONE') for n in range(1, 5)]
        result = self.stats(rows)
        self.assertEqual((result['samples'], result['trade_count'], result['duplicate_region_trades']), (1, 4, 3))
        self.assertEqual(result['selection_score'], 0)

    def test_repeated_position_not_counted_twice(self):
        self.assertEqual(self.stats([outcome(), outcome()])['trade_count'], 1)

    def test_elliott_labels_do_not_fragment_smc_group(self):
        rows = [outcome(n, elliott=f'WAVE {n}') for n in range(1, 5)]
        self.assertEqual(self.stats(rows)['samples'], 4)
        self.assertAlmostEqual(self.stats(rows)['selection_score'], 1/6)

    def test_opportunity_r_is_average_not_sum(self):
        result = self.stats([outcome(1, realized_r=2), outcome(2, region_id='R1', realized_r=-1)])
        self.assertEqual(result['mean_r'], .5)

    def test_models_contexts_directions_assets_are_separate(self):
        rows = [outcome(), outcome(2, entry_model='CHOCH_ORDER_BLOCK_RETEST'),
                outcome(3, context_mode='CORRECAO'), outcome(4, direcao='VENDA'), outcome(5, ativo='EURUSD')]
        self.assertEqual(self.stats(rows)['samples'], 1)

    def test_missing_identity_does_not_become_an_opportunity(self):
        for field in ('account_key', 'region_id', 'position_id'):
            with self.subTest(field=field):
                result = self.stats([outcome(**{field: None})])
                self.assertEqual(result['samples'], 0)
                self.assertEqual(result['unidentified_opportunity_trades'], 1)

    def test_nonfinite_simulated_and_other_version_excluded(self):
        rows = [outcome(), outcome(2, source='SHADOW'), outcome(3, setup_version='OLD'),
                outcome(4, realized_r=float('nan')), outcome(5, realized_r=float('inf'))]
        self.assertEqual(self.stats(rows)['samples'], 1)

    def test_unknown_model_never_gets_score(self):
        rows = [outcome(n, entry_model='UNSPECIFIED') for n in range(1, 5)]
        self.assertEqual(self.stats(rows, rows[0])['selection_score'], 0)

    def test_accounts_are_distinct(self):
        self.assertEqual(self.stats([outcome(), outcome(account_key='DEMO:2')])['samples'], 2)

    def test_no_mutation_and_no_validated_edge_claim(self):
        rows = [outcome()]
        original = copy.deepcopy(rows)
        self.assertFalse(self.stats(rows)['validated_edge'])
        self.assertEqual(rows, original)

    def test_neutral_score_does_not_block_entry(self):
        row = dict(outcome(), id='P1', data_abertura='1', _selection=self.stats([]))
        chosen, audit = select_ranked_candidate([row])
        self.assertIs(chosen, row)
        self.assertFalse(audit['changed_choice'])

    def test_ranking_change_is_visible_and_does_not_change_trade(self):
        a = dict(outcome(), id='P1', data_abertura='1', stop=99, tp=110, _selection={'selection_score': .2})
        b = dict(outcome(), id='P2', data_abertura='2', stop=90, tp=120, _selection={'selection_score': 0})
        original = copy.deepcopy([a,b])
        chosen, audit = select_ranked_candidate([a,b])
        self.assertIs(chosen, a)
        self.assertEqual(audit['baseline_id'], 'P2')
        self.assertTrue(audit['changed_choice'])
        self.assertEqual([a,b], original)

    def test_tie_preserves_latest_baseline(self):
        rows = [dict(outcome(), id=str(n), data_abertura=str(n), _selection={'selection_score': 0}) for n in range(2)]
        chosen, audit = select_ranked_candidate(rows)
        self.assertEqual(chosen['id'], '1')
        self.assertFalse(audit['changed_choice'])

    def test_no_candidates(self):
        self.assertEqual(select_ranked_candidate([]), (None, None))

    def test_report_preserves_pnl_and_separates_ticket_count(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(evidence, 'DATA', Path(directory)/'data'):
            for n in range(1, 5):
                evidence.record_confirmed_outcome(outcome(n, region_id='ONE'))
            snapshot = evidence.daily_evidence_report('2026-09-20')
            self.assertEqual(snapshot['confirmed_positions'], 4)
            self.assertEqual(snapshot['learning']['independent_opportunities'], 1)
            self.assertEqual(sum(g['net_profit'] for g in snapshot['patterns'].values()), 40)
            self.assertEqual(evidence.daily_evidence_report('2026-09-19')['learning']['confirmed_trades'], 0)

    def test_executor_records_comparison_without_order_or_guard_bypass(self):
        from src import mt5_order_executor as executor
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'preops.csv'
            fields = ['id', 'status', 'data_abertura', 'region_id', 'ativo', 'direcao']
            with path.open('w') as f:
                writer = csv.DictWriter(f, fields, delimiter=';')
                writer.writeheader()
                for n, status in [(1, 'ABERTO'), (2, 'OBSERVADO'), (3, 'ABERTO')]:
                    writer.writerow(dict(id=f'P{n}', status=status, data_abertura=str(n), region_id=f'R{n}', ativo='XAUUSD', direcao='COMPRA'))
            def proof(row):
                return {'ok': row['id'] != 'P3', 'proof': {'entry_model': 'ORDER_BLOCK_RETEST',
                        'timeframe_details': {'policy': {'mode': 'TENDENCIA'}}}}
            with patch.object(executor, 'PRE_OPERATION_FILE', path), \
                 patch.object(executor, 'validate_setup_evidence', side_effect=proof), \
                 patch.object(executor, '_pre_operacao_ja_executada', return_value=False), \
                 patch.object(executor, 'learning_statistics', return_value=self.stats([])):
                chosen = executor._ultima_pre_operacao_aberta()
            self.assertEqual(chosen['id'], 'P1')
            decision = json.loads((Path(directory) / 'latest_learning_selection.json').read_text())
            self.assertEqual(decision['candidate_count'], 1)
            self.assertFalse(decision['changed_choice'])
            self.assertEqual(chosen['_selection']['decision']['selected_id'], 'P1')

if __name__ == '__main__':
    unittest.main()
