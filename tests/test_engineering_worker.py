"""Worker tests use a temporary queue, mock inference and no trading modules."""
import importlib
import sys
import types
from unittest.mock import Mock

import pytest

from src import engineering_store as store


@pytest.fixture
def worker(tmp_path, monkeypatch):
    # Linux process locking is not under test on Windows. Queue locking is real SQLite.
    if sys.platform == 'win32':
        monkeypatch.setitem(sys.modules, 'fcntl', types.SimpleNamespace(LOCK_EX=2, LOCK_NB=4, flock=Mock()))
    module = importlib.import_module('src.engineering_worker')
    monkeypatch.setattr(module, 'ROOT', tmp_path)
    monkeypatch.setenv('LEON_ENGINEERING_DB', str(tmp_path / 'data' / 'engineering.sqlite3'))
    store.init_store()
    monkeypatch.setattr(module, 'Runtime', Mock(side_effect=AssertionError('Real runtime forbidden')))
    monkeypatch.setattr(module, 'get_engineering_console_snapshot', lambda: {
        'operator': dict(state='AGUARDANDO_SETUP', reason='Elliott missing', asset='XAUUSD',
                         updated_at=None, stale=True, checks=[], risk={'risk_percent': 0.5}),
        'metrics': {'confirmed_trades': 0}})
    return module


def claimed(kind='diagnose', requested_by='tester'):
    store.enqueue_job(kind, requested_by=requested_by)
    return store.claim_job()


def runtime_success(worker, monkeypatch):
    def run(job_id, prompt, heartbeat, session_created):
        assert 'EVIDENCIAS' in prompt
        session_created('ses_mock')
        heartbeat('mock/model')
        return 'Parecer: falta confirmacao, nenhuma alteracao aplicada.', {'providerID': 'mock', 'modelID': 'model'}
    fake = Mock()
    fake.run.side_effect = run
    monkeypatch.setattr(worker, 'Runtime', Mock(return_value=fake))
    return fake


@pytest.mark.parametrize('kind', ['diagnose', 'develop', 'review'])
def test_success_reports_without_mutating_trading(worker, monkeypatch, tmp_path, kind):
    sentinels = [tmp_path / 'config.ini', tmp_path / 'data' / 'trading.json']
    for path in sentinels:
        path.write_bytes(b'unchanged trading configuration')
    before = {path: path.read_bytes() for path in sentinels}
    fake = runtime_success(worker, monkeypatch)
    job = claimed(kind)
    worker.run_job(job)
    result = store.get_job(job['id'])
    assert result['state'] == 'COMPLETED' and result['finished_at']
    assert 'session_id' not in result
    assert store.get_job(job['id'], internal=True)['session_id'] == 'ses_mock'
    assert {a['kind'] for a in store.list_artifacts()} == {'evidence', 'report'}
    assert store.get_roles()[worker.ROLES[kind]]['state'] == 'COMPLETED'
    fake.run.assert_called_once()
    assert {path: path.read_bytes() for path in sentinels} == before
    assert len(store.list_jobs()) == 1


def test_runtime_failure_retains_evidence_and_marks_failed(worker, monkeypatch):
    monkeypatch.setattr(worker, 'Runtime', Mock(side_effect=RuntimeError('password=hidden')))
    job = claimed()
    worker.run_job(job)
    result = store.get_job(job['id'])
    assert result['state'] == 'FAILED' and result['finished_at']
    assert 'hidden' not in result['summary']
    assert [a['kind'] for a in store.list_artifacts()] == ['evidence']
    assert store.get_worker()['state'] == 'BLOCKED'
    assert store.list_events()[0]['severity'] == 'error'


def test_collection_failure_has_failure_artifact(worker, monkeypatch):
    monkeypatch.setattr(worker, 'evidence', Mock(side_effect=ValueError('Malformed evidence')))
    job = claimed()
    worker.run_job(job)
    assert store.get_job(job['id'])['state'] == 'FAILED'
    assert store.list_artifacts(), 'Failure must leave a reviewable artifact even when collection fails'


def test_system_success_chains_jobs(worker, monkeypatch):
    runtime_success(worker, monkeypatch)
    job = claimed(requested_by='system')
    worker.run_job(job)
    development = store.claim_job()
    assert development['kind'] == 'develop' and development['parent_id'] == job['id']
    worker.run_job(development)
    review = store.claim_job()
    assert review['kind'] == 'review' and review['parent_id'] == development['id']
    worker.run_job(review)
    assert store.claim_job() is None


def test_restart_recovers_interrupted_job(worker, monkeypatch):
    job = claimed()
    store.set_settings(enabled=False)
    class StopLoop(BaseException):
        pass
    def stop(_):
        raise StopLoop()
    monkeypatch.setattr(worker.time, 'sleep', stop)
    with pytest.raises(StopLoop):
        worker.main()
    assert store.get_job(job['id'])['state'] == 'FAILED'
    assert store.get_job(job['id'])['finished_at']
    assert store.recover_interrupted_jobs() == 0
    assert any(e['title'] == 'Executor iniciado' for e in store.list_events())
