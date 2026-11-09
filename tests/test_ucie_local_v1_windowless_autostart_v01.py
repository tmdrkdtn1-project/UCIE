"""UCIE Local V1 windowless launch preparation and safe task-migration checks.

Only exact owner D:\\UCIE is eligible for real Windows interpreter probing.
No test stops/restarts/registers any Task Scheduler job, modifies Cloudflare,
touches the public miner/SQLite, or calls a real browser.
"""
from __future__ import annotations

from contextlib import redirect_stdout
import importlib.util
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
TASK_NAME = "UCIE-LocalV1-Web"
PS_FILES = (
    "install_ucie_local_v1_autostart.ps1",
    "status_ucie_local_v1_autostart.ps1",
    "remove_ucie_local_v1_autostart.ps1",
    "set_ucie_local_v1_windowless.ps1",
)


def runner_module():
    spec = importlib.util.spec_from_file_location(
        "ucie_local_v1_windowless_test_runner",
        SCRIPTS / "run_ucie_local_v1_autostart.py",
    )
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class WindowlessOwnerTaskTest(unittest.TestCase):
    def test_exact_owner_launcher_only_accepts_its_two_venv_executables(self):
        launcher = runner_module()
        self.assertEqual(launcher.TASK_NAME, TASK_NAME)
        self.assertEqual(launcher.DEFAULT_PORT, 18767)
        with tempfile.TemporaryDirectory(prefix="UCIE_HIDDEN_TEST_") as tmp:
            with self.assertRaises(launcher.AutostartPreflightError):
                launcher.validate_owner_environment(
                    Path(tmp), Path(sys.executable), platform="nt")
        if os.name != "nt" or ROOT.resolve() != Path("D:/UCIE").resolve():
            self.skipTest("EXACT_OWNER_WINDOWS_ONLY")
        for name in ("python.exe", "pythonw.exe"):
            with self.subTest(executable=name):
                path = ROOT / ".venv" / "Scripts" / name
                self.assertTrue(path.is_file(), f"Owner venv missing {path}")
                self.assertEqual(
                    launcher.validate_owner_environment(
                        ROOT, path, platform="nt"),
                    ROOT / "src",
                )
        with self.assertRaises(launcher.AutostartPreflightError):
            launcher.validate_owner_environment(
                ROOT, ROOT / "scripts" / "run_ucie_local_v1_autostart.py",
                platform="nt",
            )

    def test_windowless_log_redirects_only_inside_supplied_first_party_root(self):
        launcher = runner_module()
        with tempfile.TemporaryDirectory(prefix="UCIE_HIDDEN_LOG_") as tmp:
            root = Path(tmp)
            (root / "runtime").mkdir()
            with patch.object(sys, "stdout") as stdout, patch.object(
                    sys, "stderr") as stderr:
                self.assertIsNone(launcher._configure_windowless_log(
                    root, Path("python.exe")))
                self.assertIs(sys.stdout, stdout)
                self.assertIs(sys.stderr, stderr)
                path = launcher._configure_windowless_log(
                    root, Path("pythonw.exe"))
                try:
                    print("UCIE_WINDOWLESS_FIRST_PARTY_LOG_OK", flush=True)
                finally:
                    sys.stdout.close()
            self.assertEqual(
                path, root / "runtime" / "ucie_local_v1_windowless.log")
            self.assertIn("UCIE_WINDOWLESS_FIRST_PARTY_LOG_OK",
                          path.read_text(encoding="utf-8"))

    def test_windowless_logger_refuses_external_symlink(self):
        launcher = runner_module()
        with tempfile.TemporaryDirectory(prefix="UCIE_HIDDEN_LINK_") as tmp:
            root = Path(tmp)
            with self.assertRaises(launcher.AutostartPreflightError):
                launcher._configure_windowless_log(
                    root, Path("pythonw.exe"))

    def test_scripts_pin_only_owned_task_and_preserve_fail_closed(self):
        install = (SCRIPTS / PS_FILES[0]).read_text(encoding="utf-8")
        status = (SCRIPTS / PS_FILES[1]).read_text(encoding="utf-8")
        remove = (SCRIPTS / PS_FILES[2]).read_text(encoding="utf-8")
        migrate = (SCRIPTS / PS_FILES[3]).read_text(encoding="utf-8")
        self.assertIn("pythonw.exe", install)
        self.assertIn("UCIE_CONSOLE_TASK_USE_SET_UCIE_LOCAL_V1_WINDOWLESS_PS1", install)
        self.assertIn("windowless_background_mode", status)
        self.assertIn("console_mode", status)
        self.assertIn("pythonw.exe", remove)
        self.assertIn("if (-not $Apply)", migrate)
        self.assertIn("Set-ScheduledTask -TaskName $taskName", migrate)
        self.assertIn("-Action $oldAction", migrate)
        self.assertIn("UCIE_LOCAL_V1_WINDOWLESS_APPLIED_AND_HEALTHY", migrate)
        self.assertIn("Invoke-RestMethod", migrate)
        self.assertIn("127.0.0.1", migrate)
        self.assertIn("Stop-ScheduledTask", migrate)
        self.assertIn("Start-ScheduledTask", migrate)
        for script in (install, status, remove, migrate):
            self.assertIn(TASK_NAME, script)
            self.assertNotIn("UCIE-PublicMiner-Hourly", script)
            self.assertNotIn("cloudflared.exe", script)
            self.assertNotIn("schtasks /delete", script)
            self.assertNotIn(" -Force", script)

    @unittest.skipUnless(os.name == "nt", "Windows PowerShell parser only")
    def test_windows_powershell_scripts_parse_without_executing(self):
        for file in PS_FILES:
            with self.subTest(file=file):
                path = SCRIPTS / file
                command = (
                    "$tok=$null;$errs=$null;"
                    "[System.Management.Automation.Language.Parser]::ParseFile("
                    "'" + str(path).replace("'", "''") +
                    "',[ref]$tok,[ref]$errs)|Out-Null;"
                    "if($errs.Count -gt 0){"
                    "$errs|ForEach-Object{Write-Output $_.Message};exit 2}"
                )
                result = subprocess.run(
                    ["powershell.exe", "-NoProfile", "-NonInteractive",
                     "-Command", command],
                    capture_output=True, text=True, encoding="utf-8",
                    errors="replace", timeout=20, check=False)
                self.assertEqual(
                    result.returncode, 0, result.stdout + result.stderr)

    @unittest.skipUnless(os.name == "nt", "Exact owner Windows only")
    def test_real_owner_windowless_interpreter_launches_a_disposable_probe(self):
        if ROOT.resolve() != Path("D:/UCIE").resolve():
            self.skipTest("EXACT_OWNER_D_UCIE_ONLY")
        with tempfile.TemporaryDirectory(prefix="UCIE_WINLESS_PROBE_") as tmp:
            output = Path(tmp) / "probe.json"
            pyw = ROOT / ".venv" / "Scripts" / "pythonw.exe"
            self.assertTrue(pyw.is_file())
            program = (
                "import json,os,sys,pathlib;"
                "pathlib.Path(sys.argv[1]).write_text(json.dumps({"
                "'exe':pathlib.Path(sys.executable).name.lower(),"
                "'stdout_none':sys.stdout is None,"
                "'stderr_none':sys.stderr is None,"
                "'os_name':os.name}),encoding='utf-8')"
            )
            result = subprocess.run(
                [str(pyw), "-B", "-c", program, str(output)],
                capture_output=True, text=True, encoding="utf-8",
                errors="replace", timeout=12, check=False)
            self.assertEqual(
                result.returncode, 0, result.stdout + result.stderr)
            self.assertTrue(output.is_file())
            data = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(data["exe"], "pythonw.exe")
            self.assertEqual(data["os_name"], "nt")

    @unittest.skipUnless(os.name == "nt", "Exact owner Windows dry-run only")
    def test_real_owner_migration_preview_never_changes_task(self):
        if ROOT.resolve() != Path("D:/UCIE").resolve():
            self.skipTest("EXACT_OWNER_D_UCIE_ONLY")
        result = subprocess.run(
            ["powershell.exe", "-NoProfile", "-NonInteractive", "-File",
             str(SCRIPTS / "set_ucie_local_v1_windowless.ps1")],
            capture_output=True, text=True, encoding="utf-8",
            errors="replace", timeout=20, check=False)
        self.assertEqual(
            result.returncode, 0, result.stdout + result.stderr)
        self.assertTrue(
            "PREVIEW_ONLY_NO_CHANGES" in result.stdout or
            "ALREADY_WINDOWLESS_NO_CHANGES" in result.stdout,
            result.stdout,
        )
        self.assertNotIn("APPLIED_AND_HEALTHY", result.stdout)


if __name__ == "__main__":
    unittest.main()
