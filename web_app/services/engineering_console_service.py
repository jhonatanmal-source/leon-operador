"""Read-only console projection. Never imports an execution engine or MT5.

Naive producer timestamps are Sao Paulo local time. Missing, malformed, future
or older-than-180s evidence cannot establish present activity. Store payloads
are projected through allowlists; artifact bodies are served separately.
"""
import configparser
import json
import math
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from src import engineering_store as store
from src.opportunity_learning import learning_summary
from src.learning_evaluation import evaluate
from src.quality_collector import cache_key

ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / 'data'
CONFIG_FILE = ROOT / 'config.ini'
ROLE_IDS = {'diagnose': 'diagnostic', 'develop': 'development', 'review': 'review'}
ROLE_NAMES = {'diagnose': ('Diagnostico', 'Investiga falhas e dados ausentes'),
              'develop': ('Desenvolvimento', 'Prepara propostas de correcao para revisao'),
              'review': ('Revisao', 'Revisa alteracoes e evidencias')}
STATES = {'RUNNING', 'QUEUED', 'COMPLETED', 'FAILED', 'WAITING', 'BLOCKED', 'UNCONFIGURED', 'STALE'}
CHECKS = {'direction': 'Direcao', 'elliott': 'Elliott', 'smc': 'SMC',
          'wave_liquidity': 'Onda e liquidez', 'top_down': 'Alinhamento dos tempos'}


def _read(name):
    try:
        path = DATA_DIR / name
        if path.stat().st_size > 8_000_000:
            return {}
        value = json.loads(path.read_text(encoding='utf-8'))
        return value if isinstance(value, dict) else {}
    except (OSError, ValueError):
        return {}


def _date(value):
    try:
        result = datetime.fromisoformat(value)
        if result.tzinfo is None:
            try:
                local = ZoneInfo('America/Sao_Paulo')
            except ZoneInfoNotFoundError:
                # Current Sao Paulo offset for Windows without a tzdata package.
                local = timezone(timedelta(hours=-3))
            result = result.replace(tzinfo=local)
        return result.astimezone(timezone.utc)
    except (ValueError, TypeError):
        return None


def _stale(value, now):
    date = _date(value)
    return date is None or not 0 <= (now - date).total_seconds() <= 180


def _iso(value):
    parsed = _date(value)
    return parsed.isoformat() if parsed else None


def _public(value):
    if isinstance(value, str):
        return store.sanitize_text(value)
    if isinstance(value, list):
        return [_public(v) for v in value]
    if isinstance(value, dict):
        return {k: _public(v) for k, v in value.items()
                if k not in {'session_id', 'content', 'password', 'token', 'api_key', 'secret'}}
    return value


def public_job(job):
    result = {key: job.get(key) for key in (
        'id', 'kind', 'title', 'state', 'label', 'created_at', 'started_at',
        'finished_at', 'summary', 'agent_id', 'artifact_ids')}
    result['agent_id'] = ROLE_IDS.get(job.get('kind'), job.get('agent_id'))
    return _public(result)


def _activity(value, now):
    updated = value.get('updated_at')
    stale = _stale(updated, now)
    state = value.get('state', 'WAITING')
    state = state if state in STATES else 'WAITING'
    if stale and state == 'RUNNING':
        state = 'STALE'
    return dict(state=state, label=('Sem evidencia recente' if stale and state not in {'COMPLETED', 'FAILED'} else value.get('label', 'Aguardando')),
                updated_at=_iso(updated), stale=stale)


def _risk():
    config = configparser.ConfigParser(interpolation=None)
    try:
        config.read(CONFIG_FILE, encoding='utf-8')
    except (OSError, configparser.Error):
        config = configparser.ConfigParser()
    result = {}
    for key, section in [('risk_percent', 'RISK_CONTROL'), ('daily_loss_percent', 'RISK_CONTROL'),
                         ('max_open_positions', 'EXECUTION')]:
        try:
            value = config.getfloat(section, key)
            result['max_positions' if key == 'max_open_positions' else key] = value if math.isfinite(value) else None
        except (ValueError, configparser.Error):
            result['max_positions' if key == 'max_open_positions' else key] = None
    return result


