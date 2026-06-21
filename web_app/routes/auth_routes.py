from datetime import datetime

from flask import (
    Blueprint,
    flash,
    redirect,
    render_template,
    request,
    session,
    url_for,
)

from web_app.database.db import get_connection
from web_app.services.access_log_service import log_action
from web_app.services.auth_service import (
    authenticate_user,
    current_user,
    hash_password,
    login_required,
    logout_user,
    verify_password,
)
from web_app.services.web_security_service import (
    clear_login_failures,
    login_rate_limited,
    register_login_failure,
)


auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user():
        return redirect(url_for("dashboard.index"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        if login_rate_limited(username):
            log_action("LOGIN_BLOQUEADO_RATE_LIMIT", username=username)
            flash(
                "Muitas tentativas. Aguarde 15 minutos antes de tentar novamente.",
                "error",
            )
            return render_template("login.html"), 429

        user = authenticate_user(username, password)

        if user is None:
            register_login_failure(username)
            log_action("LOGIN_FALHOU", username=username)
            flash("Usuário, senha ou status inválido.", "error")
            return render_template("login.html")

        clear_login_failures(username)
        session.clear()
        session["user_id"] = user["id"]
        session["username"] = user["username"]
        session["role"] = user["role"]
        session.permanent = True

        now = datetime.now().isoformat(timespec="seconds")
        with get_connection() as connection:
            connection.execute(
                "UPDATE users SET last_login = ? WHERE id = ?",
                (now, user["id"]),
            )

        log_action("LOGIN_SUCESSO", user["id"], user["username"])
        flash("Login realizado com sucesso.", "success")
        return redirect(url_for("dashboard.index"))

    return render_template("login.html")


@auth_bp.get("/logout")
def logout():
    user = current_user()
    if user:
        log_action("LOGOUT", user["id"], user["username"])
    logout_user()
    flash("Sessão encerrada.", "success")
    return redirect(url_for("auth.login"))


@auth_bp.post("/change-password")
@login_required
def change_password():
    user = current_user()
    current_password = request.form.get("current_password", "")
    new_password = request.form.get("new_password", "")
    confirmation = request.form.get("confirm_password", "")

    if len(new_password) < 10:
        flash("A nova senha deve ter pelo menos 10 caracteres.", "error")
        return redirect(url_for("dashboard.index"))
    if new_password != confirmation:
        flash("A confirmação da nova senha não confere.", "error")
        return redirect(url_for("dashboard.index"))

    with get_connection() as connection:
        stored = connection.execute(
            "SELECT password_hash FROM users WHERE id = ?",
            (user["id"],),
        ).fetchone()
        if not stored or not verify_password(
            stored["password_hash"],
            current_password,
        ):
            flash("Senha atual inválida.", "error")
            return redirect(url_for("dashboard.index"))

        connection.execute(
            """
            UPDATE users
            SET password_hash = ?, must_change_password = 0
            WHERE id = ?
            """,
            (hash_password(new_password), user["id"]),
        )

    log_action("SENHA_ALTERADA", user["id"], user["username"])
    flash("Senha alterada com sucesso.", "success")
    return redirect(url_for("dashboard.index"))
