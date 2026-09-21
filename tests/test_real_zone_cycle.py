from copy import deepcopy
from datetime import datetime, timedelta, timezone

import pytest
from src.real_zone_cycle import detect_zone, run_real_zone_cycle, SOURCE
from src.interest_zone_engine import InterestZoneStore, validate_zone_for_execution
from src.canonical_smc_entry import confirmed_zone_entry
from src.operational_evidence import wave_liquidity_confirmation, setup_decision


def fixture():
    start=datetime(2026,9,15)
    stamp=lambda minutes:(start+timedelta(minutes=minutes)).isoformat()
    m15=[dict(time=stamp(i*15),open=104,high=112 if i==1 else 110,low=104,close=104) for i in range(12)]
    m15[8].update(open=102,high=103,low=100,close=101)
    m15[9].update(open=102,high=106,low=101,close=105)
    m15[10].update(open=105,high=107,low=104,close=106)
    m5=[dict(time=stamp(t),open=105,high=107,low=104,close=105) for t in (145,150,155,160)]
    event=dict(index=9,time=m15[9]['time'],type='BOS_BULLISH',direction='BULLISH',displacement=True,level=104)
    smc=dict(direction='BULLISH',bos_event=event,events=[event],liquidity={'direction':None},
             pivots=[dict(type='HIGH',price=110),dict(type='HIGH',price=112)])
    return m15,m5,smc,stamp


def retest(m5,stamp):
    return m5+[dict(time=stamp(165),open=101,low=100.5,high=103.5,close=103),
               dict(time=stamp(170),open=103,low=103,high=103,close=103)]


def test_prospective_cycle_reaches_entry_without_fvg(tmp_path):
    m15,m5,smc,stamp=fixture();store=InterestZoneStore(tmp_path/'zones.json')
    first=run_real_zone_cycle('TEST',m15,m5,smc,store=store)
    assert first['created']==1 and first['confirmed_region'] is None
    zone=store.list()[0]
    assert zone['zone_source']==SOURCE and not zone['structural_confirmations']
    assert not validate_zone_for_execution({'region_id':zone['region_id'],'ativo':'TEST'},store=store)['ok']
    second=run_real_zone_cycle('TEST',m15,retest(m5,stamp),smc,store=store)
    confirmed=second['confirmed_region']
    assert confirmed is not None
    plan,reason=confirmed_zone_entry('COMPRA','TEST',m15,retest(m5,stamp),2,store=store)
    assert plan is not None,reason
    assert plan.region_id==confirmed['region_id'] and plan[1]==100
    elliott=dict(valid=True,entry_eligible=True,direction='ALTA')
    wave=wave_liquidity_confirmation('COMPRA',elliott,smc,confirmed)
    assert wave['structural_zone_confirmed'] and not wave['liquidity_aligned']
    assert setup_decision('COMPRA',elliott,True,wave['approved'],True)['approved']
    assert not setup_decision('COMPRA',elliott,True,wave['approved'],False)['approved']


def test_repeat_same_bar_does_not_renew_confirmation(tmp_path):
    m15,m5,smc,stamp=fixture();store=InterestZoneStore(tmp_path/'zones.json')
    now=datetime.now(timezone.utc)
    run_real_zone_cycle('TEST',m15,m5,smc,store=store,now=now)
    result=run_real_zone_cycle('TEST',m15,retest(m5,stamp),smc,store=store,now=now+timedelta(seconds=1))
    expiry=result['confirmed_region']['expires_at']
    again=run_real_zone_cycle('TEST',m15,retest(m5,stamp),smc,store=store,now=now+timedelta(seconds=2))
    assert again['confirmed_region']['expires_at']==expiry
    assert len(again['confirmed_region']['structural_confirmations'])==1


@pytest.mark.parametrize('change',['no_displacement','wrong_time','wrong_direction','no_break','old_bos','already_touched'])
def test_rejects_unverifiable_or_retroactive_origins(change):
    m15,m5,smc,stamp=fixture()
    if change=='no_displacement':smc['bos_event']['displacement']=False
    if change=='wrong_time':smc['bos_event']['time']='invalid'
    if change=='wrong_direction':smc['bos_event']['direction']='BEARISH'
    if change=='no_break':smc['bos_event']['level']=200
    if change=='old_bos':smc['bos_event']['index']=1
    if change=='already_touched':m5[-2]['low']=101
    assert detect_zone('TEST',m15,m5,smc)[0] is None


@pytest.mark.parametrize('change',['wick_invalidated','opposite_structure','expiry'])
def test_terminal_zones_never_authorize(tmp_path,change):
    m15,m5,smc,stamp=fixture();store=InterestZoneStore(tmp_path/'zones.json')
    now=datetime.now(timezone.utc)
    run_real_zone_cycle('TEST',m15,m5,smc,store=store,now=now)
    new=retest(m5,stamp)
    if change=='wick_invalidated':new[-2]['low']=99
    if change=='opposite_structure':smc['events'].append(dict(time=stamp(165),direction='BEARISH',type='CHOCH_BEARISH'))
    if change=='expiry':now+=timedelta(hours=5)
    result=run_real_zone_cycle('TEST',m15,new,smc,store=store,now=now)
    assert result['confirmed_region'] is None
    assert store.list()[0]['region_status'] in ('INVALIDADA','EXPIRADA')


def test_creation_candle_cannot_retroactively_confirm(tmp_path):
    m15,m5,smc,stamp=fixture();store=InterestZoneStore(tmp_path/'zones.json')
    run_real_zone_cycle('TEST',m15,m5,smc,store=store)
    m5[-1].update(open=101,low=100.5,high=103.5,close=103)
    m5.append(dict(time=stamp(165),open=103,high=103,low=103,close=103))
    result=run_real_zone_cycle('TEST',m15,m5,smc,store=store)
    assert result['confirmed_region'] is None


def test_lab_zone_never_relabelled(tmp_path):
    m15,m5,smc,stamp=fixture();store=InterestZoneStore(tmp_path/'zones.json')
    store.upsert(dict(region_id='LAB',symbol='TEST',zone_source='LABORATORIO',region_status='CONFIRMADA'))
    run_real_zone_cycle('TEST',m15,m5,smc,store=store)
    assert store.get('LAB')['zone_source']=='LABORATORIO'


def test_bearish_symmetry(tmp_path):
    m15,m5,smc,stamp=fixture()
    def mirror(c):return dict(c,open=220-c['open'],close=220-c['close'],high=220-c['low'],low=220-c['high'])
    m15=[mirror(c) for c in m15];old=m5;m5=[mirror(c) for c in m5]
    event=dict(smc['bos_event'],direction='BEARISH',type='BOS_BEARISH',level=116)
    smc.update(direction='BEARISH',bos_event=event,events=[event],pivots=[dict(type='LOW',price=110),dict(type='LOW',price=108)])
    store=InterestZoneStore(tmp_path/'zones.json')
    assert run_real_zone_cycle('TEST',m15,m5,smc,store=store)['created']==1
    new=[mirror(c) for c in retest(old,stamp)]
    result=run_real_zone_cycle('TEST',m15,new,smc,store=store)
    assert result['confirmed_region'] is not None
    assert confirmed_zone_entry('VENDA','TEST',m15,new,2,store=store)[0] is not None
