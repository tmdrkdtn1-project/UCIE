"""UCIE first-party bootstrap and Task installer relocated preview regression.

Three existing owner Windows scripts gain -StagePreview only; this flag emits
a safe source-path receipt from a disposable UCIE_PROJECT/UCIE hierarchy and
never starts jobs, reads SQLite, installs venv, or changes C40/MCP state.
Windows tests actually execute all three staged PowerShell entrypoints.
"""
from __future__ import annotations

from hashlib import sha256
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import unittest

REPO = Path(__file__).resolve().parents[1]
FILES = (
    "bootstrap_local.ps1",
    "install_hourly_task.ps1",
    "install_internal_minute_task.ps1",
)
MUTATORS = {
    "bootstrap_local.ps1": "-Setup",
    "install_hourly_task.ps1": "-Install",
    "install_internal_minute_task.ps1": "-Install",
}
EXPECTED_LEGACY_GUARDS = {
    "bootstrap_local.ps1": "UCIE_ROOT_MUST_BE_D_UCIE",
    "install_hourly_task.ps1": "EXPECTED_UCIE_ROOT_D_DRIVE",
    "install_internal_minute_task.ps1": "UCIE_P10_EXPECTED_EXACT_ROOT",
}


class UCIEStagedOwnerScriptBackcompatTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="UCIE_STAGE_OWNER_SCRIPT_")
        self.addCleanup(self.tmp.cleanup)
        self.temp = Path(self.tmp.name)
        self.root = self.temp / "UCIE_PROJECT" / "UCIE"
        self.scripts = self.root / "scripts"
        self.scripts.mkdir(parents=True)
        self.before = {}
        for name in FILES:
            source = REPO / "scripts" / name
            self.before[name] = sha256(source.read_bytes()).hexdigest()
            shutil.copyfile(source, self.scripts / name)
        self.sentinel = self.temp / "UCIE_OWNER_RUNTIME_NOT_TOUCHED.txt"
        self.sentinel.write_bytes(b"KEEP original UCIE tasks and MCP tunnel running")
        self.sentinel_sha = sha256(self.sentinel.read_bytes()).hexdigest()

    def _assert_no_writes(self):
        self.assertEqual(sha256(self.sentinel.read_bytes()).hexdigest(),
                         self.sentinel_sha)
        for name in FILES:
            self.assertEqual(
                sha256((self.scripts / name).read_bytes()).hexdigest(),
                self.before[name])
        for name in ("runtime", ".venv", ".git", ".ucie_bridge_state"):
            self.assertFalse((self.root / name).exists())
        self.assertEqual(
            {f.name for f in self.scripts.iterdir()}, set(FILES))

    def _powershell(self, name: str, *flags: str):
        ps = shutil.which("powershell.exe")
        if not ps:
            self.skipTest("native Windows PowerShell 5.1 not available")
        return subprocess.run(
            [ps, "-NoProfile", "-NonInteractive", "-File",
             str(self.scripts / name), *flags],
            cwd=self.root, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            timeout=25, check=False,
        )

    def test_01_three_scripts_retain_original_task_and_bootstrap_owners(self):
        for name in FILES:
            with self.subTest(name=name):
                text = (REPO / "scripts" / name).read_text("utf-8")
                self.assertIn(EXPECTED_LEGACY_GUARDS[name], text)
                self.assertIn("D:\\UCIE", text)
                self.assertIn("StagePreview", text)
                self.assertIn("UCIE_STAGE_PREVIEW_ONLY_NO_SETUP_OR_TASK_MUTATION", text)
                self.assertIn("UCIE_STAGE_PREVIEW_MUTATING_ACTION_DENIED", text)
                self.assertIn("UCIE_STAGE_PREVIEW_INDIRECT_PATH_DENIED", text)
                self.assertIn("LIVE_ROOT_CUTOVER_AUTHORIZED=FALSE", text)
        self._assert_no_writes()

    def test_02_preview_guard_precedes_existing_mutation_paths(self):
        for name in FILES:
            with self.subTest(name=name):
                text = (REPO / "scripts" / name).read_text("utf-8")
                guard = text.index("if ($StagePreview) {")
                legacy = text.index(EXPECTED_LEGACY_GUARDS[name])
                self.assertLess(guard, legacy)
                self.assertLess(
                    text.index("UCIE_STAGE_PREVIEW_MUTATING_ACTION_DENIED"),
                    text.index("UCIE_STAGE_PREVIEW_ONLY_NO_SETUP_OR_TASK_MUTATION"))
                self.assertIn("return\n}", text[guard:legacy])
        self._assert_no_writes()

    def test_03_stage_preview_has_no_mutating_operating_command(self):
        for name in FILES:
            with self.subTest(name=name):
                text = (REPO / "scripts" / name).read_text("utf-8")
                preview = text.split("if ($StagePreview) {", 1)[1]
                preview = preview.split("\n}\n", 1)[0]
                self.assertNotRegex(preview, r"(?im)^\s*(?:New-Item|Copy-Item|Move-Item|Remove-Item|Rename-Item|Set-Item|Register-ScheduledTask|Start-ScheduledTask|Stop-ScheduledTask|New-ScheduledTaskAction|Start-Process|Invoke-RestMethod|Invoke-WebRequest|Out-File|Set-Content)\b")
                self.assertIn("$PSScriptRoot", preview)
                self.assertIn("$PSCommandPath", preview)
                self.assertIn("Get-Item -LiteralPath $path", preview)
        self._assert_no_writes()

    def test_04_stage_does_not_contain_git_sqlite_venv_mcp_state(self):
        self._assert_no_writes()

    def test_05_original_executable_task_installers_still_explicit_opt_in(self):
        hourly = (REPO / "scripts" / FILES[1]).read_text("utf-8")
        internal = (REPO / "scripts" / FILES[2]).read_text("utf-8")
        boot = (REPO / "scripts" / FILES[0]).read_text("utf-8")
        self.assertIn("if (-not $Install)", hourly)
        self.assertIn("if (-not $Install)", internal)
        self.assertIn("if ($Setup)", boot)
        self.assertIn("UCIE_SCHEDULE_ALREADY_EXISTS_REFUSE_OVERWRITE", hourly)
        self.assertIn("UCIE_P10_EXISTING_TASK_REFUSE_OVERWRITE", internal)
        self.assertIn("Register-ScheduledTask", hourly)
        self.assertIn("Register-ScheduledTask", internal)
        self._assert_no_writes()

    @unittest.skipUnless(os.name == "nt", "native Windows-only PowerShell test")
    def test_06_windows_stage_preview_real_execution_all_three_scripts(self):
        for name in FILES:
            with self.subTest(name=name):
                r = self._powershell(name, "-StagePreview")
                self.assertEqual(r.returncode, 0,
                                 r.stderr.decode("utf-8", errors="replace")[-600:])
                text = r.stdout.decode("utf-8-sig", errors="replace")
                self.assertIn("UCIE_STAGE_PREVIEW_ONLY_NO_SETUP_OR_TASK_MUTATION", text)
                self.assertIn("STAGED_CODE_ROOT=", text)
                self.assertIn("GIT_VENV_RUNTIME_MCP_TUNNEL_NOT_INSPECTED_OR_MODIFIED", text)
                self.assertIn("LIVE_ROOT_CUTOVER_AUTHORIZED=FALSE", text)
                self._assert_no_writes()

    @unittest.skipUnless(os.name == "nt", "native Windows-only PowerShell test")
    def test_07_stage_preview_plus_install_or_setup_must_fail_closed(self):
        for name in FILES:
            with self.subTest(name=name):
                r = self._powershell(name, "-StagePreview", MUTATORS[name])
                self.assertNotEqual(r.returncode, 0)
                combined = (r.stdout + r.stderr).decode("utf-8", errors="replace")
                self.assertIn("UCIE_STAGE_PREVIEW_MUTATING_ACTION_DENIED", combined)
                self._assert_no_writes()

    @unittest.skipUnless(os.name == "nt", "native Windows-only PowerShell test")
    def test_08_staged_root_without_optin_follows_strict_legacy_guard(self):
        for name in FILES:
            with self.subTest(name=name):
                r = self._powershell(name)
                self.assertNotEqual(r.returncode, 0)
                combined = (r.stdout + r.stderr).decode("utf-8", errors="replace")
                self.assertIn(EXPECTED_LEGACY_GUARDS[name], combined)
                self._assert_no_writes()

    @unittest.skipUnless(os.name == "nt", "native Windows-only PowerShell test")
    def test_09_wrong_parent_uses_no_operating_paths(self):
        wrong = self.temp / "FOREIGN_PARENT" / "UCIE" / "scripts"
        wrong.mkdir(parents=True)
        for name in FILES:
            shutil.copyfile(self.scripts / name, wrong / name)
        original = self.scripts
        self.scripts = wrong
        try:
            for name in FILES:
                with self.subTest(name=name):
                    r = self._powershell(name, "-StagePreview")
                    self.assertNotEqual(r.returncode, 0)
                    msg = (r.stdout + r.stderr).decode("utf-8", errors="replace")
                    self.assertIn("UCIE_STAGE_PREVIEW_EXACT_HIERARCHY_REQUIRED", msg)
        finally:
            self.scripts = original
        self._assert_no_writes()

    @unittest.skipUnless(os.name == "nt", "native Windows-only PowerShell test")
    def test_10_windows_native_syntax_parsing_all_three(self):
        ps = shutil.which("powershell.exe")
        if not ps:
            self.skipTest("native PowerShell 5.1 unavailable")
        for name in FILES:
            with self.subTest(name=name):
                path = str(REPO / "scripts" / name).replace("'", "''")
                code = (
                    "$t=$null;$err=$null;"
                    "[System.Management.Automation.Language.Parser]::ParseFile("
                    f"'{path}',[ref]$t,[ref]$err)|Out-Null;"
                    "if($err.Count -gt 0){exit 2};exit 0"
                )
                result = subprocess.run(
                    [ps, "-NoProfile", "-NonInteractive", "-Command", code],
                    cwd=REPO, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                    timeout=25, check=False)
                self.assertEqual(result.returncode, 0,
                                 result.stderr.decode("utf-8", errors="replace")[-500:])
        self._assert_no_writes()

    def test_11_previews_do_not_grant_live_root_migration_or_release(self):
        for name in FILES:
            text = (REPO / "scripts" / name).read_text("utf-8")
            self.assertIn("LIVE_ROOT_CUTOVER_AUTHORIZED=FALSE", text)
            self.assertNotIn("AUTO_MIGRATE_ROOT", text)
            self.assertNotIn("GIT_CLEAN_NEW_ROOT", text)
        self._assert_no_writes()


if __name__ == "__main__":
    unittest.main()
