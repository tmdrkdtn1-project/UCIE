"""Owner-only exact UCIE scheduled action vs receipt lifetime witness.

Queries UCIE-PublicMiner-Hourly and last two public receipts, through the
fixed fail-closed read-only PowerShell script. No tasks or DB are changed.
Ordinary GitHub Actions checkout SKIP this owner-local probe.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess
import unittest


class UcieOwnerPostReceiptExitTimelineTests(unittest.TestCase):
    def test_exact_task_instance_action_exit_lag(self):
        root = Path(__file__).resolve().parents[1]
        if (os.name != "nt" or root.is_symlink()
                or root.resolve() != Path("D:/UCIE").resolve()):
            self.skipTest("OWNER_D_UCIE_WINDOWS_ONLY")
        executable = shutil.which("powershell.exe")
        if executable is None:
            self.skipTest("POWERSHELL_NOT_AVAILABLE_NO_ATTESTATION")
        script = root / "scripts" / "ucie_public_miner_exit_timeline_v01.ps1"
        self.assertTrue(script.is_file() and not script.is_symlink())
        run = subprocess.run(
            [executable, "-NoProfile", "-NonInteractive", "-File", str(script)],
            capture_output=True, text=True, timeout=35, check=False)
        self.assertEqual(run.returncode, 0,
                         "EXACT_UCIE_TASK_TIMELINE_NO_GO_NOT_ATTRIBUTABLE")
        report = json.loads(run.stdout.strip())
        self.assertEqual(report["schema"],
                         "UCIE_PUBLIC_MINER_POST_RECEIPT_EXIT_TIMELINE_V01")
        self.assertIn(report["status"], (
            "EXACT_TASK_ACTION_NONZERO_AFTER_RECEIPT_NO_GO",
            "EXACT_TASK_ZERO_EXIT_AFTER_RECEIPT_OBSERVED_NOT_SCHEDULER_GO",
            "EXACT_TASK_POST_RECEIPT_EXIT_NOT_PROVEN_NO_GO"))
        self.assertEqual(report["matched_receipt_count"], 2)
        self.assertEqual(report["required_receipts"], 2)
        self.assertFalse(report["exact_windows_task_healthy_attested"])
        self.assertFalse(report["production_termination_root_cause_proven"])
        self.assertFalse(report["termination_at_task_time_limit_confirmed"])
        self.assertFalse(report["task_scheduler_mutated"])
        self.assertEqual(report["operating_database_writes"], 0)
        self.assertEqual(report["public_network_requests"], 0)
        self.assertFalse(report["other_project_access"])
        self.assertFalse(report["event_instance_guid_disclosed"])
        clean = {
            "status": report["status"],
            "matched_receipts": report["matched_receipt_count"],
            "nonzero_actions": report["observed_nonzero_action_events"],
            "action_result_codes": [r["action_result_hex"]
                                    for r in report["receipts"]],
            "post_receipt_lag_seconds": [
                r["post_receipt_exit_lag_seconds"]
                for r in report["receipts"]],
            "action_elapsed_seconds": [
                r["action_elapsed_seconds"]
                for r in report["receipts"]],
            "scheduler_proof": False,
            "production_cause_proven": False,
            "task_mutated": False,
        }
        print("UCIE_OWNER_EXACT_TASK_POST_RECEIPT_EXIT_TIMELINE_V01="
              + json.dumps(clean, sort_keys=True, ensure_ascii=True))


if __name__ == "__main__":
    unittest.main()
