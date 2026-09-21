import json
import tempfile
import unittest
import sys
from types import SimpleNamespace
from contextlib import ExitStack
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

from src import operational_evidence as evidence
from src import institutional_analysis_engine as engine
from src import memory_context_engine as memory
from src.daily_entry_guard import update_daily_state
from src import mt5_operation_close_monitor as monitor
from src import obsidian_sync as obsidian


class EvidenceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / "data"
        patcher = patch.object(evidence, "DATA", self.root)
        patcher.start()
        self.addCleanup(patcher.stop)

    def operation(self, ticket=1, profit=10, version=evidence.VERSION):
        return dict(id=f"PREOP-{ticket}", source="MT5_DEMO_REAL", position_id=ticket,
                    account_key="server:1", actual_profit=profit, realized_r=profit / 10,
                    ativo="XAUUSD", direcao="COMPRA", smc="BULLISH", elliott="ONDA 3",
                    setup_version=version, data_fechamento="2026-09-10T10:00:00", currency="USD")

    def test_same_ticket_idempotent_and_other_account_distinct(self):
        self.assertTrue(evidence.record_confirmed_outcome(self.operation()))
        self.assertFalse(evidence.record_confirmed_outcome(self.operation()))
        other = self.operation()
        other["account_key"] = "server:2"
        evidence.record_confirmed_outcome(other)
        self.assertEqual(len(evidence.confirmed_records()), 2)

    def test_simulated_result_rejected(self):
        row = self.operation()
        row["source"] = "SHADOW"
        with self.assertRaises(ValueError):
            evidence.record_confirmed_outcome(row)

    def test_rank_uses_only_current_confirmed_version_and_minimum(self):
        for ticket in range(3):
            evidence.record_confirmed_outcome(self.operation(ticket=ticket + 1))
        self.assertEqual(evidence.learning_score(self.operation()), 0)
        evidence.record_confirmed_outcome(self.operation(ticket=4))
        evidence.record_confirmed_outcome(self.operation(ticket=5, profit=-999, version="LEGACY"))
        self.assertAlmostEqual(evidence.learning_score(self.operation()), 1 / 6)

    def test_learning_does_not_mix_entry_models_or_contexts(self):
        sample = dict(self.operation(), entry_model='ORDER_BLOCK_RETEST', context_mode='TENDENCIA')
        evidence.record_confirmed_outcome(sample)
        evidence.record_confirmed_outcome(dict(self.operation(ticket=2), entry_model='CHOCH_ORDER_BLOCK_RETEST', context_mode='TENDENCIA'))
        evidence.record_confirmed_outcome(dict(self.operation(ticket=3), entry_model='ORDER_BLOCK_RETEST', context_mode='CORRECAO'))
        evidence.record_confirmed_outcome(self.operation(ticket=4))
        self.assertEqual(evidence.learning_statistics(sample)['samples'], 1)
        report = evidence.daily_evidence_report('2026-09-10')
        self.assertEqual(len(report['patterns']), 4)

    def test_setup_requires_all_confirmations_and_rejects_tamper(self):
        decision = evidence.setup_decision("COMPRA", {"valid": True, "entry_eligible": True, "direction": "ALTA"}, True, True, True)
        preop = dict(id="PREOP-1", status="ABERTO", ativo="XAUUSD", direcao="COMPRA", entrada="100", stop="99", tp2="102")
        evidence.save_setup_evidence(preop, decision)
        self.assertTrue(evidence.validate_setup_evidence(preop)["ok"])
        preop["stop"] = "98"
        self.assertFalse(evidence.validate_setup_evidence(preop)["ok"])
        self.assertFalse(evidence.setup_decision("COMPRA", {"valid": False}, True, True, True)["approved"])
        self.assertFalse(evidence.setup_decision("COMPRA", {"valid": True}, False, True, True)["approved"])

    def test_stale_evidence_cannot_execute(self):
        preop = dict(id="PREOP-1", status="ABERTO")
        preop.update(direcao="COMPRA")
        evidence.save_setup_evidence(preop, evidence.setup_decision("COMPRA", {"valid": True, "entry_eligible": True, "direction": "ALTA"}, True, True, True))
        self.assertEqual(evidence.validate_setup_evidence(preop, datetime.now(timezone.utc) + timedelta(minutes=4))["error"], "SETUP_EVIDENCE_STALE")

    def test_report_does_not_include_future_operations(self):
        evidence.record_confirmed_outcome(self.operation())
        self.assertEqual(evidence.daily_evidence_report("2026-09-09")["confirmed_positions"], 0)
        self.assertEqual(evidence.daily_evidence_report("2026-09-10")["confirmed_positions"], 1)
        self.assertTrue((self.root.parent / "obsidian_vault/aprendizados_diarios/2026-09-10-evidencias.md").exists())

    def test_outcome_labels_do_not_treat_observation_as_loss(self):
        for label in ("OBSERVADO", "SEM_ENTRADA", "INVALIDADA", "BLOQUEADA", "RECUSADA"):
            self.assertFalse(memory._resultado_negativo(label))
        for label in ("WIN_TP1", "WIN_TP2", "VITORIA"):
            self.assertTrue(memory._resultado_positivo(label))

    def test_elliott_fallback_always_returns_result(self):
        pivots = [{"price": n + 1, "type": "HIGH"} for n in range(4)]
        with patch.object(engine, "detect_pivots", return_value=pivots), patch.object(engine, "analyze_fibonacci_wave_setup", return_value={"valid": False}), patch.object(engine, "detect_abc_correction", return_value={"valid": False}):
            result = engine.analyze_elliott_context([], "ALTA")
        self.assertIsInstance(result, dict)
        self.assertEqual(result["label"], "CORRECAO")
        self.assertFalse(result["valid"])

    def test_floating_profit_does_not_arm_giveback(self):
        state = update_daily_state({}, "today", 100, 10000, closed_pnl=0)
        state = update_daily_state(state, "today", 10, 10000, closed_pnl=0)
        self.assertTrue(state["approved"])
        self.assertEqual(state["peak"], 0)

    def test_closed_profit_arms_and_latches_giveback(self):
        state = update_daily_state({}, "today", 500, 10000, closed_pnl=500)
        state = update_daily_state(state, "today", 300, 10000, closed_pnl=250)
        self.assertFalse(state["approved"])
        self.assertFalse(update_daily_state(state, "today", 200, 10000, closed_pnl=200)["approved"])

    def test_migration_removes_only_old_floating_profit_pause(self):
        old = {"day": "today", "peak": 10, "reason": "DAILY_PROFIT_GIVEBACK_REACHED"}
        self.assertTrue(update_daily_state(old, "today", 0, 10000, closed_pnl=0)["approved"])
        old["reason"] = "DAILY_STOP_REACHED"
        self.assertFalse(update_daily_state(old, "today", 0, 10000, closed_pnl=0)["approved"])

    def test_daily_stop_still_accounts_for_open_loss(self):
        state = update_daily_state({}, "today", -200, 10000, closed_pnl=50)
        self.assertEqual(state["reason"], "DAILY_STOP_REACHED")

    def test_closed_monitor_uses_net_costs_and_is_idempotent(self):
        now = int(datetime.now().timestamp()) + 1
        opening = SimpleNamespace(entry=0, order=123, symbol="XAUUSD", ticket=1001, time=now-10, profit=0, commission=-2, swap=0, fee=0)
        closing = SimpleNamespace(entry=1, order=456, symbol="XAUUSD", ticket=1002, time=now, profit=10, commission=-1, swap=-1, fee=-1, reason=2, price=100)
        fake = SimpleNamespace(initialize=lambda: True, shutdown=lambda: None,
            account_info=lambda: SimpleNamespace(server="demo", login=1, currency="USD", trade_mode=0),
            positions_get=lambda: [], history_orders_get=lambda **kw: [SimpleNamespace(position_id=123)],
            history_deals_get=lambda **kw: [opening, closing], ACCOUNT_TRADE_MODE_DEMO=0,
            DEAL_ENTRY_OUT=1, DEAL_ENTRY_OUT_BY=3, DEAL_REASON_SL=1, DEAL_REASON_TP=2,
            DEAL_REASON_CLIENT=3, DEAL_REASON_EXPERT=4)
        with ExitStack() as stack:
            stack.enter_context(patch.dict(sys.modules, {"mt5_safe": fake}))
            stack.enter_context(patch.object(monitor, "DATA_DIR", self.root))
            stack.enter_context(patch.object(monitor, "START_FILE", self.root / "started.txt"))
            stack.enter_context(patch.object(monitor, "PROCESSED_FILE", self.root / "processed.json"))
            stack.enter_context(patch.object(monitor, "_read_csv", return_value=[{"status": "ENVIADA", "ticket": "123", "ativo": "XAUUSD", "pre_operation_id": "PREOP-1"}]))
            stack.enter_context(patch.object(monitor, "_pre_operations_by_id", return_value={"PREOP-1": {"id": "PREOP-1"}}))
            stack.enter_context(patch.object(monitor, "reconciliar_pre_operacao_mt5", return_value={"ok": False}))
            stack.enter_context(patch.object(monitor, "sync_closed_trade"))
            evidence.atomic_json(self.root / 'order_evidence/demo-1-123.json', {
                'entry_model':'CHOCH_ORDER_BLOCK_RETEST', 'context_mode':'CORRECAO',
                'setup_version':evidence.VERSION, 'initial_risk':10,
            })
            result = monitor.check_mt5_closed_operations()
            self.assertEqual(result["operations"][0]["actual_profit"], 5)
            self.assertEqual(result['operations'][0]['entry_model'], 'CHOCH_ORDER_BLOCK_RETEST')
            self.assertEqual(result['operations'][0]['context_mode'], 'CORRECAO')
            self.assertEqual(result['operations'][0]['realized_r'], .5)
            self.assertEqual(len(evidence.confirmed_records()), 1)
            self.assertEqual(monitor.check_mt5_closed_operations()["operations"], [])
            self.assertEqual(len(evidence.confirmed_records()), 1)
            fake.positions_get = lambda: [SimpleNamespace(ticket=123, identifier=123)]
            self.assertEqual(monitor.check_mt5_closed_operations()["operations"], [])

    def test_obsidian_same_position_does_not_increment_twice(self):
        vault = self.root.parent / "vault"
        row = self.operation()
        row["resultado"] = "WIN_TP2"
        with patch.object(obsidian, "VAULT", vault), patch.object(obsidian, "DIARIO_DIR", vault / "daily"), patch.object(obsidian, "OPERACIONAL_DIR", vault / "trades"), patch.object(obsidian, "STATS_FILE", vault / "stats.json"):
            obsidian.sync_closed_trade(row)
            obsidian.sync_closed_trade(row)
            stats = json.loads((vault / "stats.json").read_text())
            self.assertEqual(stats["total"], 1)
            self.assertEqual(stats["wins"], 1)


if __name__ == "__main__":
    unittest.main()
