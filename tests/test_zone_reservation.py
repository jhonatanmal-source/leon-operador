"""Canonical zone ownership; all market and order I/O absent."""
from concurrent.futures import ThreadPoolExecutor
import multiprocessing

import pytest
from src import interest_zone_engine as zones
from src import pre_operation_engine as preop
from src.real_zone_cycle import run_real_zone_cycle


def prepared(tmp_path, monkeypatch):
    from test_real_zone_cycle import fixture, retest
    m15,m5,smc,stamp=fixture()
    store=zones.InterestZoneStore(tmp_path/'zones.json')
    run_real_zone_cycle('TEST',m15,m5,smc,store=store)
    result=run_real_zone_cycle('TEST',m15,retest(m5,stamp),smc,store=store)
    zone=result['confirmed_region']
    assert zone is not None
    monkeypatch.setattr(zones,'InterestZoneStore',lambda:store)
    monkeypatch.setattr(preop,'DATA_DIR',tmp_path)
    monkeypatch.setattr(preop,'PRE_OPERATION_FILE',tmp_path/'preops.csv')
    monkeypatch.setattr(preop,'_rr_minimo_operacional',lambda:2)
    monkeypatch.setattr(preop,'_aprendizado_operacional_ativo',lambda:True)
    return store,zone


def register(region_id):
    return preop.registrar_pre_operacao('TEST','COMPRA','SETUP MODERADO',
        (110,100,135,140,4),'BULLISH','CORRECAO','BOS_BULLISH','SEM_CHOCH',
        'BAIXA',0,region_id=region_id)


def test_first_plan_claims_zone_second_cannot_open(tmp_path,monkeypatch):
    store,zone=prepared(tmp_path,monkeypatch)
    first=register(zone['region_id'])
    assert first['status']=='ABERTO'
    assert store.get(zone['region_id'])['pre_operation_id']==first['id']
    second=register(zone['region_id'])
    assert second['status']=='OBSERVADO'
    assert second['resultado']=='REGION_PRE_OPERATION_ID_MISMATCH'
    assert zones.validate_zone_for_execution(first,store=store)['ok']
    assert not zones.validate_zone_for_execution(second,store=store)['ok']


def test_stale_refresh_cannot_erase_or_replace_owner(tmp_path,monkeypatch):
    store,zone=prepared(tmp_path,monkeypatch)
    store.associate_pre_operation(zone['region_id'],'PREOP-FIRST')
    store.upsert(dict(zone,pre_operation_id='',updated_at='2026-09-19T00:00:00+00:00'))
    assert store.get(zone['region_id'])['pre_operation_id']=='PREOP-FIRST'
    with pytest.raises(ValueError):
        store.upsert(dict(zone,pre_operation_id='PREOP-SECOND'))
    assert store.associate_pre_operation(zone['region_id'],'PREOP-FIRST')


def test_stale_competing_claims_have_one_winner(tmp_path,monkeypatch):
    store,zone=prepared(tmp_path,monkeypatch)
    def claim(owner):
        try:
            return store.upsert(dict(zone,pre_operation_id=owner))['pre_operation_id']
        except ValueError:
            return None
    with ThreadPoolExecutor(max_workers=2) as pool:
        results=list(pool.map(claim,['PREOP-A','PREOP-B']))
    assert sum(result is not None for result in results)==1


def test_missing_zone_is_not_an_open_executable_plan(tmp_path,monkeypatch):
    prepared(tmp_path,monkeypatch)
    result=register('MISSING')
    assert result['status']=='OBSERVADO'
    assert result['resultado']=='REGION_NOT_FOUND'


def _process_claim(store,zone,owner,start,results):
    start.wait(timeout=10)
    try:
        store.upsert(dict(zone,pre_operation_id=owner))
        results.put(owner)
    except ValueError:
        results.put(None)


@pytest.mark.skipif('fork' not in multiprocessing.get_all_start_methods(),reason='Linux process locking')
def test_competing_processes_have_one_winner(tmp_path,monkeypatch):
    store,zone=prepared(tmp_path,monkeypatch)
    ctx=multiprocessing.get_context('fork')
    start=ctx.Barrier(2)
    results=ctx.Queue()
    workers=[ctx.Process(target=_process_claim,args=(store,zone,owner,start,results))
             for owner in ('PREOP-A','PREOP-B')]
    try:
        for worker in workers:worker.start()
        received=[results.get(timeout=15) for _ in workers]
        for worker in workers:
            worker.join(timeout=15)
            assert worker.exitcode==0
        assert sum(value is not None for value in received)==1
        assert store.get(zone['region_id'])['pre_operation_id'] in received
    finally:
        for worker in workers:
            if worker.is_alive():worker.terminate();worker.join()
