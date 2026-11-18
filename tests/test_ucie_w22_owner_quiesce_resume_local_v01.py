"""W22 restricted owner-maintenance contract tests.

Runs ONLY native PowerShell contract/no-approval paths on disposable CI.
Any owner maintenance, Task Scheduler changes, Live SQLite reads, C40/tunnel
roundtrips, 18767 port stop/start and real recovery remain NOT EXECUTED.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "ucie_owner_w22_quiesce_resume_local_v01.ps1"


class W22OwnerQuiescenceContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.src = SCRIPT.read_text("utf-8")

    def test_exact_owner_task_scope_no_process_kills(self):
        code = self.src
        self.assertEqual(code.count("Name=$names["), 3)
        for name in ("UCIE-PublicMiner-Hourly", "UCIE-Internal-Minute",
                     "UCIE-LocalV1-Web", "UCIE-C40-Recover"):
            self.assertIn(name, code)
        self.assertIn("$root='D:\\UCIE_PROJECT\\UCIE'", code)
        self.assertIn("$old='D:\\UCIE'", code)
        self.assertIn("OwnerTask", code)
        self.assertIn("UCIE_W22_TASK_OWNER_MISMATCH", code)
        self.assertIn("UCIE_W22_ORIGINAL_TASK_ACTION_DRIFT_HOLD", code)
        self.assertIn("Stop-ScheduledTask -TaskPath '\\' -TaskName $names[2]", code)
        self.assertIn("Disable-ScheduledTask -TaskPath '\\' -TaskName $names[$i]", code)
        self.assertNotIn("Stop-Process", code)
        self.assertNotIn("taskkill", code)
        self.assertNotIn("Restart-Service", code)
        self.assertNotIn("Set-ScheduledTask", code)
        self.assertNotIn("Remove-Item -LiteralPath $old", code)
        self.assertNotIn("git pull", code)
        self.assertNotIn("git clean", code)
        self.assertNotIn("git reset", code)

    def test_no_host_default_and_owner_approval_first(self):
        code = self.src
        self.assertLess(code.index("if ($ContractOnly) {"),
                        code.index("Import-Module ScheduledTasks"))
        self.assertLess(code.index("UCIE_W22_EXPLICIT_OWNER_APPROVAL_REQUIRED"),
                        code.index("Import-Module ScheduledTasks"))
        self.assertIn("UCIE_W22_CONTRACT_ONLY_NO_HOST_ACCESS", code)
        self.assertIn("owner_tasks_queried=$false", code)
        self.assertIn("port_probed=$false", code)
        self.assertIn("sqlite_opened=$false", code)
        self.assertIn("c40_queried=$false", code)

    def test_no_repeated_w16_backup_and_pre_outage_gates(self):
        code = self.src
        first_stop = code.index("Disable-ScheduledTask -TaskPath '\\' -TaskName $names[$i]")
        self.assertLess(code.index("SavePrivate $intent"), first_stop)
        self.assertLess(code.index("module._private_prerequisites()"), first_stop)
        self.assertLess(code.index("UCIE_W22_W19_PRIVATE_LINEAGE_GATE_HOLD_BEFORE_OUTAGE"),
                        first_stop)
        self.assertLess(code.index("Absent $p", code.index("if($ApplyLocal)")),
                        first_stop)
        self.assertIn("UCIE_W19_LOCKSTEP_FINAL_DATA_V01", code)
        self.assertIn("UCIE_W21_LOCAL_MAINTENANCE_INTENT_V01", code)
        self.assertIn("UCIE_W22_EXACT_ORIGINAL_STATES_REQUIRED", code)
        self.assertIn("UCIE_W22_ORIGINAL_LOCALV1_HEALTH_OR_PORT_HOLD", code)
        self.assertIn("UCIE_W22_C40_TASK_NOT_RUNNING_HOLD", code)

    def test_foreign_listener_after_only_old_task_stop_is_hold(self):
        code = self.src
        stop = code.index("Stop-ScheduledTask -TaskPath '\\' -TaskName $names[2]")
        port = code.index("UCIE_W22_LISTENER_NOT_RELEASED_BY_OLD_TASK_EXPLICIT_RESUME")
        w21 = code.index("& $w21 -ApplyLocal -OwnerApproval $w21Apply")
        self.assertLess(stop, port)
        self.assertLess(port, w21)
        self.assertIn("UCIE_W22_PORT_OCCUPIED_NO_BLIND_OLD_RESTART", code)
        self.assertIn("MULTIPLE_HOLD", code)
        self.assertIn("NON_LOOPBACK_HOLD", code)
        self.assertNotIn("Get-CimInstance Win32_Process", code)
        self.assertNotIn(".CommandLine", code)
        self.assertIn("c40_mcp_round_trip_verified=$false", code)
        self.assertIn("original_task_availability_automatically_restored=$false", code)

    def test_explicit_recovery_preserves_old_new_data_and_two_schedule_states(self):
        code = self.src
        self.assertIn("UCIE_W22_OWNER_MAINTENANCE_INTENT_V01.json", code)
        self.assertIn("UCIE_W22_ORIGINAL_AVAILABILITY_RESTORED_V01.json", code)
        self.assertIn("& $w21 -RollbackLocal -OwnerApproval $w21Rollback", code)
        self.assertIn("UCIE_W22_PARTIAL_STAGE_WITHOUT_W21_JOURNAL_MANUAL_HOLD", code)
        self.assertIn("UCIE_W22_OLD_LOCALV1_RESUME_FAILED_MANUAL_HOLD", code)
        self.assertIn("Enable-ScheduledTask -TaskPath '\\' -TaskName $names[2]", code)
        self.assertIn("Start-ScheduledTask -TaskPath '\\' -TaskName $names[2]", code)
        self.assertIn("Enable-ScheduledTask -TaskPath '\\' -TaskName $names[$i]", code)
        self.assertIn("original_sqlite_restored_or_overwritten=$false", code)
        self.assertIn("new_private_sqlite_copies_preserved=$true", code)
        self.assertIn("listener_task_pid_identity_verified=$false", code)
        self.assertIn("full_cutover_authorized=$false", code)

    def test_powershell_parser_default_and_unapproved_modes(self):
        exe = "powershell.exe" if os.name == "nt" else shutil.which("pwsh")
        if not exe:
            self.skipTest("PowerShell not available")
        escaped = str(SCRIPT).replace("'", "''")
        parser = (
            "$tokens=$null;$errors=$null;"
            f"[Management.Automation.Language.Parser]::ParseFile('{escaped}',"
            "[ref]$tokens,[ref]$errors)|Out-Null;"
            "if(@($errors).Count -ne 0){$errors|ForEach-Object{$_.Message};exit 2};exit 0"
        )
        syntax = subprocess.run([exe, "-NoProfile", "-NonInteractive",
                                 "-Command", parser], capture_output=True,
                                text=True, timeout=30, check=False)
        self.assertEqual(syntax.returncode, 0, syntax.stdout + syntax.stderr)
        command = [exe, "-NoProfile", "-NonInteractive"]
        if os.name == "nt":
            command.extend(["-ExecutionPolicy", "Bypass"])
        command.extend(["-File", str(SCRIPT)])
        default = subprocess.run(command, capture_output=True, text=True,
                                 timeout=30, check=False)
        self.assertEqual(default.returncode, 0, default.stdout + default.stderr)
        receipt = json.loads(default.stdout.strip())
        self.assertEqual(receipt["status"], "UCIE_W22_CONTRACT_ONLY_NO_HOST_ACCESS")
        self.assertFalse(receipt["owner_tasks_queried"])
        self.assertFalse(receipt["task_stopped_or_enabled"])
        for mode in ("-ApplyLocal", "-ResumeOld"):
            with self.subTest(mode=mode):
                denied = subprocess.run(command + [mode],
                                        capture_output=True, text=True,
                                        timeout=30, check=False)
                self.assertNotEqual(denied.returncode, 0)
                self.assertIn("UCIE_W22_EXPLICIT_OWNER_APPROVAL_REQUIRED",
                              denied.stdout + denied.stderr)


if __name__ == "__main__":
    unittest.main()
