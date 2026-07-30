from flask import Blueprint, render_template, request

from web_app.services.auth_service import login_required
from web_app.services.system_health_service import build_leon_panel_context


leon_bp = Blueprint("leon", __name__, url_prefix="/leon")


@leon_bp.get("")
@login_required
def index():
    try:
        page = int(request.args.get("page", "1"))
    except (ValueError, TypeError):
        page = 1
    try:
        per_page = int(request.args.get("per_page", "20"))
    except (ValueError, TypeError):
        per_page = 20
    per_page = max(1, min(per_page, 100))

    return render_template(
        "leon_panel.html",
        panel=build_leon_panel_context(
            access_logs_page=page,
            access_logs_per_page=per_page,
        ),
    )
