"""Testes para src/lab_zone_monitor.py — promocao de zonas LAB por evidencia real (B2)."""

import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

from src.interest_zone_engine import (
    InterestZoneStore,
    create_lab_zone,
    validate_zone_for_execution,
)
from src import lab_zone_monitor


def _candles(last_close: float, n: int = 30):
    """Gera candles sinteticos; so len e ultimo close importam (SMC/trigger mockados)."""
    candles = []
    for i in range(n):
        candles.append({
            "time": f"2026-08-24T{i % 24:02d}:00:00",
            "open": last_close,
            "high": last_close + 1,
            "low": last_close - 1,
            "close": last_close,
        })
    return candles


def _market(last_close: float, m15_n: int = 30, m5_n: int = 30, ok: bool = True, error: str = ""):
    if not ok:
        return {"ok": False, "error": error}
    return {
        "ok": True,
        "m15": _candles(last_close, m15_n),
        "m5": _candles(last_close, m5_n),
    }


def _smc_confirmada(direction_canon: str):
    """Analise SMC com estrutura + liquidez alinhadas a direcao da zona."""
    return {
        "direction": direction_canon,
        "smc": direction_canon,
        "bos": f"BOS_{direction_canon}",
        "bos_event": {"displacement": True, "time": "2026-08-24T10:00:00"},
        "choch": f"CHOCH_{direction_canon}",
        "liquidity": {
            "type": "SWEEP_SELL_SIDE" if direction_canon == "BULLISH" else "SWEEP_BUY_SIDE",
            "direction": direction_canon,
        },
    }


def _smc_neutro():
    return {
        "direction": None,
        "smc": "NEUTRO",
        "bos": "SEM_BOS",
        "choch": "SEM_CHOCH",
        "liquidity": {"type": "SEM_EVENTO", "direction": None},
    }


