import sys
from datetime import timedelta
from pathlib import Path

from flask import Flask, flash, redirect, render_template, url_for
from flask_compress import Compress


ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from web_app import config
from web_app.database.db import init_db
from web_app.routes.init import register_blueprints
from web_app.services.auth_service import current_user
from web_app.services.web_security_service import csrf_token, validate_csrf


def create_app(test_config=None):
    app = Flask(__name__)
    app.config.update(
        SECRET_KEY=config.SECRET_KEY,
        MAX_CONTENT_LENGTH=config.MAX_CONTENT_LENGTH,
        UPLOAD_FOLDER=str(config.UPLOAD_FOLDER),
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        SESSION_COOKIE_SECURE=config.SESSION_COOKIE_SECURE,
        PERMANENT_SESSION_LIFETIME=timedelta(hours=12),
    )
    if test_config:
        app.config.update(test_config)

    Compress(app)
    init_db()
    register_blueprints(app)
    app.before_request(validate_csrf)

    @app.context_processor
    def inject_current_user():
        mt5_summary = {}
        try:
            # Import lazy evita import circular (app.py -> services)
            from web_app.services.system_health_service import (
                get_mt5_account_summary,
            )

            mt5_summary = get_mt5_account_summary()
        except Exception:
            mt5_summary = {}
        return {
            "current_user": current_user(),
            "csrf_token": csrf_token,
            "mt5_account": mt5_summary.get("account") or "—",
            "mt5_server": mt5_summary.get("server") or "—",
            "mt5_type": mt5_summary.get("type") or "—",
            "mt5_connected": bool(mt5_summary.get("connected")),
            "mt5_status": mt5_summary.get("status") or "—",
        }

    @app.errorhandler(400)
    def bad_request(_error):
        return render_template(
            "base.html",
            standalone_message="Solicitação inválida. Atualize a página e tente novamente.",
        ), 400

    @app.errorhandler(403)
    def forbidden(_error):
        return render_template(
            "base.html",
            standalone_message="Acesso negado para o seu perfil.",
        ), 403

    @app.errorhandler(404)
    def not_found(_error):
        return render_template(
            "base.html",
            standalone_message="Registro não encontrado.",
        ), 404

    @app.errorhandler(413)
    def too_large(_error):
        flash(
            f"Arquivo acima do limite de {config.MAX_UPLOAD_MB} MB.",
            "error",
        )
        return redirect(url_for("analysis.upload"))

    @app.after_request
    def add_security_headers(response):
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "style-src 'self' 'unsafe-inline'; "
            "script-src 'self' 'unsafe-inline' https://cdnjs.cloudflare.com; "
            "img-src 'self' data:; "
            "font-src 'self'; "
            "connect-src 'self'; "
            "frame-ancestors 'none'; "
            "form-action 'self'"
        )
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "SAMEORIGIN"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        return response

    return app


app = create_app()


if __name__ == "__main__":
    from waitress import serve

    serve(
        app,
        host=config.WEB_HOST,
        port=config.WEB_PORT,
    )
