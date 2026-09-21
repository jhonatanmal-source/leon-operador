"""Persistent engineering queue; no authentication, network or execution here.

All functions return JSON-compatible values. Jobs never expose session_id;
get_job(id, internal=True) is reserved for the worker. Artifact content is
untrusted text, sanitized and capped at 60,000 characters. Evidence is retained.
LEON_ENGINEERING_DB overrides ROOT/data/engineering.sqlite3. Times are UTC ISO.
enqueue_job rejects duplicate active kinds and queues of ten. claim_job uses
BEGIN IMMEDIATE, returning the oldest queued job or None. Mutators accept only
documented fields; roles and worker allow JSON details with evidence lists.
"""

import json
import os
import re
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
KINDS = {'diagnose': 'Diagnostico', 'develop': 'Desenvolvimento', 'review': 'Revisao'}
STATES = {'QUEUED', 'RUNNING', 'COMPLETED', 'FAILED'}
DEFAULT_SETTINGS = dict(enabled=True, interval_seconds=900, next_run_at=None,
                        last_fingerprint=None)


def sanitize_text(text):
    """Best-effort secret redaction; not an HTML sanitizer or trust boundary."""
    text = str(text)
    text = re.sub(r'(?i)\bBearer\s+[^\s,;"\']+', 'Bearer [REDACTED]', text)
    text = re.sub(r'(?i)(["\']?\b[\w.-]*(?:password|passwd|secret|token|api[_-]?key|credential|private[_-]?key)[\w.-]*["\']?\s*[:=]\s*)(?:"[^"\n]*"|\'[^\'\n]*\'|[^\s,;}]+)',
                  lambda m: m[1] + '"[REDACTED]"', text)
    text = re.sub(r'-----BEGIN [^-]*PRIVATE KEY-----.*?-----END [^-]*PRIVATE KEY-----',
                  '[REDACTED]', text, flags=re.S)
    text = re.sub(r'\b(?:sk-[A-Za-z0-9_-]{12,}|gh[pousr]_[A-Za-z0-9_]{16,}|github_pat_[A-Za-z0-9_]{16,}|AKIA[A-Z0-9]{16}|\d{6,}:[A-Za-z0-9_-]{25,})\b', '[REDACTED]', text)
    return text


def _clean(value):
    if isinstance(value, str):
        return sanitize_text(value)
    if isinstance(value, dict):
        return {str(k): ('[REDACTED]' if re.search(r'(?i)password|passwd|secret|token|api.?key|credential', str(k))
                         else _clean(v)) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_clean(v) for v in value]
    return value


def _dump(value):
    return json.dumps(value, ensure_ascii=True, separators=(',', ':'), allow_nan=False)


def _now():
    return datetime.now(timezone.utc).isoformat()


@contextmanager
def _db(write=False):
    path = Path(os.environ.get('LEON_ENGINEERING_DB', ROOT / 'data/engineering.sqlite3'))
    path.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(str(path), timeout=30, isolation_level=None)
    con.row_factory = sqlite3.Row
    try:
        con.execute('PRAGMA busy_timeout=30000')
        con.execute('PRAGMA journal_mode=WAL')
        con.execute('PRAGMA foreign_keys=ON')
        if write:
            con.execute('BEGIN IMMEDIATE')
        yield con
        if write:
            con.commit()
    except Exception:
        if write:
            con.rollback()
        raise
    finally:
        con.close()


def init_store():
    """Create schema idempotently. Call once before other API operations."""
    with _db(True) as c:
        c.execute('CREATE TABLE IF NOT EXISTS jobs (seq INTEGER PRIMARY KEY AUTOINCREMENT, id TEXT UNIQUE NOT NULL, kind TEXT NOT NULL, state TEXT NOT NULL, data TEXT NOT NULL)')
        c.execute('CREATE TABLE IF NOT EXISTS events (seq INTEGER PRIMARY KEY AUTOINCREMENT, id TEXT UNIQUE NOT NULL, data TEXT NOT NULL)')
        c.execute('CREATE TABLE IF NOT EXISTS artifacts (seq INTEGER PRIMARY KEY AUTOINCREMENT, id TEXT UNIQUE NOT NULL, job_id TEXT NOT NULL REFERENCES jobs(id), data TEXT NOT NULL, content TEXT NOT NULL)')
        c.execute('CREATE TABLE IF NOT EXISTS kv (key TEXT PRIMARY KEY, data TEXT NOT NULL)')
        c.execute('CREATE INDEX IF NOT EXISTS jobs_state ON jobs(state,seq)')