class LabZoneMonitorTests(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.store = InterestZoneStore(Path(self.tmpdir.name) / "zones.json")
        self.now = datetime(2026, 8, 24, 12, 0, 0, tzinfo=timezone.utc)

    def tearDown(self):
        self.tmpdir.cleanup()

    def _lab_zone(self, direction="COMPRA", entry=4030.0, stop=4020.0, tp1=4045.0, tp2=4060.0, preop="PREOP-LAB"):
        zone = create_lab_zone(
            symbol="Gold_Spot",
            direction=direction,
            entry_price=entry,
            stop_price=stop,
            tp1_price=tp1,
            tp2_price=tp2,
            brain_score=60,
            pre_operation_id=preop,
            store=self.store,
        )
        self.assertIsNotNone(zone)
        return zone

    def _patch_market(self, market, smc, trigger):
        return (
            patch.object(lab_zone_monitor, "load_execution_candles", MagicMock(return_value=market)),
            patch.object(lab_zone_monitor, "analyze_smc_context", MagicMock(return_value=smc)),
            patch.object(lab_zone_monitor, "_micro_trigger", MagicMock(return_value=trigger)),
        )

    def test_short_circuit_sem_zonas_lab(self):
        result = lab_zone_monitor.monitorar_zonas_lab(store=self.store, now=self.now)
        self.assertTrue(result["ok"])
        self.assertEqual(result["monitored"], 0)
        self.assertEqual(result["promoted"], 0)
        self.assertEqual(result["details"], [])

    def test_zona_normal_nao_e_monitorada(self):
        # Zona sem zone_source=LABORATORIO nao entra no monitor LAB.
        self.store.upsert({
            "region_id": "REG-NORMAL-1",
            "symbol": "Gold_Spot",
            "region_direction": "BULLISH",
            "region_status": "ATIVA",
            "region_low": 4020.0,
            "region_high": 4030.0,
            "zone_source": "DEMANDA",
            "monitoring_enabled": True,
        })
        result = lab_zone_monitor.monitorar_zonas_lab(store=self.store, now=self.now)
        self.assertEqual(result["monitored"], 0)

    def test_zona_terminal_ignorada(self):
        zone = self._lab_zone()
        zone["region_status"] = "INVALIDADA"
        self.store.upsert(zone)
        result = lab_zone_monitor.monitorar_zonas_lab(store=self.store, now=self.now)
        self.assertEqual(result["monitored"], 0)

    def test_zona_ja_confirmada_nao_reprocessada(self):
        # Zonas ja CONFIRMADA (inclui artefatos legados pre-18/08) ficam fora do
        # loop — nao ha custo de MT5 nem risco de expira-las por idade.
        zone = self._lab_zone()
        zone["region_status"] = "CONFIRMADA"
        self.store.upsert(zone)
        fake_load = MagicMock()
        with patch.object(lab_zone_monitor, "load_execution_candles", fake_load):
            result = lab_zone_monitor.monitorar_zonas_lab(store=self.store, now=self.now)
        self.assertEqual(result["monitored"], 0)
        fake_load.assert_not_called()

    def test_skip_mercado_indisponivel(self):
        self._lab_zone()
        market = _market(0, ok=False, error="INSUFFICIENT_EXECUTION_CANDLES")
        p1, p2, p3 = self._patch_market(market, _smc_neutro(), {"confirmed": False})
        with p1, p2, p3:
            result = lab_zone_monitor.monitorar_zonas_lab(store=self.store, now=self.now)
        self.assertEqual(result["skipped"], 1)
        self.assertEqual(result["monitored"], 0)
        self.assertEqual(result["details"][0]["reason"], "INSUFFICIENT_EXECUTION_CANDLES")

    def test_skip_candles_insuficientes(self):
        self._lab_zone()
        market = _market(4025.0, m15_n=5)
        p1, p2, p3 = self._patch_market(market, _smc_neutro(), {"confirmed": False})
        with p1, p2, p3:
            result = lab_zone_monitor.monitorar_zonas_lab(store=self.store, now=self.now)
        self.assertEqual(result["skipped"], 1)
        self.assertEqual(result["details"][0]["reason"], "INSUFFICIENT_M15")

    def test_simbolo_propagado_uma_leitura_por_simbolo(self):
        self._lab_zone()
        fake_load = MagicMock(return_value=_market(4025.0))
        p1, p2, p3 = self._patch_market(_market(4025.0), _smc_neutro(), {"confirmed": False})
        with patch.object(lab_zone_monitor, "load_execution_candles", fake_load), p2, p3:
            lab_zone_monitor.monitorar_zonas_lab(store=self.store, now=self.now)
        # load_execution_candles chamado com o simbolo real da zona (persistido
        # em upper-case por create_lab_zone), nunca default XAUUSD.
        fake_load.assert_called_once_with("GOLD_SPOT")

    def test_sem_evidencia_permanece_nao_confirmada(self):
        zone = self._lab_zone()
        rid = zone["region_id"]
        market = _market(4025.0)
        p1, p2, p3 = self._patch_market(market, _smc_neutro(), {"confirmed": False})
        with p1, p2, p3:
            result = lab_zone_monitor.monitorar_zonas_lab(store=self.store, now=self.now)
        self.assertEqual(result["promoted"], 0)
        updated = self.store.get(rid)
        self.assertNotEqual(updated["region_status"], "CONFIRMADA")
        self.assertEqual(updated["structural_confirmations"], [])

    def test_liquidez_e_estrutura_sem_gatilho_nao_confirma(self):
        zone = self._lab_zone()
        rid = zone["region_id"]
        smc = _smc_confirmada("BULLISH")
        market = _market(4025.0)
        # gatilho NAO confirmado
        p1, p2, p3 = self._patch_market(market, smc, {"confirmed": False})
        with p1, p2, p3:
            result = lab_zone_monitor.monitorar_zonas_lab(store=self.store, now=self.now)
        self.assertEqual(result["promoted"], 0)
        updated = self.store.get(rid)
        self.assertEqual(updated["region_status"], "AGUARDANDO_CONFIRMACAO")
        self.assertEqual(updated["structural_confirmations"], [])

    def test_promocao_cadeia_completa_e_executavel(self):
        zone = self._lab_zone(direction="COMPRA")
        rid = zone["region_id"]
        smc = _smc_confirmada("BULLISH")
        market = _market(4025.0)  # dentro da faixa [4020, 4030]
        trigger = {"confirmed": True, "trigger_time": "2026-08-24T11:55:00"}
        p1, p2, p3 = self._patch_market(market, smc, trigger)
        with p1, p2, p3:
            result = lab_zone_monitor.monitorar_zonas_lab(store=self.store, now=self.now)

        self.assertEqual(result["promoted"], 1)
        updated = self.store.get(rid)
        self.assertEqual(updated["region_status"], "CONFIRMADA")
        self.assertTrue(updated["structural_confirmations"])
        self.assertTrue(updated["valid_confirmations"])

        # Guard de execucao agora libera a zona (antes: REGION_NOT_CONFIRMED).
        preop = {
            "id": zone["pre_operation_id"],
            "pre_operation_id": zone["pre_operation_id"],
            "ativo": "GOLD_SPOT",
            "region_id": rid,
        }
        guard = validate_zone_for_execution(preop, store=self.store)
        self.assertTrue(guard["ok"], msg=f"guard bloqueou: {guard}")

    def test_promocao_nao_fabrica_status_diretamente(self):
        # Mesmo com gatilho confirmado, sem liquidez/estrutura NAO ha CONFIRMADA.
        zone = self._lab_zone()
        rid = zone["region_id"]
        market = _market(4025.0)
        p1, p2, p3 = self._patch_market(market, _smc_neutro(), {"confirmed": True})
        with p1, p2, p3:
            result = lab_zone_monitor.monitorar_zonas_lab(store=self.store, now=self.now)
        self.assertEqual(result["promoted"], 0)
        updated = self.store.get(rid)
        self.assertNotEqual(updated["region_status"], "CONFIRMADA")

    def test_invalidacao_por_preco(self):
        zone = self._lab_zone(direction="COMPRA", entry=4030.0, stop=4020.0)
        rid = zone["region_id"]
        # preco abaixo do invalidation_price (region_low=4020) invalida a zona BULLISH.
        market = _market(4015.0)
        p1, p2, p3 = self._patch_market(market, _smc_neutro(), {"confirmed": False})
        with p1, p2, p3:
            result = lab_zone_monitor.monitorar_zonas_lab(store=self.store, now=self.now)
        self.assertEqual(result["invalidated"], 1)
        updated = self.store.get(rid)
        self.assertEqual(updated["region_status"], "INVALIDADA")

    def test_duas_zonas_mesmo_simbolo_uma_unica_leitura_mt5(self):
        self._lab_zone(preop="PREOP-LAB-A")
        self._lab_zone(preop="PREOP-LAB-B", entry=4031.0, stop=4021.0, tp1=4046.0, tp2=4061.0)
        fake_load = MagicMock(return_value=_market(4025.0))
        p1, p2, p3 = self._patch_market(_market(4025.0), _smc_neutro(), {"confirmed": False})
        with patch.object(lab_zone_monitor, "load_execution_candles", fake_load), p2, p3:
            result = lab_zone_monitor.monitorar_zonas_lab(store=self.store, now=self.now)
        self.assertEqual(result["monitored"], 2)
        # Mesmo com 2 zonas do mesmo simbolo, MT5 e lido uma unica vez no ciclo.
        fake_load.assert_called_once()


if __name__ == "__main__":
    unittest.main()
