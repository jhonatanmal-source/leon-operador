from flask import Blueprint, jsonify, render_template

from web_app.services.auth_service import login_required
from web_app.services.system_health_service import (
    build_system_health,
    get_mt5_account_summary,
)


health_bp = Blueprint("health", __name__, url_prefix="/health")


@health_bp.get("")
@login_required
def index():
    return render_template(
        "system_health.html",
        health=build_system_health(),
    )


@health_bp.get("/mt5-status")
@login_required
def mt5_status():
    """Endpoint JSON leve para o widget de status MT5 do sidebar (Fase C).

    Fora do context_processor (que roda em TODA request): o widget faz
    polling neste endpoint via JS, atualizando o sidebar sem depender do
    render de pagina. Reusa o mesmo cache stale-while-revalidate de
    get_mt5_account_summary — nunca bloqueia esperando o gateway MT5.
    Somente leitura; nenhuma ordem, nenhum dado sensivel (login mascarado).
    """
    return jsonify(get_mt5_account_summary())
