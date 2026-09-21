from copy import deepcopy
import pytest
from src.operational_evidence import select_elliott_direction, setup_decision, wave_liquidity_confirmation


@pytest.mark.parametrize('label',['CORRECAO','SEM_CONTAGEM','ONDA 5 CONCLUIDA','POSSIVEL ONDA 3'])
def test_count_is_context_not_entry_permission(label):
    h1=dict(label=label,direction='ALTA',valid=False,entry_eligible=False)
    original=deepcopy(h1)
    selected=select_elliott_direction(h1,{},'ALTA')
    assert setup_decision('COMPRA',selected,True,True,True)['approved']
    assert selected['valid'] is False and selected['entry_eligible'] is False
    assert h1==original


def test_smc_remains_the_entry_trigger():
    selected=select_elliott_direction(dict(direction='ALTA',valid=False),{},'ALTA')
    assert not setup_decision('COMPRA',selected,False,True,True)['approved']
    assert not setup_decision('COMPRA',selected,True,False,True)['approved']
    assert not setup_decision('COMPRA',selected,True,True,False)['approved']
    smc=dict(direction='BULLISH',liquidity={})
    assert not wave_liquidity_confirmation('COMPRA',selected,smc)['approved']
    smc['liquidity']=dict(direction='BULLISH',index=10)
    assert wave_liquidity_confirmation('COMPRA',selected,smc)['approved']


def test_does_not_choose_degree_to_agree_with_smc():
    selected=select_elliott_direction(dict(direction='BAIXA'),dict(direction='ALTA'),'BAIXA')
    assert selected['direction']=='BAIXA' and selected['entry_timeframe']=='H1'
    assert not setup_decision('COMPRA',selected,True,True,True)['approved']


def test_neutral_h1_selects_m15_direction_without_count_gate():
    selected=select_elliott_direction(dict(direction='BAIXA'),dict(direction='ALTA',valid=False),'LATERAL')
    assert selected['entry_timeframe']=='M15'
    assert setup_decision('COMPRA',selected,True,True,True)['approved']


def test_missing_direction_is_not_fabricated():
    selected=select_elliott_direction({}, {}, 'LATERAL')
    assert not setup_decision('COMPRA',selected,True,True,True)['approved']
