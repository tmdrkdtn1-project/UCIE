"""UCIE Local V1 owner-only Windows auto-start without external release.

No scheduled task is created, run, or removed by these tests. On Windows,
only PowerShell's parser is invoked to verify source syntax; NEVER -File.
"""
from __future__ import annotations

from contextlib import redirect_stdout
import importlib.util
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
NAMES = (
    "install_ucie_local_v1_autostart.ps1",
    "status_ucie_local_v1_autostart.ps1",
    "remove_ucie_local_v1_autostart.ps1",
)


def load_runner():
    file = SCRIPTS / "run_ucie_local_v1_autostart.py"
    spec = importlib.util.spec_from_file_location("ucie_v1_autostart_test", file)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class UcieLocalAutostartSourceTests(unittest.TestCase):
    def test_one_fixed_ucie_loopback_target_without_old_foreign_port(self):
        runner = load_runner()
        self.assertEqual(runner.TASK_NAME, "UCIE-LocalV1-Web")
        self.assertEqual(runner.DEFAULT_PORT, 18767)
        self.assertNotEqual(runner.DEFAULT_PORT, 8767)

    def test_invalid_port_never_attempts_to_start(self):
        runner = load_runner()
        for port in (80, 8767, 65536, 0):
            with self.subTest(port=port), redirect_stdout(io.StringIO()) as out:
                self.assertEqual(runner.main(["--port", str(port)]), 2)
                message = json.loads(out.getvalue())
                self.assertEqual(message["schema"], runner.SCHEMA)
                self.assertEqual(
                    message["status"], "UCIE_AUTOSTART_INVALID_OR_LEGACY_PORT")

    def test_foreign_or_synthetic_owner_root_fails_closed(self):
        runner = load_runner()
        with tempfile.TemporaryDirectory(prefix="UCIE_AUTOSTART_TEST_") as t:
            root = Path(t)
            with self.assertRaises(runner.AutostartPreflightError):
                runner.validate_owner_environment(
                    root, Path(sys.executable), platform=os.name)
        with self.assertRaises(runner.AutostartPreflightError):
            runner.validate_owner_environment(
                Path("D:/UCIE"), Path(sys.executable), platform="posix")

    def test_installer_only_registers_dedicated_task_after_apply(self):
        install = (SCRIPTS / NAMES[0]).read_text(encoding="utf-8")
        status = (SCRIPTS / NAMES[1]).read_text(encoding="utf-8")
        remove = (SCRIPTS / NAMES[2]).read_text(encoding="utf-8")
        for content in (install, status, remove):
            self.assertIn("UCIE-LocalV1-Web", content)
            self.assertNotIn("UCIE-PublicMiner-Hourly", content)
            self.assertNotIn("cloudflared.exe", content)
            self.assertNotIn("Register-Service", content)
            self.assertNotIn("schtasks /delete", content)
        self.assertIn("if (-not $Apply)", install)
        self.assertIn("New-ScheduledTaskTrigger -AtLogOn", install)
        self.assertIn("New-ScheduledTaskTrigger -Once", install)
        self.assertIn("MultipleInstances = 'IgnoreNew'", install)
        self.assertIn("RestartCount = 3", install)
        self.assertIn("GetActiveTcpListeners()", install)
        self.assertIn("TaskPath = $taskPath", install)
        self.assertNotIn(" -Force", install)
        self.assertIn("UCIE_LOCAL_V1_HEALTHY", status)
        self.assertIn("UCIE_OWNER_LOCAL_FOUR_PILLAR_APP_V01", status)
        self.assertIn("if (-not $Apply)", remove)
        self.assertIn("UCIE_AUTOSTART_TASK_IDENTITY_MISMATCH_DO_NOT_REMOVE", remove)
        self.assertNotIn("Remove-Item", remove)

    def test_launch_target_calls_existing_local_app_without_browser(self):
        runner = load_runner()
        if os.name != "nt" or ROOT.resolve() != Path("D:/UCIE").resolve():
            self.skipTest("OWNER_WINDOWS_EXACT_D_UCIE_ONLY")
        runner.validate_owner_environment(
            ROOT, Path(sys.executable), platform=os.name)
        from ucie_miner import local_v1_app_v01 as app
        with patch.object(app, "main", return_value=0) as call:
            with redirect_stdout(io.StringIO()) as output:
                self.assertEqual(runner.main(["--port", "18767"]), 0)
            call.assert_called_once_with(["--port", "18767"])
            payload = json.loads(output.getvalue())
            self.assertFalse(payload["online_release_authorized"])
            self.assertFalse(payload["cloudflare_tunnel_modified"])
            self.assertEqual(payload["operating_database_writes"], 0)

    @unittest.skipUnless(os.name == "nt", "Windows PowerShell syntax parser only")
    def test_powershell_source_parses_without_executing_any_script(self):
        # ParseFile builds an AST but DOES NOT run, install, query or
        # unregister any Windows task.
        for name in NAMES:
            with self.subTest(script=name):
                path = SCRIPTS / name
                command = (
                    "$tokens = $null; $errorsList = $null; "
                    "[System.Management.Automation.Language.Parser]::ParseFile("
                    "'" + str(path).replace("'", "''") +
                    "', [ref]$tokens, [ref]$errorsList) | Out-Null; "
                    "if ($errorsList.Count -gt 0) { "
                    "$errorsList | ForEach-Object { Write-Output $_.Message }; exit 2 }"
                )
                proc = subprocess.run(
                    ["powershell.exe", "-NoProfile", "-NonInteractive",
                     "-Command", command],
                    capture_output=True, text=True, timeout=20, check=False)
                self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)


if __name__ == "__main__":
    unittest.main()
