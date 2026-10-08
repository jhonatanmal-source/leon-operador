from types import SimpleNamespace
from unittest.mock import Mock

import mt5linux_compat as backend


def test_windows_does_not_launch_terminal_when_absent(monkeypatch):
    import psutil
    monkeypatch.setattr(backend.sys, 'platform', 'win32')
    monkeypatch.setattr(psutil, 'process_iter', lambda fields: [])
    client = Mock()
    monkeypatch.setattr(backend, '_CLIENT', client)
    assert backend.initialize() is False
    client.initialize.assert_not_called()
    assert 'MT5_TERMINAL_NOT_RUNNING' in backend.last_error()[1]


def test_windows_uses_native_backend_and_bounded_timeout(monkeypatch):
    import psutil
    monkeypatch.setattr(backend.sys, 'platform', 'win32')
    monkeypatch.setattr(psutil, 'process_iter', lambda fields: [
        SimpleNamespace(info={'name': 'terminal64.exe'})])
    client = Mock()
    client.initialize.return_value = True
    monkeypatch.setattr(backend, '_CLIENT', client)
    monkeypatch.setenv('LEON_MT5_PATH', 'example-terminal.exe')
    assert backend.initialize()
    client.initialize.assert_called_once_with('example-terminal.exe', timeout=5000)
