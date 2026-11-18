"""W21 owner-only W19+W20 maintenance orchestration, no-host regressions.

Runs parser, contract-only and approval-denied modes in ephemeral CI. It does
NOT start owner Windows tasks, access SQLite, C40, or local bridge credentials.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "ucie_owner_w21_single_local_maintenance_v01.ps1"


class W21OwnerMaintenanceContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.src = SCRIPT.read_text("utf-8")

    def test_only_three_ucie_actions_and_c40_readonly(self):
        text = self.src
        self.assertEqual(text.count("Name='UCIE-"), 3)
        for name in (
            "UCIE-PublicMiner-Hourly", "UCIE-Internal-Minute",
            "UCIE-LocalV1-Web", "UCIE-C40-Recover",
        ):
            self.assertIn(name, text)
        self.assertIn("$old='D:\\UCIE'", text)
        self.assertIn("$root='D:\\UCIE_PROJECT\\UCIE'", text)
        self.assertIn("C40Hash", text)
        self.assertIn("UCIE_W21_C40_ACTION_DRIFT_AFTER_W19", text)
        self.assertIn("UCIE_W21_C40_ACTION_DRIFT_AFTER_W20", text)
        self.assertNotIn("Set-ScheduledTask", text)
        self.assertNotIn("Enable-ScheduledTask", text)
        self.assertNotIn("Disable-ScheduledTask", text)
        self.assertNotIn("Start-ScheduledTask", text)
        self.assertNotIn("Stop-ScheduledTask", text)

    def test_one_bounded_sequence_and_durable_intent(self):
        s = self.src
        before = s.index("SavePrivate $journal")
        w19 = s.index("& $w19 -Apply")
        w20 = s.index("& $w20 -PilotLocal")
        verified = s.index("NewLocalOnly", w20)
        self.assertLess(before, w19)
        self.assertLess(w19, w20)
        self.assertLess(w20, verified)
        self.assertIn("UCIE_W19_OWNER_DATA_TASK_STAGE_JOURNAL_V01.json", s)
        self.assertIn("UCIE_W20_LOCAL_PILOT_JOURNAL_V01.json", s)
        self.assertIn("UCIE_W21_LOCAL_MAINTENANCE_INTENT_V01.json", s)
        self.assertIn("UCIE_W21_LOCAL_ONCE_FAILED_PRESERVE_RECEIPTS", s)
        self.assertIn("UCIE_W21_LOCAL_ONLY_HEALTHY__WRITERS_AND_C40_HOLD", s)
        self.assertIn("UCIE_W21_TWO_WRITER_TASKS_NOT_DISABLED", s)
        self.assertIn("writer_tasks_enabled=0", s)

    def test_rollback_prioritizes_partial_w20_then_exact_w19(self):
        s = self.src
        self.assertLess(s.index("if (Test-Path -LiteralPath $w20Journal)"),
                        s.index("elseif (Test-Path -LiteralPath $w13Journal)"))
        self.assertIn("& $w20 -RollbackLocal -OwnerApproval $w20RollbackApproval", s)
        self.assertIn("& $w19 -Rollback -OwnerApproval $w19RollbackApproval", s)
        self.assertIn("UCIE_W21_PRE_REBIND_PARTIAL_DATA_HOLD", s)
        self.assertIn("new_private_sqlite_kept=$true", s)
        self.assertIn("original_sqlite_overwritten=$false", s)
        self.assertNotIn("Remove-Item -LiteralPath $old", s)
        self.assertNotIn("git clean", s)
        self.assertNotIn("git reset", s)
        self.assertNotIn("git pull", s)
        self.assertNotIn("Restart-Service", s)
        self.assertNotIn("Stop-Process", s)

    def test_default_no_host_check_precedes_other_operations(self):
        s = self.src
        self.assertLess(s.index("if ($ContractOnly) {"),
                        s.index("Import-Module ScheduledTasks"))
        self.assertLess(s.index("UCIE_W21_EXPLICIT_OWNER_MAINTENANCE_APPROVAL_REQUIRED"),
                        s.index("Import-Module ScheduledTasks"))
        self.assertIn("UCIE_W21_CONTRACT_ONLY_NO_HOST_ACCESS", s)
        self.assertIn("owner_sqlite_opened=$false", s)
        self.assertIn("c40_task_queried=$false", s)
        self.assertIn("full_live_cutover_authorized=$false", s)
        self.assertIn("c40_mcp_round_trip_verified=$false", s)

    def test_health_is_exact_loopback_not_tunnel_assertion(self):
        s = self.src
        self.assertIn("http://127.0.0.1:18767/local/health", s)
        self.assertIn("UCIE_OWNER_LOCAL_FOUR_PILLAR_APP_V01", s)
        self.assertIn("LOCAL_V1_OWNER_ACCEPTED_LOCAL_GO_NO_ONLINE_RELEASE", s)
        self.assertIn("$p.online_release_authorized -eq $false", s)
        self.assertIn("$p.operating_database_writes -eq 0", s)
        self.assertIn("c40_mcp_round_trip_verified=$false", s)
        self.assertNotIn("c40_mcp_round_trip_verified=$true", s)

    def test_native_powershell_parser_contract_and_denials(self):
        ps = "powershell.exe" if os.name == "nt" else shutil.which("pwsh")
        if not ps:
            self.skipTest("PowerShell absent")
        quoted = str(SCRIPT).replace("'", "''")
        parser = (
            "$tokens=$null;$errors=$null;"
            f"[System.Management.Automation.Language.Parser]::ParseFile('{quoted}',"
            "[ref]$tokens,[ref]$errors)|Out-Null;"
            "if(@($errors).Count -ne 0){$errors|ForEach-Object{$_.Message};exit 2};exit 0"
        )
        p = subprocess.run([ps, "-NoProfile", "-NonInteractive", "-Command", parser],
                           capture_output=True, text=True, timeout=25)
        self.assertEqual(p.returncode, 0, p.stderr + p.stdout)
        cmd = [ps, "-NoProfile", "-NonInteractive"]
        if os.name == "nt":
            cmd += ["-ExecutionPolicy", "Bypass"]
        cmd += ["-File", str(SCRIPT)]
        safe = subprocess.run(cmd, capture_output=True, text=True, timeout=25)
        self.assertEqual(safe.returncode, 0, safe.stderr + safe.stdout)
        payload = json.loads(safe.stdout)
        self.assertEqual(payload["status"], "UCIE_W21_CONTRACT_ONLY_NO_HOST_ACCESS")
        self.assertEqual(payload["writer_tasks_enabled"], 0)
        self.assertFalse(payload["c40_task_queried"])
        for action in ("-ApplyLocal", "-RollbackLocal"):
            with self.subTest(action=action):
                denied = subprocess.run(cmd + [action],
                                        capture_output=True, text=True, timeout=25)
                self.assertNotEqual(denied.returncode, 0)
                self.assertIn("UCIE_W21_EXPLICIT_OWNER_MAINTENANCE_APPROVAL_REQUIRED",
                              denied.stdout + denied.stderr)


if __name__ == "__main__":
    unittest.main()
