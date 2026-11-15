"""UCIE only: 10-minute public-miner source contract and owner preview.

No TaskScheduler mutations in this unittest: even on owner Windows, invoke
only the updater without -Apply, and verify its read-only result.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess
import unittest
from datetime import timedelta

from ucie_miner import schedule_policy

ROOT = Path(__file__).resolve().parents[1]


class PublicMiner10MinuteCadenceTests(unittest.TestCase):
    def test_01_policy_is_ten_minutes_and_bounded_retry_remains(self):
        self.assertEqual(schedule_policy.INTERVAL, timedelta(minutes=10))
        self.assertEqual(schedule_policy.MAX_FAILURES, 6)
        self.assertEqual(schedule_policy.SUCCESS_TRIGGER_JITTER,
                         timedelta(seconds=30))
        self.assertEqual(schedule_policy.FAILURE_TRIGGER_JITTER,
                         timedelta(seconds=15))

    def test_02_installer_status_and_owner_updater_agree(self):
        installer = (ROOT / "scripts" / "install_hourly_task.ps1").read_text(
            encoding="utf-8-sig")
        observer = (ROOT / "scripts" / "task_status.ps1").read_text(
            encoding="utf-8-sig")
        updater = (ROOT / "scripts" / "set_public_miner_10min.ps1").read_text(
            encoding="utf-8-sig")
        self.assertIn("-RepetitionInterval (New-TimeSpan -Minutes 10)",
                      installer)
        self.assertIn("$intervals[0] -eq 'PT10M'", observer)
        self.assertIn("$gapMinutes -ge 8 -and $gapMinutes -le 12", observer)
        self.assertIn("cadence_minutes = 10", observer)
        self.assertIn("UCIE-PublicMiner-Hourly", updater)
        self.assertIn("param([switch]$Apply)", updater)
        self.assertIn("Set-ScheduledTask -TaskPath $taskPath -TaskName $taskName",
                      updater)
        self.assertIn("if (-not $Apply)", updater)
        self.assertIn("EXACT_UCIE_CURRENT_OWNER_SID_REQUIRED", updater)
        self.assertIn("EXACT_UCIE_TASK_ACTION_PRINCIPAL_SETTINGS_MISMATCH_NO_GO",
                      updater)
        self.assertIn("UCIE_TASK_MUST_BE_READY", updater)
        self.assertNotIn("Start-ScheduledTask -TaskPath", updater)
        self.assertNotIn("Unregister-ScheduledTask -TaskPath", updater)
        self.assertNotIn("Stop-ScheduledTask -TaskPath", updater)

    @unittest.skipUnless(os.name == "nt" and shutil.which("powershell.exe"),
                         "Owner Windows PowerShell only")
    def test_03_owner_task_read_only_preview(self):
        if (ROOT.resolve() != Path("D:/UCIE").resolve()
                or ROOT.is_symlink() or not (ROOT / ".git").is_dir()):
            self.skipTest("exact UCIE owner checkout unavailable")
        path = ROOT / "scripts" / "set_public_miner_10min.ps1"
        self.assertTrue(path.is_file() and not path.is_symlink())
        result = subprocess.run(
            ["powershell.exe", "-NoProfile", "-NonInteractive",
             "-File", str(path)],
            cwd=str(ROOT), timeout=30, capture_output=True, check=False,
            env={"SystemRoot": os.environ.get("SystemRoot", "C:\\Windows"),
                 "PATH": os.environ.get("PATH", "")},
        )
        self.assertEqual(result.returncode, 0, result.stderr.decode(
            "utf-8", "replace")[:600])
        self.assertLess(len(result.stdout), 2500)
        info = json.loads(result.stdout.decode("utf-8-sig"))
        self.assertEqual(info["schema"],
                         "UCIE_PUBLIC_MINER_10MIN_OWNER_CADENCE_V1")
        self.assertEqual(info["status"], "PREVIEW_ONLY_NO_TASK_CHANGES")
        self.assertIn(info["existing_interval"], ("PT1H", "PT10M"))
        self.assertEqual(info["requested_interval"], "PT10M")
        self.assertTrue(info["exact_task_action_and_owner_verified"])
        self.assertFalse(info["scheduler_changed"])
        self.assertFalse(info["collection_run_requested"])
        self.assertFalse(info["queue_or_database_modified"])
        self.assertFalse(info["production_approved"])
        print("UCIE_10MIN_OWNER_PREVIEW=" + json.dumps(
            info, sort_keys=True, ensure_ascii=True))


if __name__ == "__main__":
    unittest.main()
