from datetime import datetime, timezone
from types import SimpleNamespace as NS
from unittest.mock import MagicMock

import pytest
from src import ftmo_guard as g


def test_profile_required():
    assert not g.evaluate_limits("pending", 10000, 10000, 10000, 10000)["approved"]


@pytest.mark.parametrize("profile,daily,total", [
    ("free_trial_1_step", 9900, 9500),
    ("free_trial_2_step", 9700, 9000),
])
def test_product_floors(profile, daily, total):
    r = g.evaluate_limits(profile, 10000, 10200, 10500, 10200)
    assert r["daily_floor"] == daily
    assert r["total_floor"] == total


def test_open_risk_and_cost_buffer_blocks_before_loss_limit():
    r = g.evaluate_limits("free_trial_2_step", 10000, 10000, 10000, 9900, 91)
    assert not r["approved"]
    assert r["projected_equity"] == 9799


@pytest.mark.parametrize("value", [float("nan"), float("inf"), -1, 0])
def test_bad_initial_capital_blocks(value):
    assert not g.evaluate_limits("free_trial_2_step", value, 10000, 10000, 10000)["approved"]


def deal(iso, net, entry=1, order=1, kind=0, commission=0):
    return NS(time=datetime.fromisoformat(iso).timestamp(), profit=net, commission=commission,
              swap=0, fee=0, type=kind, entry=entry, order=order)


@pytest.mark.parametrize("now,before,after", [
    ("2026-07-02T01:00:00+00:00", "2026-07-01T21:59:00+00:00", "2026-07-01T22:01:00+00:00"),
    ("2026-01-02T01:00:00+00:00", "2026-01-01T22:59:00+00:00", "2026-01-01T23:01:00+00:00"),
])
def test_prague_boundary_in_summer_and_winter(now, before, after):
    trades = [deal("2020-01-01T00:00:00+00:00", 10000, kind=2), deal(before, 100), deal(after, -10, entry=0, order=2, commission=-2)]
    day, peak, entries = g.ledger_state(trades, 10000, 10088, datetime.fromisoformat(now))
    assert (day, peak, entries) == (10100, 10100, 1)


def test_trailing_uses_midnight_not_intraday_peak():
    trades = [deal("2020-01-01T00:00:00+00:00", 10000, kind=2), deal("2026-07-01T10:00:00+00:00", 500), deal("2026-07-01T12:00:00+00:00", -400)]
    assert g.ledger_state(trades, 10000, 10100, datetime(2026,7,2,tzinfo=timezone.utc))[:2] == (10100,10100)


def test_missing_history_blocks():
    with pytest.raises(ValueError, match="HISTORY_UNAVAILABLE"):
        g.ledger_state(None, 10000, 10000, datetime.now(timezone.utc))


def test_incomplete_history_blocks():
    with pytest.raises(ValueError, match="BALANCE_MISMATCH"):
        g.ledger_state([deal("2020-01-01T00:00:00+00:00", 10000, kind=2)], 10000, 9999, datetime.now(timezone.utc))


def test_balance_adjustment_blocks():
    with pytest.raises(ValueError, match="BALANCE_ADJUSTMENT"):
        g.ledger_state([deal("2026-07-01T12:00:00+00:00", 500, kind=2)], 10000,10500, datetime.now(timezone.utc))


@pytest.fixture
def connected(tmp_path, monkeypatch):
    path=tmp_path/'config.ini'
    path.write_text('[FTMO]\nprofile=free_trial_2_step\ninitial_balance=10000\naccount_login=123\naccount_server=FTMO-Demo\n')
    monkeypatch.setattr(g, 'CONFIG_FILE', path)
    m=MagicMock()
    m.ACCOUNT_TRADE_MODE_DEMO=0
    m.account_info.return_value=NS(login=123,server='FTMO-Demo',trade_mode=0,trade_allowed=True,trade_expert=True,balance=10000,equity=10000)
    m.terminal_info.return_value=NS(trade_allowed=True,tradeapi_disabled=False)
    m.history_deals_get.return_value=[deal("2020-01-01T00:00:00+00:00", 10000, kind=2)]
    m.positions_get.return_value=[]
    m.orders_get.return_value=[]
    return m


def test_empty_demo_readiness_without_sending(connected):
    assert g.evaluate_ftmo_entry(connected)['approved']
    connected.order_send.assert_not_called()


@pytest.mark.parametrize('field,value,reason', [
    ('login',321,'ACCOUNT_CHANGED'),('trade_mode',2,'REAL_ACCOUNT'),('trade_allowed',False,'ALGO_TRADING')])
def test_identity_or_permission_change_blocks(connected,field,value,reason):
    setattr(connected.account_info.return_value,field,value)
    assert reason in g.evaluate_ftmo_entry(connected)['reason']


def test_unknown_positions_blocks(connected):
    connected.positions_get.return_value=None
    assert not g.evaluate_ftmo_entry(connected)['approved']


def test_pending_orders_block(connected):
    connected.orders_get.return_value=[NS()]
    assert not g.evaluate_ftmo_entry(connected)['approved']


def test_new_request_exceeding_budget_blocks(connected):
    connected.symbol_info_tick.return_value=NS(time=datetime.now(timezone.utc).timestamp())
    connected.order_calc_profit.return_value=-250
    request={'symbol':'XAUUSD','sl':4000,'tp':4400,'price':4100,'type':0,'volume':.01}
    assert not g.evaluate_ftmo_entry(connected,request)['approved']


def test_missing_risk_conversion_blocks(connected):
    connected.symbol_info_tick.return_value=NS(time=datetime.now(timezone.utc).timestamp())
    connected.order_calc_profit.return_value=None
    request={'symbol':'XAUUSD','sl':4000,'tp':4400,'price':4100,'type':0,'volume':.01}
    assert not g.evaluate_ftmo_entry(connected,request)['approved']
