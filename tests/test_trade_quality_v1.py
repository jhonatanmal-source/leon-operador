import json
import tempfile
import unittest
from datetime import datetime, timezone, timedelta
from pathlib import Path
from types import SimpleNamespace as NS
from unittest.mock import patch
from src.trade_quality import execution_quality, quote_excursions
from src import quality_collector as collector
from src.learning_evaluation import evaluate
from src.opportunity_learning import POLICY


class QualityTests(unittest.TestCase):
    def test_buy_uses_bid_and_excludes_post_exit(self):
        ticks = [{'time_msc': 1000, 'bid': 99, 'ask': 100},
                 {'time_msc': 2000, 'bid': 104, 'ask': 105},
                 {'time_msc': 3000, 'bid': 110, 'ask': 111}]
        q = quote_excursions('COMPRA', 100, 98, 110, 1000, 2000, ticks)
        self.assertEqual((q['mfe_r'], q['mae_r']), (2, .5))
        self.assertTrue(q['target_seen_after_exit'])
        self.assertFalse(q['complete_history_verified'])

    def test_sell_uses_ask(self):
        ticks = [{'time_msc': 1000, 'bid': 100, 'ask': 101},
                 {'time_msc': 2000, 'bid': 95, 'ask': 96}]
        q = quote_excursions('VENDA', 100, 102, 90, 1000, 2000, ticks)
        self.assertEqual((q['mfe_r'], q['mae_r']), (2, .5))

    def test_missing_data_is_not_zero(self):
        q = quote_excursions('COMPRA', 100, 98, 110, 1000, 2000, [])
        self.assertIsNone(q['mfe_r'])
        self.assertIsNone(q['mae_r'])
        self.assertIsNone(q['target_seen_after_exit'])

    def test_bad_quotes_filtered(self):
        q = quote_excursions('COMPRA', 100, 98, 110, 1, 2,
                            [{'time_msc':1,'bid':100,'ask':99}, {'time_msc':1,'bid':float('nan'),'ask':101}])
        self.assertEqual(q['ticks'], 0)

    def test_bad_trade_rejected(self):
        with self.assertRaises(ValueError):
            quote_excursions('COMPRA', 100, 101, 110, 1, 2, [])

    def test_fills_costs_slippage(self):
        deals = [NS(price=100,volume=1,commission=-1,swap=0,fee=0),
                 NS(price=102,volume=3,commission=-2,swap=-1,fee=-.5)]
        q = execution_quality('COMPRA',100,deals,deals)
        self.assertEqual(q['actual_entry'],101.5)
        self.assertEqual(q['adverse_slippage_price'],1.5)
        self.assertEqual(q['commission'],-3)
        self.assertEqual(execution_quality('VENDA',100,deals,deals)['adverse_slippage_price'],-1.5)

    def test_utc_and_bounded_paging(self):
        calls = []
        def ticks(symbol, when, count, flag):
            calls.append((when, count))
            return [{'time_msc':1000,'bid':99,'ask':100}]*count
        mt5 = NS(copy_ticks_from=ticks,COPY_TICKS_ALL=0)
        data, reason = collector.tick_history(mt5,'X',1000,9999999)
        self.assertEqual(reason,'PAGINATION_STALLED')
        self.assertEqual(len(data),1)
        self.assertEqual(calls[0][0].tzinfo,timezone.utc)
        self.assertLessEqual(len(calls),collector.MAX_BATCHES)

    def test_boundary_tick_is_not_post_exit(self):
        q = quote_excursions('COMPRA',100,98,110,1,2,[{'time_msc':2,'bid':110,'ask':111}])
        self.assertIsNone(q['target_seen_after_exit'])
        self.assertEqual(q['mfe_r'],5)

    def test_future_evaluation_has_no_false_profit_claim(self):
        self.assertEqual(evaluate([])['status'],'AWAITING_PROSPECTIVE_OUTCOMES')
        row = {'source':'MT5_DEMO_REAL','actual_profit':10,'currency':'USD',
               'selection_statistics_at_entry':{'method':POLICY,'decision':{'policy':POLICY,'changed_choice':True}}}
        result = evaluate([row,dict(row,source='SHADOW')])
        self.assertEqual(result['cohorts']['changed_choice']['closed_trades'],1)
        self.assertFalse(result['validated_improvement'])

    def test_currency_never_summed_across_currencies(self):
        row = {'source':'MT5_DEMO_REAL','actual_profit':10,'currency':'USD',
               'selection_statistics_at_entry':{'method':POLICY,'decision':{'policy':POLICY,'changed_choice':False}}}
        pnl = evaluate([row,dict(row,currency='EUR')])['cohorts']['unchanged_choice']['net_profit_by_currency']
        self.assertEqual(pnl,{'USD':10,'EUR':10})


class CollectorTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        p = patch.object(collector,'DATA',self.root)
        p.start(); self.addCleanup(p.stop)
        self.rows = {str(n):dict(source='MT5_DEMO_REAL',setup_version=collector.VERSION,
                    account_key='demo:1',position_id=n,order_ticket=n,ativo='XAUUSD',direcao='COMPRA',
                    stop=98,tp2=110,data_fechamento='2026-09-21') for n in range(1,5)}
        (self.root/'confirmed_mt5_outcomes.json').write_text(json.dumps(self.rows))
        self.original = (self.root/'confirmed_mt5_outcomes.json').read_bytes()
        self.mt5 = NS(initialize=lambda:True,shutdown=lambda:None,
                      account_info=lambda:NS(server='demo',login=1,trade_mode=0),
                      positions_get=lambda:[],ACCOUNT_TRADE_MODE_DEMO=0)

    def test_job_limit_and_no_ledger_mutation(self):
        with patch.object(collector,'measure',return_value={'status':'OBSERVED_TICKS','post_exit_window_elapsed':True,'collection_reason':'REQUESTED_END_REACHED','mfe_r':1,'mae_r':.5}):
            self.assertEqual(len(collector.run(self.mt5)['processed']),2)
            self.assertEqual(len(collector.run(self.mt5)['processed']),2)
            self.assertEqual(len(collector.run(self.mt5)['processed']),0)
        self.assertEqual((self.root/'confirmed_mt5_outcomes.json').read_bytes(), self.original)

    def test_other_account_and_real_rejected(self):
        self.mt5.account_info=lambda:NS(server='demo',login=2,trade_mode=0)
        self.assertEqual(collector.run(self.mt5)['processed'],[])
        self.mt5.account_info=lambda:NS(server='real',login=1,trade_mode=2)
        self.assertFalse(collector.run(self.mt5)['ok'])

    def test_open_positions_excluded(self):
        self.mt5.positions_get=lambda:[NS(ticket=n,identifier=n) for n in range(1,5)]
        with patch.object(collector,'measure') as measure:
            self.assertEqual(collector.run(self.mt5)['processed'],[])
            measure.assert_not_called()

    def test_failure_retries_bounded_and_no_error_leak(self):
        now=datetime(2026,9,21,tzinfo=timezone.utc)
        with patch.object(collector,'measure',side_effect=RuntimeError('private diagnostic')):
            for attempt in range(3):
                collector.run(self.mt5,limit=4,now=now+timedelta(minutes=16*attempt))
            self.assertEqual(collector.run(self.mt5,limit=4,now=now+timedelta(hours=2))['processed'],[])
        content=next((self.root/'trade_quality').glob('*.json')).read_text()
        self.assertNotIn('private diagnostic',content)
        self.assertIn('ATTEMPT_LIMIT',content)

if __name__ == '__main__':
    unittest.main()
