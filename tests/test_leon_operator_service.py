import re
import unittest
from pathlib import Path


SERVICE_FILE = Path(__file__).resolve().parents[1] / "deploy" / "systemd" / "leon-operator.service"


def _parse_unit(path):
    raw = path.read_text(encoding="utf-8")
    sections = {}
    current_section = None
    current_keys = {}

    for line in raw.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        section_match = re.match(r"^\[(.+)]$", stripped)
        if section_match:
            if current_section is not None:
                sections[current_section] = current_keys
            current_section = section_match.group(1)
            current_keys = {}
            continue
        if current_section is None:
            continue
        kv_match = re.match(r"^([^=]+)=(.*)", stripped)
        if kv_match:
            key = kv_match.group(1).strip()
            val = kv_match.group(2).strip()
            if key in current_keys:
                prev = current_keys[key]
                if isinstance(prev, list):
                    prev.append(val)
                else:
                    current_keys[key] = [prev, val]
            else:
                current_keys[key] = val

    if current_section is not None:
        sections[current_section] = current_keys

    return raw, sections


class TestLeonOperatorService(unittest.TestCase):

    def setUp(self):
        self.assertTrue(
            SERVICE_FILE.is_file(),
            f"Service unit not found: {SERVICE_FILE}",
        )
        self.raw, self.unit = _parse_unit(SERVICE_FILE)

    # ── [Unit] ────────────────────────────────────────────

    def test_unit_section_exists(self):
        self.assertIn("Unit", self.unit)

    def test_unit_description_present(self):
        desc = self.unit["Unit"].get("Description", "")
        self.assertTrue(len(desc) > 0)

    def test_after_includes_network_online(self):
        after = self.unit["Unit"].get("After", "")
        self.assertIn("network-online.target", after.split())

    def test_after_includes_leon_mt5(self):
        after = self.unit["Unit"].get("After", "")
        self.assertIn("leon-mt5.service", after.split())

    def test_after_does_not_require_leon_mt5(self):
        self.assertNotIn("Requires=leon-mt5.service", self.raw)
        self.assertNotIn("Requires=leon-mt5", self.raw)

    # ── [Service] ─────────────────────────────────────────

    def test_service_section_exists(self):
        self.assertIn("Service", self.unit)

    def test_type_is_simple(self):
        self.assertEqual(self.unit["Service"].get("Type"), "simple")

    def test_user_is_leon(self):
        self.assertEqual(self.unit["Service"].get("User"), "leon")

    def test_working_directory(self):
        self.assertEqual(
            self.unit["Service"].get("WorkingDirectory"),
            "/opt/leon/app",
        )

    def test_pythonunbuffered_env(self):
        self.assertIn(
            "PYTHONUNBUFFERED=1",
            self._collect_envs(),
        )

    def test_pythonpath_env(self):
        envs = self._collect_envs()
        self.assertIn(
            "PYTHONPATH=/opt/leon/app:/opt/leon/app/src",
            envs,
        )

    def test_exec_starts_operator_script(self):
        exe = self.unit["Service"].get("ExecStart", "")
        self.assertIn("/opt/leon/venv/bin/python", exe)
        self.assertIn("-u", exe.split())
        self.assertIn("/opt/leon/app/src/leon_operator.py", exe)

    def test_restart_is_on_failure(self):
        self.assertEqual(
            self.unit["Service"].get("Restart"),
            "on-failure",
        )

    def test_restart_sec_is_reasonable(self):
        sec = int(self.unit["Service"].get("RestartSec", "0"))
        self.assertGreaterEqual(sec, 5)
        self.assertLessEqual(sec, 120)

    def test_kill_signal_is_sigint(self):
        self.assertEqual(
            self.unit["Service"].get("KillSignal"),
            "SIGINT",
        )

    def test_timeout_stop_sec_is_reasonable(self):
        to = int(self.unit["Service"].get("TimeoutStopSec", "0"))
        self.assertGreaterEqual(to, 5)
        self.assertLessEqual(to, 120)

    # ── Hardening ─────────────────────────────────────────

    def test_protect_system_is_full(self):
        self.assertEqual(
            self.unit["Service"].get("ProtectSystem"),
            "full",
        )

    def test_read_write_paths_includes_data_and_logs(self):
        rwp = self.unit["Service"].get("ReadWritePaths", "")
        paths = rwp.split()
        self.assertIn("/opt/leon/app/data", paths)
        self.assertIn("/opt/leon/app/logs", paths)

    def test_no_new_privileges(self):
        self.assertEqual(
            self.unit["Service"].get("NoNewPrivileges"),
            "true",
        )

    def test_private_tmp(self):
        self.assertEqual(
            self.unit["Service"].get("PrivateTmp"),
            "true",
        )

    # ── [Install] ─────────────────────────────────────────

    def test_install_section_exists(self):
        self.assertIn("Install", self.unit)

    def test_wanted_by_multi_user(self):
        self.assertEqual(
            self.unit["Install"].get("WantedBy"),
            "multi-user.target",
        )

    # ── helpers ───────────────────────────────────────────

    def _collect_envs(self):
        section = self.unit["Service"]
        raw = section.get("Environment", "")
        if isinstance(raw, list):
            return raw
        return [raw]
