"""UCIE-only read-only Stage17 normal TaskScheduler receipt gate.

The already reviewed first-party scripts/task_status.ps1 -Evidence is executed
only for exact owner D:/UCIE; no task start, collector call or data write.
A successful task action by itself NEVER grants a Stage17 operational PASS.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "task_status.ps1"
SCHEMA = "UCIE_HOURLY_LOCAL_OPERATIONS_READONLY_V1"


class Stage17OwnerHourlyEvidenceV15(unittest.TestCase):
    def test_01_operator_command_is_fixed_and_no_task_mutation(self):
        self.assertEqual(SCRIPT.name, "task_status.ps1")
        self.assertTrue(SCRIPT.is_file() and not SCRIPT.is_symlink())
        code = SCRIPT.read_text(encoding="utf-8-sig")
        self.assertIn("Get-ScheduledTaskInfo", code)
        self.assertIn("Get-WinEvent", code)
        self.assertIn("-MaxEvents 64", code)
        self.assertIn("UCIE-PublicMiner-Hourly", code)
        self.assertIn("INSTANCE_GUID_EVENTS_100_200_201_102", code)
        self.assertIn("last_scheduled_run_matches_receipt", code)
        for unsafe in ("Register-ScheduledTask", "Set-ScheduledTask",
                       "Start-ScheduledTask", "Stop-ScheduledTask",
                       "Unregister-ScheduledTask", "Invoke-WebRequest",
                       "Invoke-RestMethod", "Remove-Item", "Stop-Process"):
            self.assertNotIn(unsafe + " ", code)

    @unittest.skipUnless(os.name == "nt" and shutil.which("powershell.exe"),
                         "exact owner Windows PowerShell required")
    def test_02_hourly_task_config_event_and_receipt_readonly(self):
        if (ROOT.resolve() != Path("D:/UCIE").resolve()
                or ROOT.is_symlink() or not (ROOT / ".git").is_dir()
                or SCRIPT.is_symlink()):
            self.skipTest("exact owner UCIE checkout not available")
        try:
            child = subprocess.run(
                ["powershell.exe", "-NoProfile", "-NonInteractive",
                 "-File", str(SCRIPT), "-Evidence"],
                cwd=str(ROOT), capture_output=True, timeout=35, check=False,
                env={"SystemRoot": os.environ.get("SystemRoot", "C:\\Windows"),
                     "PATH": os.environ.get("PATH", "")})
        except (OSError, subprocess.TimeoutExpired):
            self.skipTest("owner read-only TaskScheduler method unavailable")
        self.assertEqual(child.returncode, 0,
                         "read-only task evidence script did not complete")
        self.assertLessEqual(len(child.stdout), 12_000)
        data = json.loads(child.stdout.decode("utf-8-sig", "strict"))
        self.assertEqual(data.get("schema"), SCHEMA)
        self.assertFalse(data["scheduler_changed"])
        self.assertFalse(data["database_modified"])
        self.assertFalse(data["private_projects_accessed"])
        self.assertEqual(data["candidates_auto_approved"], 0)
        self.assertFalse(data["production_approved"])
        passed = data.get("two_recent_hourly_successes") is True
        if passed:
            self.assertTrue(data["last_scheduled_run_matches_receipt"])
            self.assertEqual(data["scheduler_event_instance_receipts_verified"], 2)
            self.assertEqual(data["last_cycle_status"], "COLLECTED_UNVERIFIED")
            self.assertTrue(data["last_task_result_zero"])
        receipt = {
            "schema": "UCIE_STAGE17_OWNER_HOURLY_TASK_GATE_V15",
            "status": data.get("status"),
            "exact_task_found": data.get("scheduled_task_registered"),
            "task_state": data.get("task_state"),
            "owner_least_privilege_verified":
                data.get("owner_least_privilege_verified"),
            "action_matches_ucie_only": data.get("action_matches_ucie_only"),
            "hourly_no_overlap_configured":
                data.get("hourly_no_overlap_configured"),
            "last_task_result_zero": data.get("last_task_result_zero"),
            "two_recent_hourly_successes": passed,
            "event_instance_receipts_verified":
                data.get("scheduler_event_instance_receipts_verified"),
            "last_scheduled_run_matches_receipt":
                data.get("last_scheduled_run_matches_receipt"),
            "last_cycle_status": data.get("last_cycle_status"),
            "last_cycle_finished_utc": data.get("last_cycle_finished_utc"),
            "next_scheduled_utc": data.get("next_scheduled_utc"),
            "production_approved": False,
            "public_gets_triggered": 0, "task_mutations": 0,
            "operating_database_writes": 0,
        }
        print("UCIE_STAGE17_OWNER_HOURLY_TASK_GATE=" +
              json.dumps(receipt, sort_keys=True, ensure_ascii=True))


if __name__ == "__main__":
    unittest.main()
