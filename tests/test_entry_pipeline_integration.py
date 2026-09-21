"""Real pipeline through executor selection; market I/O mocked, no orders sent."""
import ast
import csv
import pytest
from datetime import datetime, timezone, timedelta
from pathlib import Path

from src import interest_zone_engine as zones
from src import canonical_smc_entry as canonical
from src import operational_evidence as evidence
from src import pre_operation_engine as preop
from src.real_zone_cycle import run_real_zone_cycle
from src.multidegree_context import evaluate_daytrade_context


@pytest.mark.parametrize('shift',[False,True])
def test_confirmed_h1_correction_reaches_executor_selection(tmp_path, monkeypatch,shift):
    from test_real_zone_cycle import fixture, retest
    import entry_price_engine as entry
    m15,m5,smc,stamp=fixture()
    if shift:
        event=dict(smc['bos_event'],type='CHOCH_BULLISH')
        smc.update(bos_event=None,choch_event=event,direction=None,events=[event])
    store=zones.InterestZoneStore(tmp_path/'zones.json')
    run_real_zone_cycle('TEST',m15,m5,smc,store=store)
    m5=retest(m5,stamp)
    result=run_real_zone_cycle('TEST',m15,m5,smc,store=store)
    assert result['confirmed_region'] is not None
    monkeypatch.setattr(zones,'InterestZoneStore',lambda:store)
    monkeypatch.setattr(canonical,'InterestZoneStore',lambda:store)
    monkeypatch.setattr(entry,'_minimum_operational_rr',lambda:2)
    monkeypatch.setattr(entry,'_learning_execution_enabled',lambda:False)
    monkeypatch.setattr(entry,'refine_m15_m5',lambda *args,**kw:dict(ok=True,m15=m15,m5=m5,trigger={'confirmed':False}))
    trace={}
    plan=entry.calcular_entrada('COMPRA',112,100,symbol='TEST',diagnostics=trace)
    assert plan is not None and trace['stage']=='ENTRY_READY'
    assert trace['region_id']==plan.region_id
    monkeypatch.setattr(preop,'DATA_DIR',tmp_path)
    monkeypatch.setattr(preop,'PRE_OPERATION_FILE',tmp_path/'preops.csv')
    monkeypatch.setattr(preop,'_rr_minimo_operacional',lambda:2)
    monkeypatch.setattr(preop,'_aprendizado_operacional_ativo',lambda:False)
    monkeypatch.setattr(evidence,'DATA',tmp_path)
    top=dict(h4_bias='BAIXA',h1_contexto='ALTA',m15_gatilho='LATERAL',macro_semanal='BAIXA')
    context=evidence.select_elliott_direction(dict(direction='ALTA',label='CORRECAO',valid=False,entry_eligible=False),
        dict(direction='ALTA'),'ALTA',top_down=top)
    wave=evidence.wave_liquidity_confirmation('COMPRA',context,smc,result['confirmed_region'])
    policy=evaluate_daytrade_context(top,'COMPRA')
    from src.smc_entry_guard import validate_smc_entry, confirmed_shift_direction
    smc_label,bos,choch=('NEUTRO','SEM_BOS','CHOCH_BULLISH') if shift else ('BULLISH','BOS_BULLISH','SEM_CHOCH')
    if shift:
        assert confirmed_shift_direction(smc,result['confirmed_region'])=='COMPRA'
    guard=validate_smc_entry('COMPRA',smc_label,bos,choch,region_id=plan.region_id,symbol='TEST')
    decision=evidence.setup_decision('COMPRA',context,guard['approved'],wave['approved'],policy['approved'])
    assert decision['approved']
    operation=preop.registrar_pre_operacao('TEST','COMPRA','SETUP MODERADO',plan,smc_label,
        'CORRECAO',bos,choch,'BAIXA',0,context_mode='CORRECAO',region_id=plan.region_id)
    assert operation['status']=='ABERTO'
    decision['entry_diagnostics']=trace
    decision['entry_model']=plan.model
    decision['timeframe_details']={'policy':policy}
    evidence.save_setup_evidence(operation,decision)
    assert evidence.validate_setup_evidence(operation)['ok']
    assert zones.validate_zone_for_execution(operation,store=store)['ok']
    source=Path(__file__).resolve().parents[1]/'src'/'mt5_order_executor.py'
    function=next(n for n in ast.parse(source.read_text()).body if isinstance(n,ast.FunctionDef) and n.name=='_ultima_pre_operacao_aberta')
    namespace=dict(PRE_OPERATION_FILE=preop.PRE_OPERATION_FILE,csv=csv,datetime=datetime,
        validate_setup_evidence=evidence.validate_setup_evidence,learning_statistics=evidence.learning_statistics,
        _pre_operacao_ja_executada=lambda identifier:False,VERSION=evidence.VERSION)
    exec(compile(ast.Module(body=[function],type_ignores=[]),str(source),'exec'),namespace)
    selected=namespace['_ultima_pre_operacao_aberta']()
    assert selected['id']==operation['id'] and selected['_selection']['samples']==0
    assert selected['entry_model']==plan.model
    assert selected['context_mode']=='CORRECAO'
    assert validate_smc_entry('COMPRA',smc_label,bos,choch,region_id=plan.region_id,symbol='TEST',pre_operation_id=selected['id'])['approved']
    assert not evidence.validate_setup_evidence(operation,now=datetime.now(timezone.utc)+timedelta(seconds=181))['ok']
    invalid=store.get(plan.region_id);invalid['region_invalidated']=True;store.upsert(invalid)
    assert not zones.validate_zone_for_execution(operation,store=store)['ok']


def test_entry_rejection_records_actual_stage(monkeypatch):
    import entry_price_engine as entry
    monkeypatch.setattr(entry,'_minimum_operational_rr',lambda:2)
    monkeypatch.setattr(entry,'_learning_execution_enabled',lambda:False)
    monkeypatch.setattr(entry,'refine_m15_m5',lambda *args,**kw:dict(ok=False,error='IPC_TEST_FAILURE'))
    trace={}
    assert entry.calcular_entrada('COMPRA',112,100,symbol='TEST',diagnostics=trace) is None
    assert trace==dict(stage='MARKET_DATA_REJECTED',reason='IPC_TEST_FAILURE')
    monkeypatch.setattr(entry,'refine_m15_m5',lambda *args,**kw:dict(ok=True,m15=[],m5=[],trigger=dict(confirmed=False,reason='NO_CLOSED_M5_REACTION')))
    monkeypatch.setattr(entry,'confirmed_zone_entry',lambda *args,**kw:(None,'INSUFFICIENT_TECHNICAL_TARGETS_AT_RR'))
    assert entry.calcular_entrada('COMPRA',112,100,symbol='TEST',diagnostics=trace) is None
    assert trace['stage']=='M5_TRIGGER_REJECTED'
    assert trace['structural_reason']=='INSUFFICIENT_TECHNICAL_TARGETS_AT_RR'
