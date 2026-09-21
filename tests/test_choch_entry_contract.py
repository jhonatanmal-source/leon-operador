from copy import deepcopy
import pytest
from src import interest_zone_engine as zones
from src.real_zone_cycle import run_real_zone_cycle, detect_zone
from src.smc_entry_guard import confirmed_shift_direction, validate_smc_entry


def shift_fixture():
    from test_real_zone_cycle import fixture
    m15,m5,smc,stamp=fixture()
    event=dict(smc['bos_event'],type='CHOCH_BULLISH')
    smc.update(bos_event=None,choch_event=event,direction=None,events=[event])
    return m15,m5,smc,stamp


def test_choch_alone_is_not_an_entry(tmp_path):
    m15,m5,smc,stamp=shift_fixture()
    assert not validate_smc_entry('COMPRA','NEUTRO','SEM_BOS','CHOCH_BULLISH')['approved']
    first=run_real_zone_cycle('TEST',m15,m5,smc,store=zones.InterestZoneStore(tmp_path/'zones.json'))
    assert first['created']==1 and first['confirmed_region'] is None
    assert confirmed_shift_direction(smc,first['confirmed_region'])=='AGUARDAR'


def test_weak_shift_cannot_create_zone():
    m15,m5,smc,stamp=shift_fixture()
    smc['choch_event']['displacement']=False
    assert detect_zone('TEST',m15,m5,smc)[0] is None


@pytest.mark.parametrize('change',['expired','invalidated','lab','wrong_symbol','wrong_direction','no_confirmation','associated'])
def test_reversal_keeps_canonical_guards(tmp_path,monkeypatch,change):
    from test_real_zone_cycle import retest
    m15,m5,smc,stamp=shift_fixture()
    store=zones.InterestZoneStore(tmp_path/'zones.json')
    run_real_zone_cycle('TEST',m15,m5,smc,store=store)
    zone=run_real_zone_cycle('TEST',m15,retest(m5,stamp),smc,store=store)['confirmed_region']
    assert zone is not None
    monkeypatch.setattr(zones,'InterestZoneStore',lambda:store)
    args=dict(region_id=zone['region_id'],symbol='TEST')
    assert validate_smc_entry('COMPRA','NEUTRO','SEM_BOS','CHOCH_BULLISH',**args)['approved']
    if change=='expired':zone['expires_at']='2000-01-01T00:00:00+00:00'
    if change=='invalidated':zone['region_invalidated']=True
    if change=='lab':zone['zone_source']='LABORATORIO'
    if change=='wrong_symbol':args['symbol']='OTHER'
    if change=='wrong_direction':zone['region_direction']='BEARISH'
    if change=='no_confirmation':zone['structural_confirmations']=[];zone['valid_confirmations']=[]
    if change=='associated':zone['pre_operation_id']='OTHER'
    # Write a corrupted fixture directly, avoiding store provenance protections.
    import json
    store.path.write_text(json.dumps([zone]))
    assert not validate_smc_entry('COMPRA','NEUTRO','SEM_BOS','CHOCH_BULLISH',**args)['approved']


def test_shift_must_match_current_event(tmp_path):
    from test_real_zone_cycle import retest
    m15,m5,smc,stamp=shift_fixture()
    store=zones.InterestZoneStore(tmp_path/'zones.json')
    run_real_zone_cycle('TEST',m15,m5,smc,store=store)
    zone=run_real_zone_cycle('TEST',m15,retest(m5,stamp),smc,store=store)['confirmed_region']
    assert confirmed_shift_direction(smc,zone)=='COMPRA'
    altered=deepcopy(smc);altered['choch_event']['time']='DIFFERENT_EVENT'
    assert confirmed_shift_direction(altered,zone)=='AGUARDAR'


def test_bearish_shift_reaches_canonical_entry(tmp_path, monkeypatch):
    from test_real_zone_cycle import retest
    from src.canonical_smc_entry import confirmed_zone_entry
    m15,m5,smc,stamp=shift_fixture()
    def mirror(c):
        return dict(c,open=220-c['open'],close=220-c['close'],high=220-c['low'],low=220-c['high'])
    later=[mirror(c) for c in retest(m5,stamp)]
    m15=[mirror(c) for c in m15]
    m5=[mirror(c) for c in m5]
    event=dict(smc['choch_event'],direction='BEARISH',type='CHOCH_BEARISH',level=116)
    smc.update(choch_event=event,events=[event],pivots=[dict(type='LOW',price=110),dict(type='LOW',price=108)])
    store=zones.InterestZoneStore(tmp_path/'zones.json')
    assert run_real_zone_cycle('TEST',m15,m5,smc,store=store)['created']==1
    zone=run_real_zone_cycle('TEST',m15,later,smc,store=store)['confirmed_region']
    assert confirmed_shift_direction(smc,zone)=='VENDA'
    monkeypatch.setattr(zones,'InterestZoneStore',lambda:store)
    assert validate_smc_entry('VENDA','NEUTRO','SEM_BOS','CHOCH_BEARISH',region_id=zone['region_id'],symbol='TEST')['approved']
    plan,reason=confirmed_zone_entry('VENDA','TEST',m15,later,2,store=store)
    assert plan is not None,reason
    assert plan.model=='CHOCH_ORDER_BLOCK_RETEST'
    assert plan[1]==120