def get_engineering_console_snapshot(can_manage=False, now=None):
    """Contract v1; reads only persisted evidence, never starts jobs or trading."""
    now = now or datetime.now(timezone.utc)
    store.init_store()
    heartbeat, decision = _read('operator_heartbeat.json'), _read('latest_setup_decision.json')
    details = heartbeat.get('details')
    details = details if isinstance(details, dict) else {}
    stale = _stale(heartbeat.get('updated_at'), now)
    expires = _date(details.get('autonomy_expires_at'))
    indefinite = details.get('autonomy_reason') == 'AUTONOMY_ACTIVE_UNTIL_REVOKED' and details.get('scope') == 'demo_execution'
    checks = decision.get('checks', {})
    checks = checks if isinstance(checks, dict) else {}
    decision_stale = _stale(decision.get('created_at'), now)
    plan = decision.get('plan', {})
    plan = plan if isinstance(plan, dict) else {}
    state = 'SEM_ATUALIZACAO' if stale else heartbeat.get('status', 'SEM_DADOS')
    labels = {'SEM_ATUALIZACAO': 'Sem atualizacao recente', 'AGUARDANDO_SETUP': 'Aguardando setup',
              'CONTA_SEM_PERMISSAO': 'Conta sem permissao para negociar', 'PAUSA_MERCADO': 'Pausa de cotacoes',
              'PAUSA_RISCO': 'Pausa por risco', 'FALHA_TECNICA': 'Falha tecnica',
              'OBSERVACAO': 'Sem autorizacao de execucao', 'ORDEM_ENVIADA': 'Ordem enviada'}
    operator = dict(state=state, label=labels.get(state, state),
                    reason=details.get('entry_reason') or details.get('reason') or 'Sem diagnostico recente',
                    asset=plan.get('ativo'), updated_at=_iso(heartbeat.get('updated_at')), stale=stale,
                    autonomy_active=bool(not stale and details.get('execution_authorized') is True and (indefinite or (expires and expires > now))),
                    autonomy_until_revoked=bool(indefinite and not stale and details.get('execution_authorized') is True),
                    autonomy_expires_at=_iso(details.get('autonomy_expires_at')),
                    checks=[dict(id=k, label=v, passed=checks.get(k) if not decision_stale and isinstance(checks.get(k), bool) else None)
                            for k, v in CHECKS.items()], risk=_risk())
    funnel = decision.get('funnel', {})
    operator['funnel'] = {k: funnel.get(k) for k in ('day', 'timezone', 'version', 'candidates', 'approved', 'blocked_by')} if isinstance(funnel, dict) else {}
    operator['setup_stage'] = decision.get('stage')
    daily_risk = details.get('daily_risk', {})
    guard = daily_risk.get('daily_entry_guard', {}) if isinstance(daily_risk, dict) else {}
    if isinstance(guard, dict):
        operator['risk'].update({k: guard.get(k) for k in
            ('giveback_activation_percent', 'giveback_activation_amount', 'giveback_day_balance', 'giveback_armed')})
    settings, worker, roles = store.get_settings(), store.get_worker(), store.get_roles()
    jobs = [public_job(j) for j in store.list_jobs()]
    agents = []
    for identifier, name, task, source_stale, updated, evidence in [
        ('coordinator', 'Operador', operator['label'], stale, heartbeat.get('updated_at'), [operator['reason']]),
        ('smc', 'SMC', 'Avaliacao de estrutura e liquidez', decision_stale, decision.get('created_at'),
         ['Confirmado' if checks.get('smc') is True else 'Sem confirmacao']),
        ('elliott', 'Elliott', 'Avaliacao de ondas', decision_stale, decision.get('created_at'),
         ['Confirmado' if checks.get('elliott') is True else 'Sem confirmacao']),
        ('risk', 'Risco', 'Protecoes de entrada', stale, heartbeat.get('updated_at'),
         [daily_risk.get('reason', 'Sem registro') if isinstance(daily_risk, dict) else 'Sem registro']),
    ]:
        agents.append(dict(id=identifier, name=name, role='Modulo operacional', kind='operational',
                           engine='Regras do operador', task=task, run_id=None,
                           evidence=evidence if not source_stale else [], updated_at=_iso(updated),
                           stale=source_stale, state='STALE' if source_stale else 'WAITING',
                           label='Sem evidencia recente' if source_stale else 'Ultima avaliacao registrada'))
    for kind, identifier in ROLE_IDS.items():
        role = roles.get(identifier, roles.get(kind, {}))
        role = role if isinstance(role, dict) else {}
        name, description = ROLE_NAMES[kind]
        agents.append(dict(id=identifier, name=name, role=description, kind='engineering',
                           engine=role.get('engine', 'Sem executor confirmado'),
                           task=role.get('task', 'Sem execucao registrada'), run_id=role.get('run_id'),
                           evidence=role.get('evidence', []) if isinstance(role.get('evidence', []), list) else [],
                           **_activity(role, now)))
    provider = worker.get('provider', {})
    provider = provider if isinstance(provider, dict) else {}
    provider = {key: provider.get(key, default) for key, default in (
        ('available', False), ('label', 'IA nao confirmada'), ('reason', 'Sem evidencia de provedor disponivel'), ('checked_at', None))}
    provider['available'] = provider['available'] is True and not _stale(provider.get('checked_at'), now)
    events = []
    for event in store.list_events():
        events.append(dict(id=event.get('id'), at=event.get('created_at'),
                           agent_id=ROLE_IDS.get(event.get('agent_id'), event.get('agent_id')),
                           **{k: event.get(k) for k in ('job_id', 'severity', 'title', 'summary')}))
    records = []
    seen = set()
    for row in _read('confirmed_mt5_outcomes.json').values():
        if not isinstance(row, dict) or row.get('source') != 'MT5_DEMO_REAL' or not row.get('account_key') or not row.get('position_id'):
            continue
        try:
            profit = float(row['actual_profit'])
        except (KeyError, TypeError, ValueError):
            continue
        identity = (str(row['account_key']), str(row['position_id']))
        if math.isfinite(profit) and identity not in seen:
            seen.add(identity)
            records.append((row, profit))
    version = decision.get('version')
    current = [(r, p) for r, p in records if version and r.get('setup_version') == version]
    learning_time = max((_iso(r.get('data_fechamento')) or '' for r, _ in records), default='') or None
    agents.append(dict(id='learning', name='Aprendizado', role='Memoria de resultados confirmados',
                       kind='operational', engine='Evidencias de operacoes fechadas',
                       state='WAITING', label='Sem nova amostra' if not current else 'Resultados registrados',
                       task=f'{len(current)} fechamentos na versao atual', updated_at=learning_time,
                       stale=_stale(learning_time, now), run_id=None,
                       evidence=[f'{len(records)} fechamentos confirmados no historico',
                                 'Resultados antigos nao comprovam melhoria da versao atual.']))
    tests = worker.get('tests', {})
    tests = tests if isinstance(tests, dict) else {}
    tests = {k: tests.get(k) for k in ('passed', 'failed', 'updated_at')}
    artifacts = [{k: a.get(k) for k in ('id', 'title', 'kind', 'created_at', 'job_id')}
                 for a in store.list_artifacts()]
    learning = learning_summary([r for r, _ in current], version)
    learning['evaluation'] = evaluate([r for r, _ in current])
    learning['trades'] = []
    for row, profit in sorted(current, key=lambda item: str(item[0].get('data_fechamento', '')), reverse=True)[:50]:
        quality = _read('trade_quality/' + cache_key(row) + '.json')
        trade = {key: row.get(key) for key in ('order_ticket', 'ativo', 'direcao', 'entry_model', 'context_mode', 'currency', 'data_fechamento')}
        trade.update(net_profit=profit, quality={key: quality.get(key) for key in
                     ('mfe_r', 'mae_r', 'status', 'collection_reason', 'updated_at', 'complete_history_verified')})
        learning['trades'].append(trade)
    quality_status = _read('quality_collector_status.json')
    learning['collector_updated_at'] = quality_status.get('updated_at')
    learning['collector_ok'] = quality_status.get('ok')
    return _public(dict(schema_version=1, generated_at=now.isoformat(), can_manage=bool(can_manage),
                        operator=operator, engineering=dict(enabled=settings['enabled'], worker=_activity(worker, now),
                        provider=provider, next_run_at=settings['next_run_at'], interval_seconds=settings['interval_seconds']),
                        agents=agents, jobs=jobs, events=events, artifacts=artifacts, learning=learning,
                        metrics=dict(confirmed_trades=len(records), version_trades=len(current),
                                     wins=sum(p > 0 for _, p in current), losses=sum(p < 0 for _, p in current),
                                     setup_version=version, tests=tests)))
