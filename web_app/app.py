import sys
from datetime import timedelta
from pathlib import Path

from flask import Flask, flash, redirect, render_template, url_for


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

    init_db()
    register_blueprints(app)
    app.before_request(validate_csrf)

    @app.context_processor
    def inject_current_user():
        return {
            "current_user": current_user(),
            "csrf_token": csrf_token,
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

    return app


app = create_app()


if __name__ == "__main__":
    from waitress import serve

    serve(
        app,
        host=config.WEB_HOST,
        port=config.WEB_PORT,
    )
