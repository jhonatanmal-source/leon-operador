"""Serviço de credenciais MT5 gerenciadas pelo painel web.

Armazena login/servidor/senha do MetaTrader 5 de forma criptografada
(Fernet + chave mestra `/opt/leon/.master_key`) e oferece um teste de
conexão somente leitura.

Guards inegociáveis:
  - Conta REAL bloqueada em código (salvamento recusa REAL; teste sinaliza
    `is_real` e a rota exibe alerta bloqueante).
  - Senha NUNCA retornada a rotas/template/log — só usada internamente para
    o teste de conexão.
  - Nenhuma ordem enviada. `test_connection` chama apenas
    `initialize`/`account_info`/`shutdown`.
"""

import json
import os
from datetime import datetime
from pathlib import Path

from cryptography.fernet import Fernet, InvalidToken


PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
MASTER_KEY_PATH = Path("/opt/leon/.master_key")
CREDENTIALS_PATH = PROJECT_ROOT / "web_app" / "database" / "mt5_credentials.json"

# Somente contas DEMO são aceitas. REAL bloqueada em código.
ALLOWED_ACCOUNT_TYPES = frozenset({"DEMO"})

# ACCOUNT_TRADE_MODE_REAL == 2 (MetaTrader5). Usado para detectar conta real
# no resultado do teste de conexão.
ACCOUNT_TRADE_MODE_DEMO = 0
ACCOUNT_TRADE_MODE_CONTEST = 1
ACCOUNT_TRADE_MODE_REAL = 2

_TRADE_MODE_LABELS = {
    ACCOUNT_TRADE_MODE_DEMO: "DEMO",
    ACCOUNT_TRADE_MODE_CONTEST: "CONTEST",
    ACCOUNT_TRADE_MODE_REAL: "REAL",
}


class CredentialError(Exception):
    """Erro de negócio com mensagem segura (sem segredo)."""


# ── Chave mestra / Fernet ──────────────────────────────────────


def _load_fernet():
    """Carrega o Fernet a partir da chave mestra.

    Levanta CredentialError com mensagem clara (sem stack trace com segredo)
    quando a chave está ausente ou inválida.
    """
    if not MASTER_KEY_PATH.exists():
        raise CredentialError(
            "Chave mestra ausente em /opt/leon/.master_key. "
            "Não é possível salvar credenciais com segurança."
        )
    try:
        key = MASTER_KEY_PATH.read_bytes()
        return Fernet(key)
    except (ValueError, TypeError) as error:
        raise CredentialError(
            "Chave mestra inválida — verifique /opt/leon/.master_key."
        ) from error


def _encrypt(fernet, plaintext):
    return fernet.encrypt(plaintext.encode("utf-8")).decode("ascii")


def _decrypt(fernet, token):
    try:
        return fernet.decrypt(token.encode("ascii")).decode("utf-8")
    except InvalidToken as error:
        raise CredentialError(
            "Falha ao decifrar as credenciais — chave mestra incorreta "
            "ou arquivo corrompido."
        ) from error


# ── Storage ────────────────────────────────────────────────────


def _read_store():
    if not CREDENTIALS_PATH.exists():
        return {}
    try:
        with CREDENTIALS_PATH.open("r", encoding="utf-8") as file:
            data = json.load(file)
        return data if isinstance(data, dict) else {}
    except (json.JSONDecodeError, OSError):
        return {}


def _write_store(data):
    CREDENTIALS_PATH.parent.mkdir(parents=True, exist_ok=True)
    # Grava e aplica chmod 600 (dono leitura/escrita).
    with CREDENTIALS_PATH.open("w", encoding="utf-8") as file:
        json.dump(data, file, indent=2, sort_keys=True)
    try:
        os.chmod(CREDENTIALS_PATH, 0o600)
    except OSError:
        pass


# ── Validação ──────────────────────────────────────────────────


def _validate_input(login, server, password, account_type):
    login = str(login or "").strip()
    server = str(server or "").strip()
    password = password or ""
    account_type = str(account_type or "").strip().upper()

    if not login.isdigit() or not (4 <= len(login) <= 12):
        raise CredentialError("Login deve ser numérico com 4 a 12 dígitos.")
    if not server:
        raise CredentialError("Servidor não pode ficar vazio.")
    if len(password) < 4:
        raise CredentialError("Senha deve ter pelo menos 4 caracteres.")
    if account_type not in ALLOWED_ACCOUNT_TYPES:
        raise CredentialError(
            "Apenas contas DEMO são aceitas. Conta REAL bloqueada."
        )
    return login, server, password, account_type


# ── API pública ────────────────────────────────────────────────


