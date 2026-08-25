"""Testes das rotas de conta MT5 (web_app/routes/mt5_account_routes.py).

Cobrem: exigência de role ADMIN, salvamento válido/ inválido, bloqueio de
conta REAL no teste de conexão, ausência de vazamento de senha em resposta.
Usa DB SQLite temporário e o serviço mockado (sem tocar chave mestra real).
"""

import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from cryptography.fernet import Fernet


class Mt5AccountRoutesTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._tmp = tempfile.mkdtemp()
        cls._db_path = Path(cls._tmp) / "leon_web_test.db"
        cls._master_key = Path(cls._tmp) / "master_key"
        cls._master_key.write_bytes(Fernet.generate_key())
        cls._cred_path = Path(cls._tmp) / "mt5_credentials.json"

        from web_app import config

        cls._db_patch = patch.object(config, "DATABASE_PATH", cls._db_path)
        cls._db_patch.start()

        from web_app.database import db as db_module

        # `config.py` lê DEFAULT_ADMIN_* no import-time; se o módulo já foi
        # importado por outro teste, mudar os.environ não tem efeito. Patch
        # direto dos nomes importados em db.py garante o admin de teste.
        cls._db_patch2 = patch.object(db_module, "DATABASE_PATH", cls._db_path)
        cls._db_patch3 = patch.object(db_module, "DEFAULT_ADMIN_USERNAME", "admin_test")
        cls._db_patch4 = patch.object(
            db_module, "DEFAULT_ADMIN_PASSWORD", "senha-admin-teste-123"
        )
        cls._db_patch2.start()
        cls._db_patch3.start()
        cls._db_patch4.start()

        from web_app.services import mt5_credential_service as service

        cls.service = service
        cls._svc_key = patch.object(service, "MASTER_KEY_PATH", cls._master_key)
        cls._svc_store = patch.object(service, "CREDENTIALS_PATH", cls._cred_path)
        cls._svc_key.start()
        cls._svc_store.start()

        # `logs/web_access.log` real é root:leon (640) — landmine conhecida
        # (ver handoff, pendência #11). Isola o log de acesso em arquivo tmp
        # para não depender de permissão de produção.
        from web_app.services import access_log_service

        cls._log_path = Path(cls._tmp) / "web_access.log"
        cls._log_patch = patch.object(access_log_service, "LOG_FILE", cls._log_path)
        cls._log_patch.start()

        from web_app.app import create_app

        cls.app = create_app({"TESTING": True, "WTF_CSRF_ENABLED": False})

    @classmethod
    def tearDownClass(cls):
        for p in (
            cls._db_patch,
            cls._db_patch2,
            cls._db_patch3,
            cls._db_patch4,
            cls._svc_key,
            cls._svc_store,
            cls._log_patch,
        ):
            p.stop()
        os.environ.pop("LEON_WEB_ADMIN_USERNAME", None)
        os.environ.pop("LEON_WEB_ADMIN_PASSWORD", None)
        __import__("shutil").rmtree(cls._tmp, ignore_errors=True)

    def setUp(self):
        if self._cred_path.exists():
            self._cred_path.unlink()
        self.client = self.app.test_client()

    def _login_admin(self):
        with self.app.app_context():
            from web_app.database.db import get_connection

            with get_connection() as connection:
                row = connection.execute(
                    "SELECT id FROM users WHERE username = ?", ("admin_test",)
                ).fetchone()
            admin_id = row["id"]
        with self.client.session_transaction() as sess:
            sess["user_id"] = admin_id
            sess["_csrf_token"] = "test-token"
        return admin_id

    def _form(self, **extra):
        data = {"csrf_token": "test-token"}
        data.update(extra)
        return data

    # ── Permissão ────────────────────────────────────────────

    def test_index_requires_login(self):
        response = self.client.get("/mt5-account", follow_redirects=False)
        self.assertEqual(response.status_code, 302)
        self.assertIn("/login", response.headers["Location"])

    def test_index_forbidden_for_non_admin(self):
        with self.app.app_context():
            from datetime import datetime

            from web_app.database.db import get_connection
            from web_app.services.auth_service import hash_password

            with get_connection() as connection:
                cursor = connection.execute(
                    """
                    INSERT INTO users (username, password_hash, role, is_active,
                        must_change_password, created_at)
                    VALUES (?, ?, 'VISUALIZADOR', 1, 0, ?)
                    """,
                    ("viewer_test", hash_password("x" * 10),
                     datetime.now().isoformat(timespec="seconds")),
                )
                viewer_id = cursor.lastrowid
        with self.client.session_transaction() as sess:
            sess["user_id"] = viewer_id
        response = self.client.get("/mt5-account", follow_redirects=False)
        self.assertEqual(response.status_code, 302)
        self.assertIn("/", response.headers["Location"])

    def test_index_ok_for_admin(self):
        self._login_admin()
        response = self.client.get("/mt5-account")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Conta MT5", response.data)

    # ── Salvamento ───────────────────────────────────────────

    def test_save_valid_demo_credentials(self):
        self._login_admin()
        response = self.client.post(
            "/mt5-account/save",
            data=self._form(
                login="12345678",
                server="Broker-Demo",
                password="senha123",
                confirm_password="senha123",
                account_type="DEMO",
            ),
            follow_redirects=True,
        )
        self.assertEqual(response.status_code, 200)
        status = self.service.get_masked_status()
        self.assertTrue(status["configured"])
        self.assertNotIn(b"senha123", response.data)

    def test_save_password_mismatch(self):
        self._login_admin()
        response = self.client.post(
            "/mt5-account/save",
            data=self._form(
                login="12345678",
                server="Broker-Demo",
                password="senha123",
                confirm_password="outra",
                account_type="DEMO",
            ),
            follow_redirects=True,
        )
        self.assertIn("confirma", response.data.decode("utf-8").lower())
        self.assertFalse(self.service.get_masked_status()["configured"])

    def test_save_rejects_real_type(self):
        self._login_admin()
        self.client.post(
            "/mt5-account/save",
            data=self._form(
                login="12345678",
                server="Broker-Real",
                password="senha123",
                confirm_password="senha123",
                account_type="REAL",
            ),
            follow_redirects=True,
        )
        self.assertFalse(self.service.get_masked_status()["configured"])

    # ── Teste de conexão ─────────────────────────────────────

    def test_test_connection_blocks_real_account(self):
        self._login_admin()
        fake_result = {
            "ok": False,
            "error": "Conta REAL detectada — bloqueada por segurança.",
            "account_login": "****5678",
            "server": "Broker-Real",
            "trade_mode": "REAL",
            "is_real": True,
        }
        with patch.object(self.service, "test_connection", return_value=fake_result):
            response = self.client.post(
                "/mt5-account/test",
                data=self._form(login="12345678", server="Broker-Real", password="x"),
                follow_redirects=True,
            )
        self.assertEqual(response.status_code, 200)
        self.assertIn("REAL", response.data.decode("utf-8"))

    def test_test_connection_demo_success(self):
        self._login_admin()
        fake_result = {
            "ok": True,
            "error": "",
            "account_login": "****5678",
            "server": "Broker-Demo",
            "trade_mode": "DEMO",
            "is_real": False,
        }
        with patch.object(self.service, "test_connection", return_value=fake_result):
            response = self.client.post(
                "/mt5-account/test",
                data=self._form(),
                follow_redirects=True,
            )
        self.assertEqual(response.status_code, 200)
        self.assertIn("OK", response.data.decode("utf-8"))


if __name__ == "__main__":
    unittest.main()
