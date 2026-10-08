"""Start/stop this isolated Windows analysis installation."""
import configparser
import json
import os
from pathlib import Path
import subprocess
import sys

import psutil

ROOT = Path(__file__).resolve().parents[1]
STATE = ROOT / 'data/local_processes.json'
TARGETS = {'panel': 'web_app.run', 'operator': 'src.leon_operator'}
MT5_PATH = r'C:\Program Files\FTMO Global Markets MT5 Terminal\terminal64.exe'


def verify_start(config):
    flags = [config.getboolean(s, k, fallback=False) for s, k in
             [('EXECUTION', 'enabled'), ('AUTONOMY', 'enabled'), ('OPERATOR', 'demo_execution_enabled')]]
    if not any(flags):
        return
    if not all(flags) or not config.getboolean('EXECUTION', 'demo_only', fallback=False):
        raise SystemExit('Startup refused: inconsistent demo configuration')
    if config.getboolean('EXECUTION', 'learning_lab_enabled', fallback=True):
        raise SystemExit('Startup refused: lab bypass mode is not allowed')
    sys.path.insert(0, str(ROOT))
    os.environ['LEON_MT5_PATH'] = MT5_PATH
    os.environ['LEON_NEWS_SOURCE'] = 'forex_factory'
    from src.autonomy_guard import status_autonomia
    from src.ftmo_guard import evaluate_ftmo_entry
    from src.news_shield import avaliar_news_shield
    import mt5_safe as mt5
    state = status_autonomia()
    if not state.get('active') or state.get('scope') != 'demo_execution':
        print('Sessao demo inativa: iniciando somente observacao; executor bloqueado pela autonomia.')
        return
    if not mt5.initialize():
        raise SystemExit('Startup refused: MT5 not connected')
    try:
        result = evaluate_ftmo_entry(mt5)
        if not result.get('approved'):
            raise SystemExit('Startup refused: ' + result['reason'])
    finally:
        mt5.shutdown()
    news = avaliar_news_shield()
    if not news.get('ok'):
        raise SystemExit('Startup refused: economic calendar unavailable')


def matching(name):
    matches = []
    for process in psutil.process_iter(['pid', 'cmdline', 'exe']):
        try:
            args = process.info['cmdline'] or []
            exe = (process.info['exe'] or '').lower()
            if exe.startswith(str(ROOT).lower() + os.sep) and TARGETS[name] in args:
                matches.append(process)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    return matches


def main():
    action = sys.argv[1] if len(sys.argv) > 1 else 'status'
    if action not in ('start', 'stop', 'status'):
        raise SystemExit('Use start, stop or status')
    if action == 'start':
        config = configparser.ConfigParser()
        config.read(ROOT / 'config.ini', encoding='utf-8')
        verify_start(config)
    state = {}
    for name, module in TARGETS.items():
        active = matching(name)
        if action == 'stop':
            for process in active:
                try:
                    process.terminate()
                except psutil.NoSuchProcess:
                    pass
            psutil.wait_procs(active, timeout=5)
        elif action == 'start' and not active:
            (ROOT / 'logs').mkdir(exist_ok=True)
            env = dict(os.environ, PYTHONUTF8='1', PYTHONPATH=str(ROOT),
                       LEON_MT5_PATH=MT5_PATH, LEON_NEWS_SOURCE='forex_factory')
            with (ROOT / 'logs' / f'local_{name}.log').open('ab') as log:
                process = subprocess.Popen([sys.executable, '-u', '-m', module],
                    cwd=ROOT, env=env, stdout=log, stderr=log,
                    creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
                state[name] = process.pid
        print(name, [p.pid for p in matching(name)])
    if action == 'start':
        STATE.parent.mkdir(exist_ok=True)
        STATE.write_text(json.dumps(state), encoding='utf-8')


if __name__ == '__main__':
    main()
