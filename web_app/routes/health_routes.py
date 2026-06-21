from flask import Blueprint, render_template

from web_app.services.auth_service import login_required
from web_app.services.system_health_service import build_system_health


health_bp = Blueprint("health", __name__, url_prefix="/health")


@health_bp.get("")
@login_required
def index():
    return render_template(
        "system_health.html",
        health=build_system_health(),
    )
