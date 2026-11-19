"""W25: no-host post-recovery audit and redacted nested-W21 error contract.

No CI test runs owner -CheckLocal, W19 Apply, W21 Apply, Task Scheduler
mutations, SQLite handoff, C40 tunnel or owner HTTP interactions.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]
PROBE = ROOT / "scripts" / "ucie_owner_w25_w19_prejournal_probe_v01.ps1"
W21 = ROOT / "scripts" / "ucie_owner_w21_single_local_maintenance_v01.ps1"


class W25OwnerReadOnlyPrejournalContracts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.probe = PROBE.read_text(encoding="utf-8")
        cls.w21 = W21.read_text(encoding="utf-8")

    def test_probe_default_no_host_contract_first(self):
        source = self.probe
        self.assertLess(source.index("if($ContractOnly){"),
                        source.index("Get-ScheduledTask -TaskPath"))
        self.assertLess(source.index("UCIE_W25_EXPLICIT_READONLY_OWNER_APPROVAL_REQUIRED"),
                        source.index("Get-ScheduledTask -TaskPath"))
        self.assertIn("UCIE_W25_CONTRACT_ONLY_NO_HOST_ACCESS", source)
        self.assertIn("owner_tasks_queried=$false", source)
        self.assertIn("private_archive_accessed=$false", source)
        self.assertIn("sqlite_opened=$false", source)
        self.assertIn("journal_written=$false", source)
        self.assertIn("task_or_c40_modified=$false", source)

    def test_probe_current_recovery_instead_of_replaying_w19_apply(self):
        source = self.probe
        self.assertIn("UCIE_W24_PRE_REBIND_OWNER_RECOVERY_RECEIPT_V01.json", source)
        self.assertIn("UCIE_W24_PRE_REBIND_ORIGINAL_SERVICE_RESTORED", source)
        self.assertIn("UCIE_W21_LOCAL_MAINTENANCE_INTENT_V01.json", source)
        self.assertIn("UCIE_W21_LOCAL_MAINTENANCE_INTENT_HOLD", source)
        self.assertIn("UCIE_W19_OWNER_DATA_TASK_STAGE_JOURNAL_V01.json", source)
        self.assertIn("UCIE_W13_TASK_REBIND_V01.json", source)
        self.assertIn("UCIE_W20_LOCAL_PILOT_JOURNAL_V01.json", source)
        self.assertIn("UCIE_W19_LOCKSTEP_FINAL_DATA_V01", source)
        self.assertIn("$root+'\\runtime'", source)
        self.assertIn("UCIE_W25_EXPECTED_W19_ANCESTRY_MISSING", source)
        self.assertIn("UCIE_W25_RESTORED_TASK_ACTION_DRIFT", source)
        self.assertIn("UCIE_W25_PRIOR_INCIDENT_PROVENANCE_OR_C40_DRIFT", source)
        self.assertIn("UCIE_W25_RUNNING_OLD_ROOT_PREREQUISITES_VERIFIED__W19_DISABLED_PREJOURNAL_NOT_REPLAYED", source)
        self.assertIn("root_cause_verified=$false", source)
        self.assertIn("prior_w21_nested_error_reason='NOT_CAPTURED'", source)
        self.assertIn("c40_mcp_round_trip_verified=$false", source)
        self.assertIn("operating_sqlite_opened=$false", source)

    def test_probe_does_not_change_process_tasks_git_data(self):
        source = self.probe
        for forbidden in (
            "Stop-Process", "taskkill", "Start-ScheduledTask",
            "Disable-ScheduledTask", "Enable-ScheduledTask",
            "Set-ScheduledTask", "Register-ScheduledTask",
            "Unregister-ScheduledTask", "Restart-Service",
            "Remove-Item", "Move-Item", "Rename-Item",
            "Copy-Item", "New-Item", "New-ScheduledTask",
            "[IO.File]::Write", "git reset", "git clean",
            "git pull", "-ApplyLocal", "-RollbackLocal",
        ):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, source)
        self.assertIn("$env:GIT_OPTIONAL_LOCKS='0'", source)
        self.assertIn("GIT_OPTIONAL_LOCKS=$prior", source)

    def test_w21_identifies_nested_stage_and_strictly_redacts_error(self):
        source = self.w21
        stage_sequence = (
            "W19_OWNER_APPLY", "W19_STAGE_JOURNAL_REQUIRED",
            "W13_REBIND_JOURNAL_REQUIRED", "POST_W19_C40_ACTION_CHECK",
            "W20_LOCAL_PILOT", "W20_PILOT_JOURNAL_REQUIRED",
            "NEW_LOCALV1_TASK_ACTIONS_CHECK",
            "NEW_LOCALV1_HTTP_HEALTH_CHECK",
            "POST_W20_C40_ACTION_CHECK",
        )
        indexes = [source.index("$childStage='" + stage + "'")
                   for stage in stage_sequence]
        self.assertEqual(indexes, sorted(indexes))
        self.assertLess(indexes[0],
                        source.index("& $w19 -Apply -OwnerApproval $w19Approval"))
        self.assertIn("UCIE_W25_W21_SANITIZED_CHILD_FAILURE_V01", source)
        self.assertIn("UCIE_W25_NONCANONICAL_CHILD_EXCEPTION", source)
        self.assertIn("if($raw -cmatch '^UCIE_[A-Z0-9_]{5,100}$')", source)
        self.assertIn("if($kind -notmatch '^[A-Za-z][A-Za-z0-9]{0,60}$')", source)
        self.assertIn("stage=$childStage", source)
        self.assertIn("reason_code=$reason", source)
        self.assertIn("exception_class=$kind", source)
        self.assertIn("private_path_or_error_text_exposed=$false", source)
        self.assertIn("owner_maintenance_retry_authorized=$false", source)
        self.assertIn("throw 'UCIE_W21_LOCAL_ONCE_FAILED_PRESERVE_RECEIPTS_EXPLICIT_ROLLBACK_ONLY'", source)
        self.assertNotIn("exception_text=$raw", source)
        self.assertNotIn("error_message=$raw", source)
        self.assertNotIn("Write-Host $raw", source)

    def test_native_powershell_parser_default_and_denied_owner(self):
        exe = "powershell.exe" if os.name == "nt" else shutil.which("pwsh")
        if not exe:
            self.skipTest("PowerShell not available in this CI")
        escaped = str(PROBE).replace("'", "''")
        parser = (
            "$tokens=$null;$errors=$null;"
            f"[Management.Automation.Language.Parser]::ParseFile('{escaped}',"
            "[ref]$tokens,[ref]$errors)|Out-Null;"
            "if(@($errors).Count -ne 0){$errors|ForEach-Object{$_.Message};exit 2};exit 0"
        )
        syntax = subprocess.run([exe, "-NoProfile", "-NonInteractive",
                                 "-Command", parser],
                                capture_output=True, text=True, timeout=30)
        self.assertEqual(syntax.returncode, 0, syntax.stdout + syntax.stderr)
        w21_escaped = str(W21).replace("'", "''")
        w21_syntax = subprocess.run(
            [exe, "-NoProfile", "-NonInteractive", "-Command",
             "$tokens=$null;$errors=$null;"
             f"[Management.Automation.Language.Parser]::ParseFile('{w21_escaped}',"
             "[ref]$tokens,[ref]$errors)|Out-Null;"
             "if(@($errors).Count -ne 0){$errors|ForEach-Object{$_.Message};exit 2};exit 0"],
            capture_output=True, text=True, timeout=30,
        )
        self.assertEqual(w21_syntax.returncode, 0,
                         w21_syntax.stdout + w21_syntax.stderr)
        cmd = [exe, "-NoProfile", "-NonInteractive"]
        if os.name == "nt":
            cmd.extend(["-ExecutionPolicy", "Bypass"])
        cmd.extend(["-File", str(PROBE)])
        safe = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        self.assertEqual(safe.returncode, 0, safe.stdout + safe.stderr)
        obj = json.loads(safe.stdout)
        self.assertEqual(obj["status"], "UCIE_W25_CONTRACT_ONLY_NO_HOST_ACCESS")
        self.assertFalse(obj["owner_tasks_queried"])
        self.assertFalse(obj["journal_written"])
        denied = subprocess.run(cmd + ["-CheckLocal"], capture_output=True,
                                text=True, timeout=30)
        self.assertNotEqual(denied.returncode, 0)
        self.assertIn("UCIE_W25_EXPLICIT_READONLY_OWNER_APPROVAL_REQUIRED",
                      denied.stdout + denied.stderr)


if __name__ == "__main__":
    unittest.main()
