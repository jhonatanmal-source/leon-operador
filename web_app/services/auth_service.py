from functools import wraps

from flask import flash, redirect, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

from web_app.database.db import get_connection


VALID_ROLES = {"ADMIN", "SUPERVISOR", "COLABORADOR", "VISUALIZADOR"}


def hash_password(password):
    return generate_password_hash(password)


def verify_password(password_hash, password):
    return check_password_hash(password_hash, password)


def authenticate_user(username, password):
    normalized_username = str(username or "").strip()
    if not normalized_username or not password:
        return None

    with get_connection() as connection:
        user = connection.execute(
            "SELECT * FROM users WHERE username = ?",
            (normalized_username,),
        ).fetchone()

    if not user or not user["is_active"]:
        return None
    if user["role"] not in VALID_ROLES:
        return None
    if not verify_password(user["password_hash"], password):
        return None
    return dict(user)


def current_user():
    user_id = session.get("user_id")
    if not user_id:
        return None

    with get_connection() as connection:
        user = connection.execute(
            """
            SELECT id, username, role, is_active, must_change_password,
                   created_at, last_login
            FROM users
            WHERE id = ?
            """,
            (user_id,),
        ).fetchone()

    if not user or not user["is_active"]:
        session.clear()
        return None
    return dict(user)


def logout_user():
    session.clear()


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if current_user() is None:
            flash("Faça login para acessar o painel.", "error")
            return redirect(url_for("auth.login"))
        return view(*args, **kwargs)

    return wrapped


def role_required(*roles):
    allowed_roles = set(roles)

    def decorator(view):
        @wraps(view)
        def wrapped(*args, **kwargs):
            user = current_user()
            if user is None:
                flash("Faça login para acessar o painel.", "error")
                return redirect(url_for("auth.login"))
            if user["role"] not in allowed_roles:
                flash("Seu usuário não possui permissão para esta ação.", "error")
                return redirect(url_for("dashboard.index"))
            return view(*args, **kwargs)

        return wrapped

    return decorator
