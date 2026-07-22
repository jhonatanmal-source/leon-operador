import json
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path


from src.interest_zone_engine import (
    InterestZoneStore,
    build_zone_from_context,
    monitor_zone,
    validate_zone_for_execution,
)


def _identity(cycle="CYCLE-1"):
    return {
        "cycle_id": cycle,
        "analysis_id": f"ANALYSIS-{cycle}",
        "symbol": "XAUUSD",
        "timeframe": "M15",
        "candle_timestamp": "2026-07-12T21:45:00+00:00",
    }


def _context(score=None, momentum=None):
    return {
        "cycle_id": "CYCLE-1",
        "analysis_id": "ANALYSIS-CYCLE-1",
        "symbol": "XAUUSD",
        "weekly_context": "BULLISH_CONDITIONAL",
        "h4_structure": "ALTA",
        "h1_structure": "ALTA",
        "directional_context": "BULLISH",
        "region": {
            "region_detected": True,
            "region_type": "FVG_BULLISH",
            "region_low": 4000.0,
            "region_high": 4010.0,
            "region_direction": "BULLISH",
            "source_timeframe": "M15",
            "source_module": "institutional_analysis_engine",
            "source_reason": "FVG nao mitigado apos estrutura.",
            "invalidation_price": 3998.0,
        },
        "smc": {
            "direction": "BULLISH",
            "fvg_valid": True,
            "liquidity_identified": True,
            "liquidity_swept": False,
            "bos": "BOS_BULLISH",
            "choch": "CHOCH_BULLISH",
        },
        "elliott": {
            "scenario_present": True,
            "scenario_type": "ABC_CORRECTION",
            "possible_wave_c": True,
            "correction_possible": True,
        },
        "fibonacci": {
            "fib_region_present": True,
            "fib_level": 0.618,
            "fib_confluence": True,
        },
        "score": score,
        "momentum": momentum,
    }


