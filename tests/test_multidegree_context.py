from copy import deepcopy
import ast
from pathlib import Path
import pytest
from src.multidegree_context import describe_multidegree, diagnose_candidate, evaluate_daytrade_context
from src.operational_evidence import select_elliott_direction, setup_decision, wave_liquidity_confirmation


@pytest.mark.parametrize('macro,lower,correction,resume',[
    ('ALTA','BAIXA','VENDA','COMPRA'),('BAIXA','ALTA','COMPRA','VENDA')])
def test_lower_correction_does_not_reverse_macro(macro,lower,correction,resume):
    top=dict(h4_bias=macro,h1_contexto=macro,m15_gatilho=lower,macro_semanal=macro)
    before=deepcopy(top)
    result=describe_multidegree(top)
    assert result['macro_direction']==macro
    assert result['phase']=='POSSIVEL_CORRECAO_NO_MENOR'
    assert result['reversal_confirmed'] is False
    assert diagnose_candidate(top,correction)['intent']=='CORRECAO_CONTRA_TENDENCIA_MAIOR'
    assert diagnose_candidate(top,resume)['intent']=='RETOMADA_A_CONFIRMAR_SMC'
    assert not result['entry_authorized']
    assert top==before


def test_micro_alignment_does_not_claim_h1_correction_finished():
    result=describe_multidegree(dict(h4_bias='ALTA',h1_contexto='BAIXA',m15_gatilho='ALTA'))
    assert result['phase']=='MICRO_A_FAVOR_MACRO_H1_AINDA_CONTRARIO'
    assert result['macro_direction']=='ALTA' and result['h1_direction']=='BAIXA'
    assert not result['entry_authorized']


def test_neutral_lower_is_not_filled_using_smc_candidate():
    result=diagnose_candidate(dict(h4_bias='BAIXA',h1_contexto='LATERAL',m15_gatilho='LATERAL'),'COMPRA')
    assert result['phase']=='MENOR_SEM_DIRECAO'
    assert result['m15_direction']=='LATERAL'
    assert result['intent']=='SEM_ALINHAMENTO_COM_MOVIMENTO_MENOR'


def test_missing_macro_does_not_invent_direction():
    result=describe_multidegree(dict(h4_bias='LATERAL',h1_contexto='LATERAL',m15_gatilho='ALTA'))
    assert result['macro_direction'] is None and not result['entry_authorized']


def test_h1_can_supply_macro_when_h4_has_no_direction():
    result=describe_multidegree(dict(h4_bias='LATERAL',h1_contexto='ALTA',m15_gatilho='BAIXA'))
    assert result['macro_timeframe']=='H1'
    assert result['phase']=='POSSIVEL_CORRECAO_NO_MENOR'


def test_present_two_of_three_rule_blocks_correction_not_trend():
    top=dict(h4_bias='ALTA',h1_contexto='ALTA',m15_gatilho='BAIXA',macro_semanal='ALTA')
    assert not diagnose_candidate(top,'VENDA')['current_policy']['approved']
    assert diagnose_candidate(top,'COMPRA')['current_policy']['approved']


@pytest.mark.parametrize('macro,lower,correction,resume',[
    ('ALTA','BAIXA','VENDA','COMPRA'),('BAIXA','ALTA','COMPRA','VENDA')])
def test_daytrade_can_trade_both_legs_only_with_smc(macro,lower,correction,resume):
    top=dict(h4_bias=macro,h1_contexto=macro,m15_gatilho=lower,macro_semanal=macro)
    context=select_elliott_direction(dict(direction=macro,valid=False,entry_eligible=False),
        dict(direction=lower,valid=False,entry_eligible=False),macro,top_down=top)
    assert set(context['allowed_directions'])=={macro,lower}
    for direction in (correction,resume):
        policy=evaluate_daytrade_context(top,direction)
        assert policy['approved']
        assert setup_decision(direction,context,True,True,policy['approved'])['approved']
        assert not setup_decision(direction,context,False,True,policy['approved'])['approved']
        assert not setup_decision(direction,context,True,False,policy['approved'])['approved']
        assert not wave_liquidity_confirmation(direction,context,{'liquidity':{}})['approved']
    assert evaluate_daytrade_context(top,correction)['mode']=='CORRECAO'
    assert evaluate_daytrade_context(top,resume)['mode']=='TENDENCIA'


def test_aligned_timeframes_do_not_authorize_arbitrary_opposite_trade():
    top=dict(h4_bias='ALTA',h1_contexto='ALTA',m15_gatilho='ALTA')
    context=select_elliott_direction(dict(direction='ALTA'),{},'ALTA',top_down=top)
    assert not setup_decision('VENDA',context,True,True,True)['approved']
    assert not evaluate_daytrade_context(top,'VENDA')['approved']


@pytest.mark.parametrize('direction',['COMPRA','VENDA','AGUARDAR'])
def test_no_macro_means_no_synthetic_correction(direction):
    top=dict(h4_bias='LATERAL',h1_contexto='LATERAL',m15_gatilho='ALTA')
    assert not evaluate_daytrade_context(top,direction)['approved']


def test_analysis_and_executor_use_same_daytrade_policy():
    src=Path(__file__).resolve().parents[1]/'src'
    for name in ('leon.py','mt5_order_executor.py'):
        tree=ast.parse((src/name).read_text(encoding='utf-8-sig'))
        imports=[n for n in ast.walk(tree) if isinstance(n,ast.ImportFrom)
                 and n.module=='src.multidegree_context']
        assert any(a.name=='evaluate_daytrade_context' for n in imports for a in n.names)
        calls=[n.func.id for n in ast.walk(tree) if isinstance(n,ast.Call) and isinstance(n.func,ast.Name)]
        assert 'evaluate_daytrade_context' in calls
        assert 'evaluate_timeframe_policy' not in calls


@pytest.mark.parametrize('macro,h1,direction', [('BAIXA','ALTA','COMPRA'),('ALTA','BAIXA','VENDA')])
def test_h1_correction_is_not_erased_by_lateral_m15(macro,h1,direction):
    top=dict(h4_bias=macro,h1_contexto=h1,m15_gatilho='LATERAL',macro_semanal=macro)
    policy=evaluate_daytrade_context(top,direction)
    context=select_elliott_direction(dict(direction=h1),dict(direction=h1),h1,top_down=top)
    assert policy['approved'] and policy['mode']=='CORRECAO'
    assert setup_decision(direction,context,True,True,policy['approved'])['approved']
    assert not setup_decision(direction,context,True,False,policy['approved'])['approved']