def _job(c, row, internal=False):
    if row is None:
        return None
    result = json.loads(row['data'])
    result['artifact_ids'] = [r['id'] for r in c.execute('SELECT id FROM artifacts WHERE job_id=? ORDER BY seq', (result['id'],))]
    if not internal:
        result.pop('session_id', None)
    return result


def enqueue_job(kind, requested_by='system', parent_id=None):
    """Enqueue diagnose/develop/review; duplicate active kind/full queue raises RuntimeError."""
    if not isinstance(kind, str) or kind not in KINDS:
        raise ValueError('Invalid job kind')
    with _db(True) as c:
        if c.execute("SELECT 1 FROM jobs WHERE kind=? AND state IN ('QUEUED','RUNNING')", (kind,)).fetchone():
            raise RuntimeError('Job kind already active')
        if c.execute("SELECT COUNT(*) FROM jobs WHERE state='QUEUED'").fetchone()[0] >= 10:
            raise RuntimeError('Queue full')
        if parent_id is not None and not c.execute('SELECT 1 FROM jobs WHERE id=?', (str(parent_id),)).fetchone():
            raise ValueError('Unknown parent job')
        job = dict(id=str(uuid.uuid4()), kind=kind, title=KINDS[kind], state='QUEUED',
                   label='Na fila', created_at=_now(), started_at=None, finished_at=None,
                   summary='', agent_id=kind, requested_by=sanitize_text(requested_by),
                   parent_id=parent_id, artifact_ids=[], evidence=[])
        c.execute('INSERT INTO jobs(id,kind,state,data) VALUES(?,?,?,?)', (job['id'], kind, job['state'], _dump(job)))
        return job


def claim_job():
    """Atomically claim oldest queued job; includes internal session_id if present."""
    with _db(True) as c:
        job = _job(c, c.execute("SELECT * FROM jobs WHERE state='QUEUED' ORDER BY seq LIMIT 1").fetchone(), True)
        if job is None:
            return None
        job.update(state='RUNNING', label='Executando', started_at=_now())
        c.execute('UPDATE jobs SET state=?,data=? WHERE id=?', (job['state'], _dump(job), job['id']))
        return job


def update_job(job_id, **fields):
    """Update state/label/summary/session_id/started_at/finished_at; unknown ID returns None."""
    allowed = {'state', 'label', 'summary', 'session_id', 'started_at', 'finished_at'}
    if fields.keys() - allowed:
        raise ValueError('Unknown job fields')
    if 'state' in fields and fields['state'] not in STATES:
        raise ValueError('Invalid state')
    if any(v is not None and not isinstance(v, str) for v in fields.values()):
        raise ValueError('Job fields must be strings or None')
    with _db(True) as c:
        job = _job(c, c.execute('SELECT * FROM jobs WHERE id=?', (str(job_id),)).fetchone(), True)
        if job is None:
            return None
        state = fields.get('state', job['state'])
        if state != job['state'] and (job['state'], state) not in {('QUEUED', 'RUNNING'), ('QUEUED', 'FAILED'), ('RUNNING', 'COMPLETED'), ('RUNNING', 'FAILED')}:
            raise ValueError('Invalid state transition')
        job.update({k: (v if k == 'session_id' or v is None else sanitize_text(v)) for k, v in fields.items()})
        c.execute('UPDATE jobs SET state=?,data=? WHERE id=?', (job['state'], _dump(job), job['id']))
        job.pop('session_id', None)
        return job


def get_job(id, internal=False):
    with _db() as c:
        return _job(c, c.execute('SELECT * FROM jobs WHERE id=?', (str(id),)).fetchone(), internal)


def _limit(value):
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError('Limit must be a nonnegative integer')
    return min(value, 1000)


def list_jobs(limit=30):
    with _db() as c:
        return [_job(c, r) for r in c.execute('SELECT * FROM jobs ORDER BY seq DESC LIMIT ?', (_limit(limit),)).fetchall()]


