"""W13 UCIE owner-only reversible task-action rebind, static + native PS5 tests.

Tests execute ContractOnly and parser in disposable CI only. No actual owner
Task Scheduler changes, SQLite opens, private files, process/tunnel restarts.
"""
from __future__ import annotations
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "ucie_owner_task_rebind_v01.ps1"


class UCIEW13TaskRebindContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = SCRIPT.read_text("utf-8")

    def test_only_three_known_python_tasks_are_changed(self):
        text = self.source
        self.assertIn("Name='UCIE-PublicMiner-Hourly'", text)
        self.assertIn("Name='UCIE-Internal-Minute'", text)
        self.assertIn("Name='UCIE-LocalV1-Web'", text)
        self.assertIn("$c40='UCIE-C40-Recover'", text)
        self.assertEqual(text.count("Name='UCIE-"), 3)
        self.assertIn("foreach ($spec in $specs)", text)
        self.assertIn("C40ActionHash", text)
        self.assertNotIn("Set-ScheduledTask -TaskPath '\\' -TaskName $c40", text)

    def test_full_old_and_new_exact_paths_plus_relocated_flag(self):
        text = self.source
        self.assertIn("$old='D:\\UCIE'", text)
        self.assertIn("$new='D:\\UCIE_PROJECT\\UCIE'", text)
        self.assertIn("b8301014f9f8e5b2a7d40424684a98a05fcd040e", text)
        self.assertEqual(text.count("NewArgs="), 3)
        self.assertEqual(text.count("--owner-relocated-runtime'"), 3)
        self.assertIn("UCIE_OWNER_RELOCATED_RUNTIME_OPT_IN_V01", text)
        self.assertIn("UCIE_W13_PYTHON_315_MISSING", text)

    def test_no_restarts_or_git_cleanup_or_foreign_project_mutation(self):
        text = self.source
        for pattern in (
            r"(?m)^\s*(?:Start-ScheduledTask|Stop-ScheduledTask|Enable-ScheduledTask|Disable-ScheduledTask|"
            r"Register-ScheduledTask|Unregister-ScheduledTask|Start-Process|Stop-Process|"
            r"Restart-Service|Start-Service|Stop-Service|Invoke-RestMethod|Invoke-WebRequest)\b",
            r"\bgit\s+(?:clean|reset|pull|gc|prune)\b",
        ):
            self.assertNotRegex(text, pattern)
        self.assertNotIn("D:\\UCIE_DATA\\", text)
        self.assertNotIn("D:\\UCIE_PREVIEW\\", text)
        self.assertNotIn("C:\\Windows\\System32", text)

    def test_apply_has_private_journal_before_any_mutation(self):
        text = self.source
        self.assertIn("UCIE_W13_PRIVATE_ARCHIVE_ACL_REQUIRED", text)
        self.assertIn("UCIE_W13_JOURNAL_EXISTS_NO_REAPPLY", text)
        self.assertIn("UCIE_W13_PYTHON_TASK_NOT_ALREADY_DISABLED", text)
        self.assertIn("UCIE_W13_EXPLICIT_OWNER_APPROVAL_REQUIRED", text)
        self.assertIn("[IO.File]::Move($tmp,$journal)", text)
        self.assertLess(text.index("[IO.File]::Move($tmp,$journal)"),
                        text.index("Set-ScheduledTask -TaskPath '\\'"))
        self.assertIn("UCIE_W13_PARTIAL_FAILURE_MANUAL_ROLLBACK_REQUIRED", text)
        self.assertIn("UCIE_W13_ROLLBACK_UNKNOWN_ACTION_NO_GO", text)

    def test_rollback_is_explicit_and_journal_is_preserved(self):
        text = self.source
        self.assertIn("if ($Apply.IsPresent -eq $Rollback.IsPresent)", text)
        self.assertIn("UCIE_W13_ROLLBACK_JOURNAL_MISMATCH", text)
        self.assertIn("UCIE_W13_THREE_TASK_ACTIONS_ROLLED_BACK_DISABLED", text)
        self.assertIn("private_rollback_journal_preserved=$true", text)
        self.assertNotRegex(text, r"(?im)^\s*Remove-Item\s+-LiteralPath\s+\$journal")
        self.assertIn("live_cutover_authorized=$false", text)

    @unittest.skipUnless(os.name == "nt", "native Windows PowerShell only")
    def test_windows_contract_only_exits_before_host_access(self):
        pwsh = shutil.which("powershell.exe")
        if not pwsh:
            self.skipTest("Windows PowerShell 5.1 not installed")
        r = subprocess.run(
            [pwsh, "-NoProfile", "-NonInteractive", "-File", str(SCRIPT),
             "-ContractOnly"], capture_output=True, text=True,
            encoding="utf-8", errors="replace", timeout=25, check=False)
        self.assertEqual(r.returncode, 0, r.stderr[-700:])
        p = json.loads(r.stdout.strip())
        self.assertEqual(p["status"], "UCIE_W13_CONTRACT_ONLY")
        self.assertEqual(p["planned_python_task_count"], 3)
        for key in ("c40_action_modified", "tasks_queried",
                    "task_actions_changed", "services_restarted",
                    "operating_database_modified", "live_cutover_authorized"):
            self.assertFalse(p[key], key)

    @unittest.skipUnless(os.name == "nt", "native Windows PowerShell only")
    def test_windows_parser_and_mutation_is_refused_without_approval(self):
        pwsh = shutil.which("powershell.exe")
        if not pwsh:
            self.skipTest("Windows PowerShell 5.1 not installed")
        name = str(SCRIPT).replace("'", "''")
        code = ("$a=$null;$b=$null;"
                "[Management.Automation.Language.Parser]::ParseFile("
                f"'{name}',[ref]$a,[ref]$b)|Out-Null;"
                "if($b.Count -ne 0){$b|ForEach-Object{$_.Message};exit 2};exit 0")
        parsed = subprocess.run(
            [pwsh, "-NoProfile", "-NonInteractive", "-Command", code],
            capture_output=True, text=True, encoding="utf-8",
            errors="replace", timeout=25, check=False)
        self.assertEqual(parsed.returncode, 0, parsed.stderr + parsed.stdout)
        for flags in (("-Apply",), ("-Rollback",), ("-ContractOnly", "-Apply")):
            with self.subTest(flags=flags):
                r = subprocess.run(
                    [pwsh, "-NoProfile", "-NonInteractive", "-File",
                     str(SCRIPT), *flags],
                    capture_output=True, text=True, encoding="utf-8",
                    errors="replace", timeout=25, check=False)
                self.assertNotEqual(r.returncode, 0)
                self.assertIn("UCIE_W13_", r.stderr + r.stdout)


if __name__ == "__main__":
    unittest.main()
