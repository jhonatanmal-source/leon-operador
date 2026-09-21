import json
from datetime import datetime, timezone

import pytest

from src import engineering_store as store
from web_app.services import engineering_console_service as service

NOW = datetime(2026, 9, 10, 15, tzinfo=timezone.utc)


def test_root_is_repository_not_web_folder():
    assert (service.ROOT / 'src/daily_entry_guard.py').exists()
    assert service.DATA_DIR == service.ROOT / 'data'


@pytest.fixture
def data(tmp_path, monkeypatch):
    monkeypatch.setenv('LEON_ENGINEERING_DB', str(tmp_path / 'queue.sqlite3'))
    monkeypatch.setattr(service, 'DATA_DIR', tmp_path)
    monkeypatch.setattr(service, 'CONFIG_FILE', tmp_path / 'missing.ini')
    store.init_store()
    return tmp_path


def write(data, name, value):
    (data / name).write_text(json.dumps(value), encoding='utf-8')


def test_empty_is_not_activity(data):
    result = service.get_engineering_console_snapshot(now=NOW)
    assert result['operator']['stale']
    assert not result['operator']['autonomy_active']
    assert all(a['stale'] and a['state'] != 'RUNNING' for a in result['agents'])
    assert result['events'] == []
    assert result['metrics']['tests']['passed'] is None
    assert result['operator']['risk']['risk_percent'] is None


@pytest.mark.parametrize('time,stale', [('2026-09-10T12:00:00', False),
    ('2026-09-10T11:57:00', False), ('2026-09-10T11:56:59', True),
    ('2026-09-10T12:01:00', True), ('invalid', True)])
def test_sao_paulo_timestamps(data, time, stale):
    write(data, 'operator_heartbeat.json', dict(updated_at=time, status='AGUARDANDO_SETUP',
          details=dict(execution_authorized=True, autonomy_expires_at='2026-09-10T13:00:00')))
    operator = service.get_engineering_console_snapshot(now=NOW)['operator']
    assert operator['stale'] is stale
    assert operator['autonomy_active'] is (not stale)


def test_confirmed_outcomes_and_stale_checks(data):
    write(data, 'latest_setup_decision.json', dict(version='v2', created_at='2026-09-10T14:00:00+00:00', checks={'elliott': True}))
    row = dict(source='MT5_DEMO_REAL', account_key='a', position_id=1, actual_profit=2, setup_version='v2')
    write(data, 'confirmed_mt5_outcomes.json', {'one': row, 'duplicate': row,
          'old': dict(row, position_id=2, setup_version='v1'),
          'loss': dict(row, position_id=3, actual_profit=-1),
          'fake': dict(row, position_id=4, source='SIMULATION'),
          'bad': dict(row, position_id=5, actual_profit='NaN')})
    result = service.get_engineering_console_snapshot(now=NOW)
    assert result['metrics']['confirmed_trades'] == 3
    assert result['metrics']['version_trades'] == 2
    assert result['metrics']['wins'] == result['metrics']['losses'] == 1
    assert all(c['passed'] is None for c in result['operator']['checks'])


def test_projection_redaction_and_role_staleness(data, monkeypatch):
    monkeypatch.setattr(store, '_now', lambda: '2026-09-10T14:50:00+00:00')
    job = store.enqueue_job('diagnose')
    store.update_job(job['id'], session_id='private-session')
    store.set_role('diagnose', state='RUNNING', task='password=hidden')
    store.set_worker('RUNNING', 'Working', provider={'available': True, 'session_id': 'hidden'})
    event = store.add_event('develop', 'Saved')
    store.add_artifact(job['id'], 'Report', 'text', 'private-body')
    result = service.get_engineering_console_snapshot(now=NOW)
    assert result['jobs'][0]['agent_id'] == 'diagnostic'
    assert result['events'][0]['agent_id'] == 'development'
    assert result['events'][0]['at'] == event['created_at']
    assert result['agents'][0]['state'] == 'STALE'
    assert not result['engineering']['provider']['available']
    text = json.dumps(result)
    assert 'private-session' not in text and 'private-body' not in text and 'hidden' not in text


def test_malformed_records_do_not_crash(data):
    for name in ('operator_heartbeat.json', 'latest_setup_decision.json', 'confirmed_mt5_outcomes.json'):
        (data / name).write_text('{broken', encoding='utf-8')
    assert service.get_engineering_console_snapshot(now=NOW)['operator']['stale']
