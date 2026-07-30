from flask import Blueprint, render_template

from web_app.services.auth_service import login_required
from web_app.services.virtual_operations_service import get_virtual_operations_snapshot


virtual_operations_bp = Blueprint("virtual_operations", __name__, url_prefix="/central-virtual")


@virtual_operations_bp.get("")
@login_required
def index():
    return render_template(
        "central_virtual.html",
        virtual=get_virtual_operations_snapshot(),
    )
