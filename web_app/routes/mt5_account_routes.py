"""Rotas administrativas para gestão de credenciais MT5 pelo painel web.

Todas as rotas exigem role ADMIN. Nenhuma ordem é enviada; nenhuma senha é
ecoada em flash, log ou resposta. Conta REAL é recusada tanto no salvamento
quanto no teste de conexão.
"""

from flask import (
    Blueprint,
    flash,
    redirect,
    render_template,
    request,
    url_for,
)

from web_app.services import mt5_credential_service
from web_app.services.access_log_service import log_action
from web_app.services.auth_service import current_user, role_required


mt5_account_bp = Blueprint("mt5_account", __name__, url_prefix="/mt5-account")


@mt5_account_bp.get("")
@role_required("ADMIN")
def index():
    status = mt5_credential_service.get_masked_status()
    return render_template("mt5_account.html", status=status, test_result=None)


@mt5_account_bp.post("/save")
@role_required("ADMIN")
def save():
    login = request.form.get("login", "")
    server = request.form.get("server", "")
    password = request.form.get("password", "")
    confirm_password = request.form.get("confirm_password", "")
    account_type = request.form.get("account_type", "")

    if password != confirm_password:
        flash("A confirmação de senha não corresponde.", "error")
        return redirect(url_for("mt5_account.index"))

    admin = current_user()
    result = mt5_credential_service.save_credentials(
        login=login,
        server=server,
        password=password,
        account_type=account_type,
        updated_by=admin["username"] if admin else None,
    )

    if not result["ok"]:
        flash(result["error"], "error")
        return redirect(url_for("mt5_account.index"))

    log_action(
        "MT5_CREDENCIAIS_SALVAS",
        admin["id"] if admin else None,
        admin["username"] if admin else None,
    )
    flash("Credenciais MT5 salvas com sucesso.", "success")
    return redirect(url_for("mt5_account.index"))


@mt5_account_bp.post("/test")
@role_required("ADMIN")
def test():
    login = request.form.get("login", "").strip()
    server = request.form.get("server", "").strip()
    password = request.form.get("password", "")

    credentials = None
    if login or server or password:
        credentials = {"login": login, "server": server, "password": password}

    result = mt5_credential_service.test_connection(credentials)

    admin = current_user()
    log_action(
        "MT5_CREDENCIAS_TESTE",
        admin["id"] if admin else None,
        admin["username"] if admin else None,
    )

    if result["is_real"]:
        flash(
            "BLOQUEADO: a conta detectada é REAL. "
            "Apenas contas DEMO são permitidas.",
            "error",
        )
    elif result["ok"]:
        flash(
            f"Conexão OK — conta {result['account_login']} "
            f"({result['trade_mode']}) no servidor {result['server']}.",
            "success",
        )
    else:
        flash(result["error"] or "Falha ao testar conexão.", "error")

    status = mt5_credential_service.get_masked_status()
    return render_template("mt5_account.html", status=status, test_result=result)