class InterestZoneEngineTests(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.store = InterestZoneStore(Path(self.tmpdir.name) / "zones.json")

    def tearDown(self):
        self.tmpdir.cleanup()

    def _zone(self, price=4030.0, cycle="CYCLE-1", score=None, momentum=None):
        zone = build_zone_from_context(
            _identity(cycle),
            _context(score=score, momentum=momentum),
            current_price=price,
        )
        self.assertIsNotNone(zone)
        return zone

    def test_scenario_a_price_outside_zone(self):
        zone = self._zone(4030.0)
        self.assertEqual(zone["region_status"], "FORA_DA_ZONA")
        self.assertNotEqual(zone["region_status"], "CONFIRMADA")

    def test_scenario_b_price_approaches_zone(self):
        zone = self._zone(4015.0)
        self.assertEqual(zone["region_status"], "APROXIMANDO")
        self.assertTrue(zone["monitoring_enabled"])

    def test_touch_does_not_authorize_entry(self):
        zone = self._zone(4005.0)
        self.assertEqual(zone["region_status"], "ATIVA")
        self.assertNotIn(zone["region_status"], {"CONFIRMADA", "PRE_TRADE_VALID"})

    def test_scenario_c_waits_for_liquidity(self):
        zone = self._zone(4005.0)
        zone = monitor_zone(
            zone,
            current_price=4005.0,
            evidence={"liquidity_present": True, "liquidity_swept": False},
        )
        self.assertEqual(zone["region_status"], "AGUARDANDO_LIQUIDEZ")

    def test_liquidity_swept_waits_for_structure_on_same_zone(self):
        zone = self._zone(4005.0)
        region_id = zone["region_id"]
        zone = monitor_zone(
            zone,
            current_price=4005.0,
            evidence={"liquidity_present": True, "liquidity_swept": True},
        )
        self.assertEqual(zone["region_status"], "AGUARDANDO_ESTRUTURA")
        self.assertEqual(zone["region_id"], region_id)

    def test_scenario_d_waits_for_confirmation(self):
        zone = self._zone(4005.0)
        zone = monitor_zone(
            zone,
            current_price=4005.0,
            evidence={
                "liquidity_present": True,
                "liquidity_swept": True,
                "choch_present": True,
                "trigger_confirmed": False,
            },
        )
        self.assertEqual(zone["region_status"], "AGUARDANDO_CONFIRMACAO")

    def test_scenario_e_confirmation_makes_zone_confirmed(self):
        zone = self._zone(4005.0)
        zone = monitor_zone(
            zone,
            current_price=4005.0,
            evidence={
                "liquidity_present": True,
                "liquidity_swept": True,
                "mss_present": True,
                "trigger_confirmed": True,
            },
        )
        self.assertEqual(zone["region_status"], "CONFIRMADA")
        self.assertEqual(zone["next_required_event"], "VALIDAR_PRE_TRADE_E_RISCO")

    def test_scenario_f_broken_region_is_invalidated(self):
        zone = self._zone(4005.0)
        zone = monitor_zone(zone, current_price=3997.0, evidence={})
        self.assertEqual(zone["region_status"], "INVALIDADA")
        self.assertFalse(zone["region_valid"])

    def test_old_region_expires(self):
        zone = self._zone(4030.0)
        zone["created_at"] = "2026-07-01T00:00:00+00:00"
        zone = monitor_zone(
            zone,
            current_price=4030.0,
            evidence={},
            now=datetime(2026, 7, 12, tzinfo=timezone.utc),
            max_age=timedelta(days=7),
        )
        self.assertEqual(zone["region_status"], "EXPIRADA")

    def test_same_market_zone_reuses_region_id_across_cycles(self):
        first = self._zone(4030.0, cycle="CYCLE-1")
        second = self._zone(4020.0, cycle="CYCLE-2")
        self.assertEqual(first["region_id"], second["region_id"])

    def test_score_and_momentum_do_not_change_zone(self):
        low = self._zone(4030.0, score=0, momentum=0)
        high = self._zone(4030.0, score=100, momentum=100)
        self.assertEqual(low["region_id"], high["region_id"])
        self.assertEqual(low["region_status"], high["region_status"])

    def test_unbounded_or_unsupported_context_does_not_create_zone(self):
        context = _context()
        context["region"]["region_high"] = None
        self.assertIsNone(build_zone_from_context(_identity(), context, current_price=4000))

    def test_atomic_store_reuses_record_and_keeps_valid_json(self):
        zone = self._zone(4030.0)
        self.store.upsert(zone)
        zone = monitor_zone(zone, current_price=4015.0, evidence={})
        self.store.upsert(zone)
        self.assertEqual(len(self.store.list()), 1)
        payload = json.loads(self.store.path.read_text(encoding="utf-8"))
        self.assertEqual(payload[0]["region_id"], zone["region_id"])
        self.assertFalse(list(self.store.path.parent.glob("*.tmp")))

    def test_execution_guard_requires_confirmed_matching_zone(self):
        zone = self._zone(4005.0)
        self.store.upsert(zone)
        preop = {
            "id": "PREOP-1",
            "pre_operation_id": "PREOP-1",
            "ativo": "XAUUSD",
            "region_id": zone["region_id"],
        }
        waiting = validate_zone_for_execution(preop, store=self.store)
        self.assertFalse(waiting["ok"])
        self.assertEqual(waiting["error"], "REGION_NOT_CONFIRMED")

        zone = monitor_zone(
            zone,
            current_price=4005.0,
            evidence={
                "liquidity_present": True,
                "liquidity_swept": True,
                "choch_present": True,
                "trigger_confirmed": True,
            },
        )
        zone["pre_operation_id"] = "PREOP-1"
        # Isolated legacy flags remain blocked.  A live official setup must
        # persist one complete, observable and causal structural sequence.
        self.assertFalse(validate_zone_for_execution(preop, store=self.store)["ok"])
        completed_at = "2026-07-12T22:15:00+00:00"
        zone.update({
            "causal_contract_version": "LEON_CAUSAL_CONTRACT_V2",
            "confirmation_contract_mode": "OFFICIAL_CAUSAL",
            "confirmation_state": "COMPLETE",
            "confirmation_completed_at": completed_at,
            "causality_state": "CAUSAL",
            "valid_confirmations": [{
                "confirmation_id": "CONF-1",
                "event_id": "EVENT-1",
                "structural_event_id": "STRUCT-1",
                "state": "COMPLETE",
                "confirmation_state": "COMPLETE",
                "timeline_state": "OBSERVABLE",
                "quality_valid": True,
                "confirmation_completed_at": completed_at,
            }],
        })
        self.store.upsert(zone)
        self.assertTrue(validate_zone_for_execution(preop, store=self.store)["ok"])

    def test_execution_guard_rejects_new_record_without_region(self):
        result = validate_zone_for_execution(
            {"id": "PREOP-NEW", "ativo": "XAUUSD"},
            store=self.store,
        )
        self.assertFalse(result["ok"])
        self.assertEqual(result["error"], "PRE_OPERATION_REGION_REQUIRED")

    # ── CONFIRMADA flow tests ─────────────────────────────────────

    def test_fresh_build_zone_starts_ativa_not_confirmada(self):
        zone = self._zone(4005.0)
        self.assertEqual(zone["region_status"], "ATIVA")
        self.assertNotIn(zone["region_status"], {"CONFIRMADA", "PRE_TRADE_VALID"})

    def test_empty_evidence_blocks_confirmada(self):
        zone = self._zone(4005.0)
        z2 = monitor_zone(zone, current_price=4005.0, evidence={})
        self.assertEqual(z2["region_status"], "ATIVA")

    def test_full_chain_to_confirmada(self):
        zone = self._zone(4005.0)
        z1 = monitor_zone(zone, current_price=4005.0, evidence={
            "liquidity_present": True, "liquidity_swept": True,
        })
        self.assertEqual(z1["region_status"], "AGUARDANDO_ESTRUTURA")

        z2 = monitor_zone(z1, current_price=4005.0, evidence={
            "liquidity_present": True, "liquidity_swept": True,
            "choch_present": True, "trigger_confirmed": False,
        })
        self.assertEqual(z2["region_status"], "AGUARDANDO_CONFIRMACAO")

        z3 = monitor_zone(z2, current_price=4005.0, evidence={
            "liquidity_present": True, "liquidity_swept": True,
            "choch_present": True, "trigger_confirmed": True,
        })
        self.assertEqual(z3["region_status"], "CONFIRMADA")
        self.assertEqual(z3["next_required_event"], "VALIDAR_PRE_TRADE_E_RISCO")

    def test_trigger_confirmed_alone_does_not_shortcircuit(self):
        zone = self._zone(4005.0)
        z = monitor_zone(zone, current_price=4005.0, evidence={
            "trigger_confirmed": True,
        })
        self.assertEqual(z["region_status"], "AGUARDANDO_LIQUIDEZ")

    def test_multi_step_progression_preserves_region_id(self):
        zone = self._zone(4005.0)
        rid = zone["region_id"]
        for ev in (
            {"liquidity_present": True, "liquidity_swept": True},
            {"liquidity_present": True, "liquidity_swept": True, "choch_present": True},
            {"liquidity_present": True, "liquidity_swept": True, "choch_present": True, "trigger_confirmed": True},
        ):
            zone = monitor_zone(zone, current_price=4005.0, evidence=ev)
            self.assertEqual(zone["region_id"], rid)
        self.assertEqual(zone["region_status"], "CONFIRMADA")


if __name__ == "__main__":
    unittest.main()
