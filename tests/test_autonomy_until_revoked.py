import importlib.util
import tempfile
import unittest
from pathlib import Path
from datetime import datetime, timedelta

spec = importlib.util.spec_from_file_location('guard', Path(__file__).resolve().parents[1] / 'src/autonomy_guard.py')
guard = importlib.util.module_from_spec(spec)
spec.loader.exec_module(guard)

class AutonomyTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        guard.DATA_DIR = Path(self.tmp.name)
        guard.AUTONOMY_FILE = guard.DATA_DIR / 'state.json'
        guard.CONFIG_FILE = guard.DATA_DIR / 'config.ini'
        guard.CONFIG_FILE.write_text('[AUTONOMY]\nenabled=true\nscope=demo_execution\nmax_minutes=60\n')
        guard._salvar_estado({'enabled': True, 'scope': 'demo_execution', 'until_revoked': True})

    def test_indefinite(self):
        self.assertTrue(guard.status_autonomia()['active'])
        self.assertIsNone(guard.status_autonomia()['expires_at'])

    def test_revocation_persists(self):
        guard.revogar_autonomia()
        self.assertEqual(guard.status_autonomia()['reason'], 'AUTONOMY_REVOKED')
        self.assertFalse(guard.status_autonomia()['active'])

    def test_config_off(self):
        guard.CONFIG_FILE.write_text('[AUTONOMY]\nenabled=false\nscope=demo_execution\n')
        self.assertFalse(guard.status_autonomia()['active'])

    def test_real_scope_rejected(self):
        guard.CONFIG_FILE.write_text('[AUTONOMY]\nenabled=true\nscope=real_execution\n')
        self.assertFalse(guard.status_autonomia()['active'])

    def test_timed_grant_replaces_indefinite(self):
        self.assertTrue(guard.conceder_autonomia(30)['ok'])
        self.assertNotIn('until_revoked', guard._ler_estado())
        self.assertTrue(guard.status_autonomia()['active'])

    def test_missing_expiry_still_rejected(self):
        guard._salvar_estado({'enabled': True, 'scope': 'demo_execution'})
        self.assertFalse(guard.status_autonomia()['active'])

    def test_expired(self):
        guard._salvar_estado({'enabled': True, 'expires_at': (datetime.now()-timedelta(seconds=1)).isoformat()})
        self.assertEqual(guard.status_autonomia()['reason'], 'AUTONOMY_EXPIRED')

if __name__ == '__main__':
    unittest.main()
