import hmac
import secrets
from collections import defaultdict, deque
from datetime import datetime, timedelta

from flask import abort, request, session


LOGIN_ATTEMPTS = defaultdict(deque)
LOGIN_WINDOW = timedelta(minutes=15)
LOGIN_LIMIT = 8


def csrf_token():
    token = session.get("_csrf_token")
    if not token:
        token = secrets.token_urlsafe(32)
        session["_csrf_token"] = token
    return token


def validate_csrf():
    if request.method not in {"POST", "PUT", "PATCH", "DELETE"}:
        return
    expected = session.get("_csrf_token", "")
    received = request.form.get("csrf_token", "") or request.headers.get(
        "X-CSRF-Token",
        "",
    )
    if not expected or not received or not hmac.compare_digest(expected, received):
        abort(400, description="CSRF token inválido.")


def _attempt_key(username):
    return (
        request.remote_addr or "unknown",
        str(username or "").strip().lower(),
    )


def login_rate_limited(username):
    now = datetime.now()
    attempts = LOGIN_ATTEMPTS[_attempt_key(username)]
    while attempts and now - attempts[0] > LOGIN_WINDOW:
        attempts.popleft()
    return len(attempts) >= LOGIN_LIMIT


def register_login_failure(username):
    LOGIN_ATTEMPTS[_attempt_key(username)].append(datetime.now())


def clear_login_failures(username):
    LOGIN_ATTEMPTS.pop(_attempt_key(username), None)
