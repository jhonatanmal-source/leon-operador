import pytest
from flask import Flask
from src import engineering_store as store
from web_app.routes import virtual_operations_routes as routes
from web_app.services.web_security_service import validate_csrf


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv('LEON_ENGINEERING_DB', str(tmp_path / 'engineering.sqlite3'))
    app = Flask(__name__)
    app.secret_key = 'isolated-test-only'
    app.register_blueprint(routes.virtual_operations_bp)
    app.before_request(validate_csrf)
    monkeypatch.setattr(routes, 'current_user', lambda: {'id': 1, 'role': 'ADMIN'})
    store.init_store()
    with app.test_client() as client:
        with client.session_transaction() as session:
            session['_csrf_token'] = 'test-csrf'
        yield client


def test_mutation_requires_csrf(client):
    assert client.post('/central-virtual/jobs', json={'kind': 'diagnose'}).status_code == 400
    assert store.list_jobs() == []


def test_admin_jobs_and_duplicates(client):
    headers = {'X-CSRF-Token': 'test-csrf'}
    response = client.post('/central-virtual/jobs', json={'kind': 'diagnose'}, headers=headers)
    assert response.status_code == 202
    assert response.json['job']['agent_id'] == 'diagnostic'
    assert client.post('/central-virtual/jobs', json={'kind': 'diagnose'}, headers=headers).status_code == 409
    assert client.post('/central-virtual/jobs', json={'kind': 'shell'}, headers=headers).status_code == 400


def test_readers_cannot_mutate_or_read_artifact(client, monkeypatch):
    monkeypatch.setattr(routes, 'current_user', lambda: {'id': 2, 'role': 'VISUALIZADOR'})
    assert client.post('/central-virtual/automation', json={'enabled': False}, headers={'X-CSRF-Token': 'test-csrf'}).status_code == 403
    assert client.get('/central-virtual/artifacts/any').status_code == 403


def test_anonymous_snapshot_denied(client, monkeypatch):
    monkeypatch.setattr(routes, 'current_user', lambda: None)
    response = client.get('/central-virtual/snapshot')
    assert response.status_code == 401
    assert response.headers['Cache-Control'] == 'no-store'


def test_pause_only_engineering(client):
    response = client.post('/central-virtual/automation', json={'enabled': False}, headers={'X-CSRF-Token': 'test-csrf'})
    assert response.status_code == 200
    assert store.get_settings()['enabled'] is False
    assert client.post('/central-virtual/automation', json={'enabled': 'false'}, headers={'X-CSRF-Token': 'test-csrf'}).status_code == 400
