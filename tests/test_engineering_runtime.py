"""Runtime contract tests: every HTTP request is intercepted locally."""
import json
import urllib.error
from unittest.mock import Mock

import pytest

from src import engineering_runtime as runtime


@pytest.fixture
def engine(monkeypatch):
    monkeypatch.setattr(runtime, 'dotenv_values', lambda _: {'OPENCODE_SERVER_PASSWORD': 'test-secret'})
    monkeypatch.setattr(runtime.urllib.request, 'urlopen', Mock(side_effect=AssertionError('Real network forbidden')))
    return runtime.Runtime()


def scenario(engine, monkeypatch, *, tools=None, messages=None, abort_error=False):
    calls = []
    def request(path, body=None, method=None):
        calls.append((path, body, method))
        if path == '/config':
            return {'model': 'provider/model'}
        if path == '/provider':
            return {'connected': ['provider']}
        if path == '/experimental/tool/ids':
            return tools if tools is not None else ['bash', 'edit', 'mcp__trade', 'read']
        if path == '/session':
            return {'id': 'ses_test123'}
        if '/message?' in path:
            return messages if messages is not None else [{'info': {'role': 'assistant', 'time': {'completed': 1}},
                'parts': [{'type': 'text', 'text': 'Relatorio comprovado'}, {'type': 'tool', 'text': 'ignore'}]}]
        if path.endswith('/abort') and abort_error:
            raise RuntimeError('abort unavailable')
        return None
    monkeypatch.setattr(engine, 'request', request)
    return calls


def test_session_denies_every_permission_and_disables_all_tools(engine, monkeypatch):
    calls = scenario(engine, monkeypatch)
    heartbeat, created = Mock(), Mock()
    report, model = engine.run('job', 'Evidence only', heartbeat, created)
    session = next(body for path, body, _ in calls if path == '/session')
    assert session['permission'] == [{'permission': '*', 'pattern': '*', 'action': 'deny'}]
    prompt = next(body for path, body, _ in calls if path.endswith('/prompt_async'))
    assert prompt['tools'] == {'bash': False, 'edit': False, 'mcp__trade': False, 'read': False}
    assert prompt['agent'] == 'plan'
    assert report == 'Relatorio comprovado'
    assert model == {'providerID': 'provider', 'modelID': 'model'}
    created.assert_called_once_with('ses_test123')
    heartbeat.assert_called_once_with('provider/model')
    assert calls[-1] == ('/session/ses_test123/abort', {}, 'POST')


@pytest.mark.parametrize('tools', [{}, ['bash', 1], 'bash'])
def test_unverified_tool_catalog_fails_before_session(engine, monkeypatch, tools):
    calls = scenario(engine, monkeypatch, tools=tools)
    with pytest.raises(RuntimeError, match='ferramentas bloqueadas'):
        engine.run('job', 'text', Mock(), Mock())
    assert not any(path == '/session' for path, _, _ in calls)


def test_model_failure_aborts_session(engine, monkeypatch):
    calls = scenario(engine, monkeypatch, messages=[{'info': {'role': 'assistant', 'error': {'name': 'ProviderError'}}}])
    with pytest.raises(RuntimeError, match='ProviderError'):
        engine.run('job', 'text', Mock(), Mock())
    assert calls[-1][0].endswith('/abort')


def test_timeout_aborts_without_sleep(engine, monkeypatch):
    calls = scenario(engine, monkeypatch, messages=[])
    times = iter([0, 241])
    monkeypatch.setattr(runtime.time, 'monotonic', lambda: next(times))
    monkeypatch.setattr(runtime.time, 'sleep', Mock(side_effect=AssertionError('No real sleep')))
    with pytest.raises(RuntimeError, match='Tempo limite'):
        engine.run('job', 'text', Mock(), Mock())
    assert calls[-1][0].endswith('/abort')


def test_cleanup_failure_does_not_discard_success(engine, monkeypatch):
    scenario(engine, monkeypatch, abort_error=True)
    assert engine.run('job', 'text', Mock(), Mock())[0] == 'Relatorio comprovado'


def test_http_is_local_bounded_and_authenticated(engine, monkeypatch):
    response = Mock()
    response.__enter__ = Mock(return_value=response)
    response.__exit__ = Mock(return_value=False)
    response.read.return_value = b'{"ok":true}'
    opener = Mock(return_value=response)
    monkeypatch.setattr(runtime.urllib.request, 'urlopen', opener)
    assert engine.request('/session', {'title': 'test'}) == {'ok': True}
    req = opener.call_args.args[0]
    assert req.full_url == 'http://127.0.0.1:4096/session?directory=%2Fopt%2Fleon%2Fapp'
    assert req.get_header('Authorization').startswith('Basic ')
    assert json.loads(req.data) == {'title': 'test'}
    assert opener.call_args.kwargs['timeout'] == 20
    response.read.assert_called_once_with(2_000_001)
    response.read.return_value = b'x' * 2_000_001
    with pytest.raises(RuntimeError, match='excedeu limite'):
        engine.request('/config')


def test_transport_error_does_not_expose_credentials(engine, monkeypatch):
    monkeypatch.setattr(runtime.urllib.request, 'urlopen', Mock(side_effect=urllib.error.URLError('test-secret')))
    with pytest.raises(RuntimeError) as error:
        engine.request('/config')
    assert 'test-secret' not in str(error.value)
