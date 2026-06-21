from flask import Blueprint, render_template

from web_app.database.db import get_connection
from web_app.services.auth_service import current_user, login_required


dashboard_bp = Blueprint("dashboard", __name__)


@dashboard_bp.get("/")
@login_required
def index():
    user = current_user()
    role = user["role"]

    if role == "COLABORADOR":
        filter_sql = "WHERE user_id = ?"
        params = (user["id"],)
    elif role == "VISUALIZADOR":
        filter_sql = "WHERE status = 'APROVADA'"
        params = ()
    else:
        filter_sql = ""
        params = ()

    with get_connection() as connection:
        total = connection.execute(
            f"SELECT COUNT(*) AS total FROM human_analyses {filter_sql}",
            params,
        ).fetchone()["total"]

        def status_count(status):
            connector = "AND" if filter_sql else "WHERE"
            return connection.execute(
                f"""
                SELECT COUNT(*) AS total
                FROM human_analyses
                {filter_sql} {connector} status = ?
                """,
                (*params, status),
            ).fetchone()["total"]

        active_users = connection.execute(
            "SELECT COUNT(*) AS total FROM users WHERE is_active = 1"
        ).fetchone()["total"]
        pending = status_count("PENDENTE")
        approved = status_count("APROVADA")
        rejected = status_count("REJEITADA")
        recent = connection.execute(
            f"""
            SELECT human_analyses.*, users.username
            FROM human_analyses
            JOIN users ON users.id = human_analyses.user_id
            {filter_sql}
            ORDER BY human_analyses.id DESC
            LIMIT 5
            """,
            params,
        ).fetchall()

    stats = {
        "total": total,
        "pending": pending,
        "approved": approved,
        "rejected": rejected,
        "active_users": active_users,
    }
    return render_template(
        "dashboard.html",
        user=user,
        stats=stats,
        recent=recent,
    )
