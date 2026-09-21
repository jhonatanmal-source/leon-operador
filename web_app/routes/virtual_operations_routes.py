from functools import wraps

from flask import Blueprint, jsonify, render_template, request

from web_app.services.auth_service import current_user, login_required
from web_app.services.engineering_console_service import get_engineering_console_snapshot, public_job
from src import engineering_store as store


virtual_operations_bp = Blueprint("virtual_operations", __name__, url_prefix="/central-virtual")


@virtual_operations_bp.get("")
@login_required
def index():
    return render_template(
        "central_virtual.html",
        console=get_engineering_console_snapshot(can_manage=current_user()['role'] == 'ADMIN'),
    )


@virtual_operations_bp.after_request
def no_store(response):
    response.headers['Cache-Control'] = 'no-store'
    return response


def api_auth(admin=False):
    def decorate(view):
        @wraps(view)
        def wrapped(*args, **kwargs):
            user = current_user()
            if user is None:
                return jsonify(error='Autenticacao necessaria'), 401
            if admin and user['role'] != 'ADMIN':
                return jsonify(error='Acesso restrito a administradores'), 403
            return view(*args, **kwargs)
        return wrapped
    return decorate


@virtual_operations_bp.get('/snapshot')
@api_auth()
def snapshot():
    return jsonify(get_engineering_console_snapshot(can_manage=current_user()['role'] == 'ADMIN'))


@virtual_operations_bp.post('/jobs')
@api_auth(admin=True)
def jobs():
    # Global validate_csrf protects all mutations, including JSON requests.
    body = request.get_json(silent=True)
    if not isinstance(body, dict) or set(body) != {'kind'} or not isinstance(body['kind'], str):
        return jsonify(error='Informe somente kind'), 400
    store.init_store()
    try:
        job = store.enqueue_job(body['kind'], requested_by=str(current_user()['id']))
    except ValueError:
        return jsonify(error='Tipo de tarefa invalido'), 400
    except RuntimeError as error:
        return jsonify(error=store.sanitize_text(error)), 409
    return jsonify(job=public_job(job)), 202


@virtual_operations_bp.post('/automation')
@api_auth(admin=True)
def automation():
    body = request.get_json(silent=True)
    if not isinstance(body, dict) or set(body) != {'enabled'} or not isinstance(body['enabled'], bool):
        return jsonify(error='enabled deve ser booleano'), 400
    store.init_store()
    return jsonify(enabled=store.set_settings(enabled=body['enabled'])['enabled'])


@virtual_operations_bp.get('/artifacts/<artifact_id>')
@api_auth(admin=True)
def artifact(artifact_id):
    store.init_store()
    value = store.get_artifact(artifact_id)
    if value is None:
        return jsonify(error='Artefato nao encontrado'), 404
    return jsonify({k: store.sanitize_text(value[k]) if isinstance(value.get(k), str) else value.get(k)
                    for k in ('id', 'title', 'kind', 'job_id', 'created_at', 'content')})
