import ast
from pathlib import Path
from unittest.mock import patch

import pytest
from src.canonical_smc_entry import confirmed_zone_entry, zone_retest_levels


class Store:
    def __init__(self,zone):self.zone=zone
    def list(self):return [self.zone]
    def get(self,region_id):return self.zone if region_id==self.zone['region_id'] else None


def fixture(buy=True):
    zone=dict(region_id='TEST-ONLY',symbol='TEST',region_type='BULLISH_ORDER_BLOCK',
              region_direction='BULLISH',region_low=100,region_high=102,invalidation_price=99,
              target_prices=[108,110],region_valid=True,region_invalidated=False,region_status='CONFIRMADA',
              structural_confirmations=[{'type':'BOS','test':True}],monitor_timeline=[{'type':'RETEST','test':True}],
              fvg_present=False)
    bars=[dict(time=i,open=103,high=104,low=102,close=103) for i in range(7)]
    bars[-2]=dict(time=5,open=101,low=100.5,high=103.5,close=103)
    if not buy:
        for k in ('region_low','region_high'):
            zone[k]=200-zone[k]
        zone['region_low'],zone['region_high']=zone['region_high'],zone['region_low']
        zone.update(region_direction='BEARISH',region_type='BEARISH_ORDER_BLOCK',invalidation_price=101,
                    target_prices=[92,90])
        bars=[dict(time=c['time'],open=200-c['open'],close=200-c['close'],high=200-c['low'],low=200-c['high']) for c in bars]
    return zone,bars


@pytest.mark.parametrize('buy',[True,False])
def test_confirmed_order_block_does_not_require_fvg(buy):
    zone,bars=fixture(buy)
    plan,reason=confirmed_zone_entry('COMPRA' if buy else 'VENDA','TEST',bars,bars,1.0,store=Store(zone))
    assert plan is not None,reason
    assert len(plan)==5 and plan.region_id=='TEST-ONLY'
    assert plan.model=='ORDER_BLOCK_RETEST'
    assert plan[1]==zone['invalidation_price']
    assert plan.evidence['fvg_required'] is False


@pytest.mark.parametrize('change', ['unconfirmed','invalidated','no_confirmation','no_timeline','expired','associated','wrong_symbol','wrong_direction','lab','replay'])
def test_cannot_bypass_existing_zone_guards(change):
    zone,bars=fixture()
    if change=='unconfirmed':zone['region_status']='IDENTIFICADA'
    if change=='invalidated':zone['region_invalidated']=True
    if change=='no_confirmation':zone['structural_confirmations']=[]
    if change=='no_timeline':zone['monitor_timeline']=[]
    if change=='expired':zone['expires_at']='2000-01-01T00:00:00+00:00'
    if change=='associated':zone['pre_operation_id']='OTHER'
    if change=='wrong_symbol':zone['symbol']='OTHER'
    if change=='wrong_direction':zone['region_direction']='BEARISH'
    if change=='lab':zone['zone_source']='LABORATORIO'
    if change=='replay':zone['replay_run_id']='TEST-REPLAY'
    assert confirmed_zone_entry('COMPRA','TEST',bars,bars,1,store=Store(zone))[0] is None


@pytest.mark.parametrize('change',['no_touch','wrong_reaction','invalidated_wick','missing_stop','wrong_stop','extended','no_targets'])
def test_requires_retest_reaction_and_technical_risk(change):
    zone,bars=fixture()
    if change=='no_touch':bars[-2].update(low=103,high=104,open=103,close=104)
    if change=='wrong_reaction':bars[-2].update(open=103,close=101)
    if change=='invalidated_wick':bars[-2]['low']=98
    if change=='missing_stop':zone['invalidation_price']=None
    if change=='wrong_stop':zone['invalidation_price']=101
    if change=='extended':bars[-2].update(close=106,high=107)
    if change=='no_targets':zone['target_prices']=[]
    assert zone_retest_levels(zone,'COMPRA',bars,bars,1)[0] is None


def test_rr_not_manufactured_by_moving_stop():
    zone,bars=fixture()
    plan,reason=zone_retest_levels(zone,'COMPRA',bars,bars,2)
    assert plan is None and reason=='INSUFFICIENT_TECHNICAL_TARGETS_AT_RR'
    assert zone['invalidation_price']==99


def test_forming_bar_cannot_create_reaction():
    zone,bars=fixture()
    bars[-1]=dict(time=6,open=100,low=98,high=150,close=149)
    assert zone_retest_levels(zone,'COMPRA',bars,bars,1)[0] is not None


def test_full_entry_engine_uses_canonical_route_without_calling_fvg():
    import entry_price_engine as entry
    zone,bars=fixture()
    plan,_=zone_retest_levels(zone,'COMPRA',bars,bars,1)
    with patch.object(entry,'_minimum_operational_rr',return_value=1),patch.object(entry,'_learning_execution_enabled',return_value=False), \
         patch.object(entry,'refine_m15_m5',return_value={'ok':True,'m15':bars,'m5':bars,'trigger':{'confirmed':False}}), \
         patch.object(entry,'confirmed_zone_entry',return_value=(plan,'READY')), \
         patch.object(entry,'build_smc_trade_levels',side_effect=AssertionError('FVG must not be required')):
        result=entry.calcular_entrada('COMPRA',110,99,symbol='TEST')
    assert result is plan


def test_pipeline_propagates_canonical_region():
    tree=ast.parse((Path(__file__).parents[1]/'src/leon.py').read_text())
    calls=[n for n in ast.walk(tree) if isinstance(n,ast.Call) and isinstance(n.func,ast.Name)
           and n.func.id=='registrar_pre_operacao']
    assert any(k.arg=='region_id' and 'structural_region' in ast.unparse(k.value) for c in calls for k in c.keywords)
