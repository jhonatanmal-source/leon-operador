import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace

from src import market_session_guard


class FakeMT5:
    SYMBOL_TRADE_MODE_DISABLED = 0

    def __init__(self, tick_time, connected=True, trade_allowed=True):
        self.tick_time = tick_time
        self.connected = connected
        self.trade_allowed = trade_allowed
        self.shutdown_calls = 0

    def initialize(self):
        return True

    def shutdown(self):
        self.shutdown_calls += 1

    def last_error(self):
        return (1, "Success")

    def terminal_info(self):
        return SimpleNamespace(connected=self.connected)

    def account_info(self):
        return SimpleNamespace(
            trade_allowed=self.trade_allowed,
            server="Broker-Test",
        )

    def symbol_select(self, symbol, enabled):
        return True

    def symbol_info(self, symbol):
        return SimpleNamespace(trade_mode=4)

    def symbol_info_tick(self, symbol):
        return SimpleNamespace(time=int(self.tick_time.timestamp()))


class MarketSessionGuardTests(unittest.TestCase):

    def test_account_permission_is_not_market_closure(self):
        now = datetime(2026, 9, 22, 9, 0, tzinfo=timezone.utc)
        result = market_session_guard.inspect_broker_session(
            now=now, mt5_module=FakeMT5(now, trade_allowed=False))
        self.assertFalse(result['open'])
        self.assertEqual(result['status'], 'BROKER_TRADING_BLOCKED')
        self.assertEqual(market_session_guard.operator_session_status(result), 'CONTA_SEM_PERMISSAO')

    def test_session_states_distinguish_technical_failure(self):
        for status in ('WEEKEND_CLOSED', 'DAILY_MARKET_PAUSE'):
            self.assertEqual(market_session_guard.operator_session_status({'status': status}), 'PAUSA_MERCADO')
        for status in ('MT5_DISCONNECTED', 'SYMBOL_UNAVAILABLE', 'NO_BROKER_TICK', 'BROKER_SYMBOL_DISABLED'):
            self.assertEqual(market_session_guard.operator_session_status({'status': status}), 'FALHA_TECNICA')

    def test_recent_broker_tick_opens_market(self):
        now = datetime(2026, 6, 19, 14, 0, tzinfo=timezone.utc)
        mt5 = FakeMT5(now - timedelta(seconds=20))

        result = market_session_guard.inspect_broker_session(
            now=now,
            stale_tick_seconds=180,
            mt5_module=mt5,
        )

        self.assertTrue(result["open"])
        self.assertEqual(result["status"], "MARKET_OPEN")

    def test_stale_weekday_tick_enters_daily_pause(self):
        now = datetime(2026, 6, 19, 22, 30, tzinfo=timezone.utc)
        mt5 = FakeMT5(now - timedelta(minutes=10))

        result = market_session_guard.inspect_broker_session(
            now=now,
            stale_tick_seconds=180,
            mt5_module=mt5,
        )

        self.assertFalse(result["open"])
        self.assertEqual(result["status"], "DAILY_MARKET_PAUSE")

    def test_weekend_is_closed_by_broker_tick(self):
        now = datetime(2026, 6, 20, 14, 0, tzinfo=timezone.utc)
        mt5 = FakeMT5(now - timedelta(hours=12))

        result = market_session_guard.inspect_broker_session(
            now=now,
            stale_tick_seconds=180,
            mt5_module=mt5,
        )

        self.assertFalse(result["open"])
        self.assertEqual(result["status"], "WEEKEND_CLOSED")

    def test_maintenance_runs_only_once_per_closed_window(self):
        now = datetime(2026, 6, 19, 22, 30, tzinfo=timezone.utc)
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "session.json"
            session = {
                "open": False,
                "status": "DAILY_MARKET_PAUSE",
                "reason": "pause",
                "checked_at": now.isoformat(),
                "symbol": "XAUUSD",
            }
            state = market_session_guard.register_session_status(session, path)
            state["closed_since"] = (
                now - timedelta(minutes=3)
            ).isoformat()

            self.assertTrue(
                market_session_guard.maintenance_is_due(
                    state,
                    delay_seconds=120,
                    now=now,
                )
            )
            state["maintenance_done"] = True
            self.assertFalse(
                market_session_guard.maintenance_is_due(
                    state,
                    delay_seconds=120,
                    now=now,
                )
            )


if __name__ == "__main__":
    unittest.main()
