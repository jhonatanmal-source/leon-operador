import json
import os
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace as NS
from unittest.mock import MagicMock
import pytest

from src import news_shield as n
from src import risk_control_agent as r


def test_no_news_source_blocks(monkeypatch):
    monkeypatch.setattr(n,'_load_events',lambda:([], 'NAO_CONFIGURADO'))
    assert not n.avaliar_news_shield()['approved']


def test_high_impact_not_dependent_on_known_event_name(monkeypatch):
    now=datetime.now(timezone.utc)
    event={'Date':now.isoformat(),'Importance':3,'Country':'United States','Event':'New economic release'}
    monkeypatch.setattr(n,'_load_events',lambda:([event], 'TRADING_ECONOMICS'))
    assert not n.avaliar_news_shield(now)['approved']


def test_bad_calendar_blocks(monkeypatch):
    monkeypatch.setattr(n,'_load_events',lambda:([{'Importance':'bad'}], 'CACHE'))
    assert not n.avaliar_news_shield()['approved']


def test_fresh_file_with_expired_coverage_blocks(tmp_path,monkeypatch):
    path=tmp_path/'calendar.json'
    path.write_text(json.dumps({'events':[], 'valid_from':'2020-01-01T00:00:00Z','valid_until':'2020-01-02T00:00:00Z'}))
    monkeypatch.setattr(n,'CACHE_FILE',path)
    monkeypatch.setattr(n,'MANUAL_EVENTS_FILE',tmp_path/'missing')
    monkeypatch.setattr(n,'_api_events',lambda:None)
    assert not n.avaliar_news_shield()['approved']


def test_stale_file_blocks_despite_coverage(tmp_path,monkeypatch):
    path=tmp_path/'calendar.json'; now=datetime.now(timezone.utc)
    path.write_text(json.dumps({'events':[], 'valid_from':(now-timedelta(days=1)).isoformat(),'valid_until':(now+timedelta(days=1)).isoformat()}))
    os.utime(path,(now.timestamp()-7*3600,)*2)
    monkeypatch.setattr(n,'CACHE_FILE',path)
    monkeypatch.setattr(n,'MANUAL_EVENTS_FILE',tmp_path/'missing')
    monkeypatch.setattr(n,'_api_events',lambda:None)
    assert not n.avaliar_news_shield()['approved']


def test_daily_history_error_blocks(monkeypatch):
    import sys
    m=MagicMock(); m.account_info.return_value=NS(balance=10000,equity=10000)
    m.history_deals_get.return_value=None
    monkeypatch.setitem(sys.modules,'mt5_safe',m)
    assert r.avaliar_limite_perda_diaria()['error']=='MT5_HISTORY_UNAVAILABLE'


def test_entry_commission_and_equity_included(monkeypatch):
    import sys
    m=MagicMock(); m.DEAL_TYPE_BALANCE=2
    m.account_info.return_value=NS(balance=9995,equity=9800)
    m.history_deals_get.return_value=[NS(type=0,entry=0,profit=0,commission=-5,swap=0,fee=0)]
    monkeypatch.setitem(sys.modules,'mt5_safe',m)
    result=r.avaliar_limite_perda_diaria()
    assert result['starting_balance']==10000
    assert result['realized_result']==-5
    assert not result['approved']


def test_weekly_feed_wrong_week_rejected(tmp_path,monkeypatch):
    monkeypatch.setattr(n,'FF_CACHE_FILE',tmp_path/'ff.json')
    response=MagicMock()
    response.json.return_value=[{'date':'2000-01-01T12:00:00Z','country':'USD','impact':'High','title':'Event'}]
    monkeypatch.setattr(n.requests,'get',lambda *a,**k:response)
    with pytest.raises(ValueError,match='week mismatch'):
        n._forex_factory_events()


def test_weekly_feed_failure_blocks(monkeypatch):
    monkeypatch.setenv('LEON_NEWS_SOURCE','forex_factory')
    def fail():
        raise ValueError('bad feed')
    monkeypatch.setattr(n,'_forex_factory_events',fail)
    assert not n.avaliar_news_shield()['approved']
