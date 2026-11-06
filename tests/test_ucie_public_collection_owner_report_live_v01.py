"""Exact owner UCIE public counts + scheduler unified read-only report test.

Runs only the fixed UCIE report once (no arbitrary arguments), then verifies
aggregate-only status and truthfully retains TaskScheduler NO_GO.
No task execution, DB mutation, source collection, training or exports.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess
import unittest


class UcieOwnerPublicCollectionReportTests(unittest.TestCase):
    def test_combined_owner_public_inventory_and_scheduler_report(self):
        root = Path(__file__).resolve().parents[1]
        if (os.name != "nt" or root.is_symlink()
                or root.resolve() != Path("D:/UCIE").resolve()):
            self.skipTest("OWNER_D_UCIE_WINDOWS_ONLY")
        command = shutil.which("powershell.exe")
        if command is None:
            self.skipTest("POWERSHELL_NOT_AVAILABLE")
        script = root / "scripts" / "ucie_public_collection_report_v01.ps1"
        self.assertTrue(script.is_file() and not script.is_symlink())
        result = subprocess.run(
            [command, "-NoProfile", "-NonInteractive", "-File", str(script)],
            capture_output=True, text=True, timeout=35, check=False)
        self.assertEqual(result.returncode, 0,
                         "UCIE_COMBINED_OWNER_REPORT_UNAVAILABLE_NO_GO")
        report = json.loads(result.stdout.strip())
        self.assertEqual(report["schema"],
                         "UCIE_PUBLIC_COLLECTION_OWNER_REPORT_V01")
        self.assertEqual(report["counts"]["schema"],
                         "UCIE_PUBLIC_COLLECTION_INVENTORY_READONLY_V01")
        task = report["task_scheduler"]
        self.assertTrue(task["diagnostic_validated"])
        self.assertIn(task["last_task_result_interpretation"], (
            "LAST_TASK_RESULT_ZERO", "SCHED_S_TASK_RUNNING",
            "SCHED_S_TASK_TERMINATED",
            "NONZERO_RESULT_UNKNOWN_EXACT_CODE_REQUIRED",
            "SCHED_S_TASK_READY", "SCHED_S_TASK_DISABLED",
            "SCHED_S_TASK_HAS_NOT_RUN", "SCHED_S_TASK_NO_MORE_RUNS",
            "SCHED_S_TASK_NOT_SCHEDULED",
            "SCHED_S_TASK_NO_VALID_TRIGGERS",
            "SCHED_E_USER_NOT_LOGGED_ON", "SCHED_E_SERVICE_TOO_BUSY"))
        self.assertEqual(report["operating_database_writes"], 0)
        self.assertFalse(report["scheduled_tasks_changed"])
        self.assertFalse(report["other_project_access"])
        self.assertEqual(report["public_network_requests"], 0)
        self.assertEqual(report["auto_approved_rules"], 0)
        if not task["exact_task_event_proof_verified"]:
            self.assertIn("NO_GO", report["status"])
        clean = {
            "report_status": report["status"],
            "counts": {
                "legacy_candidates":
                    report["counts"]["legacy_miner"]["candidates"],
                "legacy_runs": report["counts"]["legacy_miner"]["runs"],
                "stage10_pr_revisions":
                    report["counts"]["stage10_public_candidate_staging"][
                        "candidate_revisions"],
                "stage12_review":
                    report["counts"]["stage12_unverified_review"][
                        "review_proposals"],
            },
            "task": {
                "state": task["task_state"],
                "last_result_decimal": task["last_task_result_decimal"],
                "last_result_hex": task["last_task_result_hex"],
                "meaning": task["last_task_result_interpretation"],
                "matched_events": task["event_receipts_verified"],
                "blockers": task["blocker_codes"],
            },
        }
        print("UCIE_OWNER_COLLECTION_AND_SCHEDULER_REPORT_V01="
              + json.dumps(clean, ensure_ascii=True, sort_keys=True))


if __name__ == "__main__":
    unittest.main()
