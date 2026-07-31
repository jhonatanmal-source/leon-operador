import csv
from pathlib import Path
from flask import Blueprint, render_template

from web_app.database.db import get_connection
from web_app.services.auth_service import current_user, login_required
from web_app.services.system_health_service import (
    _performance_summary,
    _shadow_summary,
    get_dashboard_system_status,
)

dashboard_bp = Blueprint("dashboard", __name__)

BASE_DIR = Path(__file__).resolve().parent.parent.parent
DATA_DIR = BASE_DIR / "data"


def _read_study_state():
    path = DATA_DIR / "study_state.txt"
    if path.exists():
        return path.read_text(encoding="utf-8", errors="replace").strip()
    return None


def _read_demo_state():
    path = DATA_DIR / "demo_execution_state.txt"
    if path.exists():
        return path.read_text(encoding="utf-8", errors="replace").strip()
    return None


def _recent_demo_orders(limit=5):
    path = DATA_DIR / "mt5_order_memory.csv"
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8", errors="replace", newline="") as f:
        rows = list(csv.DictReader(f, delimiter=";"))
    return rows[-limit:]


def _simulated_summary():
    path = DATA_DIR / "simulated_entries.csv"
    if not path.exists():
        return {"total": 0, "wins": 0, "losses": 0}
    with path.open("r", encoding="utf-8", errors="replace", newline="") as f:
        rows = list(csv.DictReader(f, delimiter=";"))
    return {
        "total": len(rows),
        "wins": sum(1 for r in rows if str(r.get("resultado", "")).startswith("WIN")),
        "losses": sum(1 for r in rows if r.get("resultado") == "LOSS"),
    }


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

    study_state = _read_study_state()
    demo_state = _read_demo_state()
    recent_orders = _recent_demo_orders()
    shadow = _shadow_summary()
    simulated = _simulated_summary()
    performance = _performance_summary()
    system = get_dashboard_system_status()

    return render_template(
        "dashboard.html",
        user=user,
        stats=stats,
        recent=recent,
        study=study_state,
        demo=demo_state,
        recent_orders=recent_orders,
        shadow=shadow,
        simulated=simulated,
        performance=performance,
        system=system,
    )
