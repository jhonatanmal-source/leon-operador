from flask import Blueprint, flash, redirect, render_template, url_for

from web_app.services.auth_service import login_required, role_required
from web_app.services.weekly_audit_service import (
    build_weekly_audit,
    save_weekly_audit,
)


weekly_audit_bp = Blueprint(
    "weekly_audit",
    __name__,
    url_prefix="/auditoria-semanal",
)


@weekly_audit_bp.get("")
@login_required
def index():
    return render_template(
        "weekly_audit.html",
        audit=build_weekly_audit(),
    )


@weekly_audit_bp.post("/gerar")
@role_required("ADMIN", "SUPERVISOR")
def generate():
    audit = build_weekly_audit()
    save_weekly_audit(audit)
    flash("Relatório semanal atualizado e salvo.", "success")
    return redirect(url_for("weekly_audit.index"))
