from datetime import datetime

from flask import (
    Blueprint,
    flash,
    redirect,
    render_template,
    request,
    url_for,
)

from web_app.database.db import get_connection
from web_app.services.access_log_service import log_action
from web_app.services.auth_service import (
    VALID_ROLES,
    current_user,
    hash_password,
    role_required,
)


users_bp = Blueprint("users", __name__, url_prefix="/users")


@users_bp.get("")
@role_required("ADMIN")
def list_users():
    with get_connection() as connection:
        users = connection.execute(
            """
            SELECT users.*, operator_reputation.total_analyses,
                   operator_reputation.approved_analyses,
                   operator_reputation.average_quality,
                   operator_reputation.confidence_level
            FROM users
            LEFT JOIN operator_reputation
                ON operator_reputation.user_id = users.id
            ORDER BY users.username
            """
        ).fetchall()
    return render_template("users.html", users=users, roles=sorted(VALID_ROLES))


@users_bp.route("/create", methods=["GET", "POST"])
@role_required("ADMIN")
def create_user():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        role = request.form.get("role", "").upper()

        if len(username) < 3:
            flash("O usuário deve ter pelo menos 3 caracteres.", "error")
            return render_template("create_user.html", roles=sorted(VALID_ROLES))
        if len(password) < 10:
            flash("A senha deve ter pelo menos 10 caracteres.", "error")
            return render_template("create_user.html", roles=sorted(VALID_ROLES))
        if role not in VALID_ROLES:
            flash("Função inválida.", "error")
            return render_template("create_user.html", roles=sorted(VALID_ROLES))

        now = datetime.now().isoformat(timespec="seconds")
        try:
            with get_connection() as connection:
                cursor = connection.execute(
                    """
                    INSERT INTO users (
                        username, password_hash, role, is_active,
                        must_change_password, created_at
                    )
                    VALUES (?, ?, ?, 1, 1, ?)
                    """,
                    (username, hash_password(password), role, now),
                )
                connection.execute(
                    """
                    INSERT INTO operator_reputation (user_id, updated_at)
                    VALUES (?, ?)
                    """,
                    (cursor.lastrowid, now),
                )
        except Exception as error:
            if "UNIQUE" in str(error).upper():
                flash("Esse nome de usuário já existe.", "error")
                return render_template(
                    "create_user.html",
                    roles=sorted(VALID_ROLES),
                )
            raise

        admin = current_user()
        log_action(
            f"USUARIO_CRIADO:{username}:{role}",
            admin["id"],
            admin["username"],
        )
        flash("Usuário criado com sucesso.", "success")
        return redirect(url_for("users.list_users"))

    return render_template("create_user.html", roles=sorted(VALID_ROLES))


@users_bp.post("/<int:user_id>/toggle")
@role_required("ADMIN")
def toggle_user(user_id):
    admin = current_user()
    if user_id == admin["id"]:
        flash("Você não pode desativar o próprio usuário.", "error")
        return redirect(url_for("users.list_users"))

    with get_connection() as connection:
        user = connection.execute(
            "SELECT username, is_active FROM users WHERE id = ?",
            (user_id,),
        ).fetchone()
        if not user:
            flash("Usuário não encontrado.", "error")
            return redirect(url_for("users.list_users"))
        new_status = 0 if user["is_active"] else 1
        connection.execute(
            "UPDATE users SET is_active = ? WHERE id = ?",
            (new_status, user_id),
        )

    log_action(
        f"USUARIO_STATUS:{user['username']}:{new_status}",
        admin["id"],
        admin["username"],
    )
    flash("Status do usuário atualizado.", "success")
    return redirect(url_for("users.list_users"))


@users_bp.post("/<int:user_id>/role")
@role_required("ADMIN")
def change_role(user_id):
    admin = current_user()
    role = request.form.get("role", "").upper()
    if role not in VALID_ROLES:
        flash("Função inválida.", "error")
        return redirect(url_for("users.list_users"))
    if user_id == admin["id"] and role != "ADMIN":
        flash("O administrador logado não pode remover a própria função.", "error")
        return redirect(url_for("users.list_users"))

    with get_connection() as connection:
        user = connection.execute(
            "SELECT username FROM users WHERE id = ?",
            (user_id,),
        ).fetchone()
        if not user:
            flash("Usuário não encontrado.", "error")
            return redirect(url_for("users.list_users"))
        connection.execute(
            "UPDATE users SET role = ? WHERE id = ?",
            (role, user_id),
        )

    log_action(
        f"USUARIO_ROLE:{user['username']}:{role}",
        admin["id"],
        admin["username"],
    )
    flash("Função atualizada.", "success")
    return redirect(url_for("users.list_users"))
