"""Testes do serviço de credenciais MT5 (web_app/services/mt5_credential_service.py).

Cobrem: validação de entrada, criptografia/descriptografia, guard de conta
REAL (salvamento e teste de conexão), ausência de vazamento de senha no
status mascarado, chmod 600 do arquivo de storage.
"""

import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from cryptography.fernet import Fernet

from web_app.services import mt5_credential_service as service


class Mt5CredentialServiceTests(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = Path(self._make_tmp_dir())
        self.master_key_path = self.tmp_dir / "master_key"
        self.master_key_path.write_bytes(Fernet.generate_key())
        self.credentials_path = self.tmp_dir / "mt5_credentials.json"

        self._patches = [
            patch.object(service, "MASTER_KEY_PATH", self.master_key_path),
            patch.object(service, "CREDENTIALS_PATH", self.credentials_path),
        ]
        for p in self._patches:
            p.start()
        self.addCleanup(self._stop_patches)

    def _stop_patches(self):
        for p in self._patches:
            p.stop()

    def _make_tmp_dir(self):
        import tempfile

        directory = tempfile.mkdtemp()
        self.addCleanup(lambda: __import__("shutil").rmtree(directory, ignore_errors=True))
        return directory

    # ── Validação ────────────────────────────────────────────

    def test_save_rejects_non_numeric_login(self):
        result = service.save_credentials("abc123", "Broker-Demo", "senha123", "DEMO")
        self.assertFalse(result["ok"])
        self.assertIn("Login", result["error"])

    def test_save_rejects_short_login(self):
        result = service.save_credentials("123", "Broker-Demo", "senha123", "DEMO")
        self.assertFalse(result["ok"])

    def test_save_rejects_empty_server(self):
        result = service.save_credentials("12345678", "", "senha123", "DEMO")
        self.assertFalse(result["ok"])
        self.assertIn("Servidor", result["error"])

    def test_save_rejects_short_password(self):
        result = service.save_credentials("12345678", "Broker-Demo", "abc", "DEMO")
        self.assertFalse(result["ok"])
        self.assertIn("Senha", result["error"])

    def test_save_rejects_real_account_type(self):
        result = service.save_credentials(
            "12345678", "Broker-Demo", "senha123", "REAL"
        )
        self.assertFalse(result["ok"])
        self.assertIn("REAL", result["error"])

    def test_save_rejects_unknown_account_type(self):
        result = service.save_credentials(
            "12345678", "Broker-Demo", "senha123", "CONTEST"
        )
        self.assertFalse(result["ok"])

    # ── Persistência e criptografia ─────────────────────────

    def test_save_and_load_roundtrip(self):
        result = service.save_credentials(
            "12345678", "Broker-Demo", "senha123", "DEMO", updated_by="admin"
        )
        self.assertTrue(result["ok"], result.get("error"))

        loaded = service.load_credentials()
        self.assertEqual(loaded["login"], "12345678")
        self.assertEqual(loaded["server"], "Broker-Demo")
        self.assertEqual(loaded["password"], "senha123")
        self.assertEqual(loaded["account_type"], "DEMO")

    def test_stored_file_never_contains_plaintext_password(self):
        service.save_credentials(
            "12345678", "Broker-Demo", "s3nhaSecreta", "DEMO"
        )
        raw = self.credentials_path.read_text(encoding="utf-8")
        self.assertNotIn("s3nhaSecreta", raw)

    def test_stored_file_has_owner_only_permissions(self):
        service.save_credentials("12345678", "Broker-Demo", "senha123", "DEMO")
        mode = self.credentials_path.stat().st_mode & 0o777
        self.assertEqual(mode, 0o600)

    def test_load_credentials_returns_none_when_not_configured(self):
        self.assertIsNone(service.load_credentials())

    def test_missing_master_key_returns_clear_error_without_traceback_secret(self):
        missing_key_path = self.tmp_dir / "does_not_exist"
        with patch.object(service, "MASTER_KEY_PATH", missing_key_path):
            result = service.save_credentials(
                "12345678", "Broker-Demo", "senha123", "DEMO"
            )
        self.assertFalse(result["ok"])
        self.assertIn("Chave mestra", result["error"])

    # ── Status mascarado (sem vazamento de senha) ───────────

    def test_masked_status_never_exposes_password(self):
        service.save_credentials(
            "12345678", "Broker-Demo", "senha123", "DEMO", updated_by="admin"
        )
        status = service.get_masked_status()
        self.assertTrue(status["configured"])
        self.assertNotIn("password", status)
        self.assertNotIn("senha123", str(status))
        self.assertTrue(status["login"].endswith("5678"))
        self.assertTrue(status["login"].startswith("*"))

    def test_masked_status_when_not_configured(self):
        status = service.get_masked_status()
        self.assertFalse(status["configured"])
        self.assertIsNone(status["login"])

    # ── Teste de conexão (mock do módulo MT5) ───────────────

    def _install_fake_mt5(self, account_mock=None, initialize_ok=True):
        fake = MagicMock(name="mt5linux_compat")
        fake.initialize.return_value = initialize_ok
        fake.account_info.return_value = account_mock
        fake.last_error.return_value = (-1, "erro simulado")
        sys.modules["mt5linux_compat"] = fake
        self.addCleanup(lambda: sys.modules.pop("mt5linux_compat", None))
        return fake

    def test_test_connection_returns_error_when_not_configured(self):
        result = service.test_connection()
        self.assertFalse(result["ok"])
        self.assertIn("Nenhuma credencial", result["error"])

    def test_test_connection_fails_gracefully_when_initialize_fails(self):
        service.save_credentials("12345678", "Broker-Demo", "senha123", "DEMO")
        self._install_fake_mt5(initialize_ok=False)
        result = service.test_connection()
        self.assertFalse(result["ok"])
        self.assertIn("conectar", result["error"])

    def test_test_connection_blocks_real_account(self):
        service.save_credentials("12345678", "Broker-Demo", "senha123", "DEMO")
        account = MagicMock()
        account.trade_mode = service.ACCOUNT_TRADE_MODE_REAL
        account.login = 12345678
        account.server = "Broker-Real"
        fake = self._install_fake_mt5(account_mock=account)

        result = service.test_connection()

        self.assertTrue(result["is_real"])
        self.assertFalse(result["ok"])
        self.assertIn("REAL", result["error"])
        fake.shutdown.assert_called_once()
        fake.order_send.assert_not_called()

    def test_test_connection_succeeds_for_demo_account(self):
        service.save_credentials("12345678", "Broker-Demo", "senha123", "DEMO")
        account = MagicMock()
        account.trade_mode = service.ACCOUNT_TRADE_MODE_DEMO
        account.login = 12345678
        account.server = "Broker-Demo"
        fake = self._install_fake_mt5(account_mock=account)

        result = service.test_connection()

        self.assertTrue(result["ok"])
        self.assertFalse(result["is_real"])
        self.assertEqual(result["trade_mode"], "DEMO")
        fake.shutdown.assert_called_once()

    def test_test_connection_never_calls_order_functions(self):
        """Guard de segurança: nenhuma função de ordem é chamada no teste."""
        service.save_credentials("12345678", "Broker-Demo", "senha123", "DEMO")
        account = MagicMock()
        account.trade_mode = service.ACCOUNT_TRADE_MODE_DEMO
        account.login = 12345678
        account.server = "Broker-Demo"
        fake = self._install_fake_mt5(account_mock=account)

        service.test_connection()

        fake.order_send.assert_not_called()
        fake.order_check.assert_not_called()
        fake.login.assert_not_called()

    def test_test_connection_with_explicit_credentials_does_not_use_saved(self):
        service.save_credentials("11112222", "Broker-Saved", "senhaSalva", "DEMO")
        account = MagicMock()
        account.trade_mode = service.ACCOUNT_TRADE_MODE_DEMO
        account.login = 99998888
        account.server = "Broker-Explicit"
        self._install_fake_mt5(account_mock=account)

        result = service.test_connection(
            {"login": "99998888", "server": "Broker-Explicit", "password": "outraSenha"}
        )

        self.assertTrue(result["ok"])
        self.assertTrue(result["account_login"].endswith("8888"))


if __name__ == "__main__":
    unittest.main()