def save_credentials(login, server, password, account_type, updated_by=None):
    """Valida e grava as credenciais criptografadas.

    Retorna dict de resultado {ok, error, status}. NUNCA ecoa a senha.
    """
    try:
        login, server, password, account_type = _validate_input(
            login, server, password, account_type
        )
    except CredentialError as error:
        return {"ok": False, "error": str(error)}

    try:
        fernet = _load_fernet()
    except CredentialError as error:
        return {"ok": False, "error": str(error)}

    record = {
        "login_enc": _encrypt(fernet, login),
        "server_enc": _encrypt(fernet, server),
        "password_enc": _encrypt(fernet, password),
        "account_type": account_type,
        "updated_at": datetime.now().isoformat(timespec="seconds"),
        "updated_by": str(updated_by or "").strip() or "desconhecido",
    }
    _write_store(record)
    return {"ok": True, "error": "", "status": get_masked_status()}


def load_credentials():
    """Carrega credenciais em claro para uso EXCLUSIVO do teste de conexão.

    NUNCA deve ser retornado a rotas/templates. Retorna None se não
    configurado.
    """
    store = _read_store()
    if not store or "login_enc" not in store:
        return None
    fernet = _load_fernet()
    return {
        "login": _decrypt(fernet, store["login_enc"]),
        "server": _decrypt(fernet, store["server_enc"]),
        "password": _decrypt(fernet, store["password_enc"]),
        "account_type": store.get("account_type", "DEMO"),
    }


def _mask_login(login):
    text = str(login or "")
    if len(text) <= 4:
        return "****"
    return f"{'*' * (len(text) - 4)}{text[-4:]}"


def get_masked_status():
    """Status mascarado para exibição. NUNCA inclui senha."""
    store = _read_store()
    if not store or "login_enc" not in store:
        return {
            "configured": False,
            "login": None,
            "server": None,
            "account_type": None,
            "updated_at": None,
            "updated_by": None,
        }
    try:
        fernet = _load_fernet()
        login_plain = _decrypt(fernet, store["login_enc"])
        server_plain = _decrypt(fernet, store["server_enc"])
    except CredentialError:
        login_plain = ""
        server_plain = ""
    return {
        "configured": True,
        "login": _mask_login(login_plain),
        "server": server_plain or "—",
        "account_type": store.get("account_type", "DEMO"),
        "updated_at": store.get("updated_at"),
        "updated_by": store.get("updated_by"),
    }


def test_connection(credentials=None):
    """Testa conexão MT5 com as credenciais salvas ou recebidas.

    Somente leitura: chama initialize/account_info/shutdown. Nenhuma ordem.
    Retorna {ok, error, account_login, server, trade_mode, is_real}.
    Detecta conta REAL (trade_mode == 2) e sinaliza `is_real=True`.
    """
    if credentials is None:
        try:
            credentials = load_credentials()
        except CredentialError as error:
            return _test_result(ok=False, error=str(error))
        if credentials is None:
            return _test_result(
                ok=False, error="Nenhuma credencial configurada."
            )

    login = str(credentials.get("login", "")).strip()
    server = str(credentials.get("server", "")).strip()
    password = credentials.get("password", "")

    if not login.isdigit():
        return _test_result(ok=False, error="Login inválido.")

    try:
        import mt5linux_compat as mt5
    except Exception as error:  # noqa: BLE001
        return _test_result(
            ok=False,
            error=f"Módulo MT5 indisponível: {type(error).__name__}.",
        )

    initialized = False
    try:
        initialized = bool(
            mt5.initialize(login=int(login), password=password, server=server)
        )
        if not initialized:
            try:
                err = mt5.last_error()
            except Exception:  # noqa: BLE001
                err = "desconhecido"
            return _test_result(
                ok=False,
                error=(
                    "Não foi possível conectar ao MT5 "
                    f"(terminal offline ou credenciais inválidas): {err}. "
                    "Se o terminal estiver instável, reinicie os scripts "
                    "start-rpyc-server.sh e run-mt5-headless."
                ),
            )

        account = mt5.account_info()
        if account is None:
            return _test_result(
                ok=False, error="Conta não disponível após conexão."
            )

        trade_mode = int(getattr(account, "trade_mode", -1))
        is_real = trade_mode == ACCOUNT_TRADE_MODE_REAL
        return _test_result(
            ok=not is_real,
            error=(
                "Conta REAL detectada — bloqueada por segurança."
                if is_real
                else ""
            ),
            account_login=_mask_login(getattr(account, "login", login)),
            server=getattr(account, "server", server),
            trade_mode=_TRADE_MODE_LABELS.get(trade_mode, str(trade_mode)),
            is_real=is_real,
        )
    except Exception as error:  # noqa: BLE001
        return _test_result(
            ok=False,
            error=f"Erro ao testar conexão: {type(error).__name__}.",
        )
    finally:
        if initialized:
            try:
                mt5.shutdown()
            except Exception:  # noqa: BLE001
                pass


def _test_result(
    ok,
    error="",
    account_login=None,
    server=None,
    trade_mode=None,
    is_real=False,
):
    return {
        "ok": bool(ok),
        "error": error,
        "account_login": account_login,
        "server": server,
        "trade_mode": trade_mode,
        "is_real": bool(is_real),
    }