def add_event(agent_id, title, summary='', job_id=None, severity='info'):
    """Record an actual caller-reported operation, never synthesize activity."""
    event = _clean(dict(id=str(uuid.uuid4()), agent_id=agent_id, title=title,
                        summary=summary, job_id=job_id, severity=severity, created_at=_now(), evidence=[]))
    with _db(True) as c:
        c.execute('INSERT INTO events(id,data) VALUES(?,?)', (event['id'], _dump(event)))
    return event


def list_events(limit=60):
    with _db() as c:
        return [json.loads(r['data']) for r in c.execute('SELECT data FROM events ORDER BY seq DESC LIMIT ?', (_limit(limit),))]


def add_artifact(job_id, title, kind, content):
    """Store sanitized untrusted content capped at 60k; return metadata only."""
    artifact = _clean(dict(id=str(uuid.uuid4()), job_id=job_id, title=title, kind=kind,
                           created_at=_now(), evidence=[]))
    content = sanitize_text(content)[:60000]
    with _db(True) as c:
        if not c.execute('SELECT 1 FROM jobs WHERE id=?', (str(job_id),)).fetchone():
            raise ValueError('Unknown job')
        c.execute('INSERT INTO artifacts(id,job_id,data,content) VALUES(?,?,?,?)',
                  (artifact['id'], str(job_id), _dump(artifact), content))
    return artifact


def list_artifacts(limit=40):
    with _db() as c:
        return [json.loads(r['data']) for r in c.execute('SELECT data FROM artifacts ORDER BY seq DESC LIMIT ?', (_limit(limit),))]


def get_artifact(id):
    with _db() as c:
        row = c.execute('SELECT data,content FROM artifacts WHERE id=?', (str(id),)).fetchone()
        return None if row is None else dict(json.loads(row['data']), content=row['content'][:60000])


def _get(c, key, default):
    row = c.execute('SELECT data FROM kv WHERE key=?', (key,)).fetchone()
    return json.loads(row['data']) if row else dict(default)


def _set(c, key, value):
    c.execute('INSERT INTO kv(key,data) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET data=excluded.data', (key, _dump(value)))


def _details(fields):
    fields = _clean(fields)
    if 'evidence' in fields and not isinstance(fields['evidence'], list):
        raise ValueError('Evidence must be a list')
    _dump(fields)
    return fields


def set_worker(state, label, **details):
    with _db(True) as c:
        value = _get(c, 'worker', {'evidence': []})
        value.update(_details(details))
        value.update(state=sanitize_text(state), label=sanitize_text(label), updated_at=_now())
        _set(c, 'worker', value)
        return value


def get_worker():
    with _db() as c:
        return _get(c, 'worker', dict(state='UNKNOWN', label='Sem evidencia recente', evidence=[]))


def set_role(role_id, **fields):
    with _db(True) as c:
        roles = _get(c, 'roles', {})
        value = roles.setdefault(str(role_id), {'evidence': []})
        value.update(_details(fields))
        value['updated_at'] = _now()
        _set(c, 'roles', roles)
        return value


def get_roles():
    with _db() as c:
        return _get(c, 'roles', {})


def get_settings():
    with _db() as c:
        return dict(DEFAULT_SETTINGS, **_get(c, 'settings', {}))


def set_settings(**values):
    if values.keys() - {'enabled', 'next_run_at', 'last_fingerprint'}:
        raise ValueError('Unknown settings')
    if 'enabled' in values and not isinstance(values['enabled'], bool):
        raise ValueError('enabled must be bool')
    if any(v is not None and not isinstance(v, str) for k, v in values.items() if k != 'enabled'):
        raise ValueError('Settings must be strings or None')
    with _db(True) as c:
        settings = dict(DEFAULT_SETTINGS, **_get(c, 'settings', {}))
        settings.update(_clean(values))
        _set(c, 'settings', settings)
        return settings


def recover_interrupted_jobs():
    """On worker restart mark RUNNING jobs FAILED, retaining sessions/evidence."""
    with _db(True) as c:
        rows = c.execute("SELECT * FROM jobs WHERE state='RUNNING'").fetchall()
        for row in rows:
            job = json.loads(row['data'])
            job.update(state='FAILED', label='Interrompido por reinicio', finished_at=_now())
            c.execute('UPDATE jobs SET state=?,data=? WHERE id=?', ('FAILED', _dump(job), job['id']))
        return len(rows)
