"""Owner-only UCIE TaskScheduler exact-task event triage read-only acceptance.

The exact UCIE-only source script is fixed, with no parameters.
No impersonation, no task/service/DB change, no event message/user IDs.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess
import unittest


class UcieExactEventTriageTests(unittest.TestCase):
    def test_owner_only_sanitized_events_for_exact_public_miner_task(self):
        root = Path(__file__).resolve().parents[1]
        if (os.name != "nt" or root.is_symlink()
                or root.resolve() != Path("D:/UCIE").resolve()):
            self.skipTest("OWNER_D_UCIE_WINDOWS_ONLY")
        command = shutil.which("powershell.exe")
        if command is None:
            self.skipTest("POWERSHELL_NOT_AVAILABLE")
        script = root / "scripts" / "ucie_public_miner_task_event_triage_v01.ps1"
        self.assertTrue(script.is_file() and not script.is_symlink())
        result = subprocess.run(
            [command, "-NoProfile", "-NonInteractive", "-File", str(script)],
            capture_output=True, text=True, timeout=30, check=False)
        self.assertEqual(result.returncode, 0,
                         "UCIE_EXACT_TASK_EVENT_READ_FAILED_NO_GO")
        data = json.loads(result.stdout.strip())
        self.assertEqual(data["schema"],
                         "UCIE_EXACT_PUBLIC_MINER_TASK_EVENT_TRIAGE_V01")
        self.assertIn(data["status"], (
            "EXACT_UCIE_TASK_EVENT_ROWS_OBSERVED_NOT_CYCLE_PROOF",
            "UCIE_EXACT_TASK_EVENTS_NOT_AVAILABLE_NO_GO",
            "UCIE_PUBLIC_MINER_TASK_MISSING_NO_GO"))
        self.assertFalse(data["event_proof_for_two_cycles"])
        self.assertFalse(data["task_changed"])
        if data["status"] != "UCIE_PUBLIC_MINER_TASK_MISSING_NO_GO":
            self.assertFalse(data["other_task_events_requested"])
            self.assertFalse(data["event_payload_or_user_id_returned"])
            self.assertEqual(data["operating_db_writes"], 0)
            self.assertEqual(data["public_network_requests"], 0)
        rows = data.get("event_rows", [])
        self.assertLessEqual(len(rows), 24)
        for row in rows:
            self.assertEqual(
                set(row), {"event_id", "event_utc", "result_code_if_present"})
            self.assertIsInstance(row["event_id"], int)
        safe = {
            "status": data["status"],
            "events_readable": data["events_readable"],
            "record_count": data["record_count"],
            "event_ids": data["event_ids"],
            "latest_events": rows[:12],
            "observed_termination_event_111":
                data.get("observed_termination_event_111"),
            "observed_action_completed_event_201":
                data.get("observed_action_completed_event_201"),
            "observed_task_completed_event_102":
                data.get("observed_task_completed_event_102"),
            "execution_time_limit": data.get("execution_time_limit"),
            "stop_if_going_on_batteries":
                data.get("stop_if_going_on_batteries"),
            "disallow_start_if_on_batteries":
                data.get("disallow_start_if_on_batteries"),
            "task_state": data.get("task_state"),
            "task_changed": False,
        }
        print("UCIE_EXACT_TASK_EVENT_TRIAGE_LIVE_V01="
              + json.dumps(safe, ensure_ascii=True, sort_keys=True))


if __name__ == "__main__":
    unittest.main()
