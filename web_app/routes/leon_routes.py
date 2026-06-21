from flask import Blueprint, render_template

from web_app.services.auth_service import login_required
from web_app.services.system_health_service import build_leon_panel_context


leon_bp = Blueprint("leon", __name__, url_prefix="/leon")


@leon_bp.get("")
@login_required
def index():
    return render_template(
        "leon_panel.html",
        panel=build_leon_panel_context(),
    )
