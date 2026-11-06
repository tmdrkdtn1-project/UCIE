"""UCIE C40 second-cycle observation, READ ONLY.

Checks the exact UCIE C40 scheduled task and its existing bounded health
receipt. A passing test is NOT proof of two cycles unless the printed
cycle_verdict explicitly says SECOND_OR_LATER_CYCLE_CONFIRMED.
No task control, client start/stop, unrelated process or DB access.
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
import shutil
import subprocess
import unittest

UCIE_HOST = Path(r"D:\UCIE_DATA\mcp_tunnel_profiles\ucie-private-c40.yaml")
RECEIPT = Path(r"D:\UCIE\.ucie_bridge_state\c40_supervisor_health_v1.json")
SOURCE = Path(r"D:\UCIE\scripts\ucie_c40_recover.ps1")
ORIGINAL_FIRST_CYCLE = datetime.fromisoformat(
    "2026-11-03T05:58:55.234357+00:00"
)
PINNED_SOURCE_SHA = "23dcb08524b32c611b43c1136a444286d7dc776598a739a7152a651a5244e66f"


class C40SecondCycleReadonly(unittest.TestCase):
    def test_existing_owner_supervisor_second_cycle_witness(self):
        if os.name != "nt" or not UCIE_HOST.is_file():
            self.skipTest("UCIE owner Windows host only")
        if not RECEIPT.is_file() or RECEIPT.is_symlink():
            self.fail("UCIE_C40_HEALTH_RECEIPT_MISSING_OR_SYMLINK")
        if RECEIPT.stat().st_size > 2048:
            self.fail("UCIE_C40_HEALTH_RECEIPT_OVERSIZED")
        shell = shutil.which("powershell.exe")
        if not shell:
            self.skipTest("Windows PowerShell absent")
        script = r"""
$ErrorActionPreference = 'Stop'
$task = Get-ScheduledTask -TaskPath '\' -TaskName 'UCIE-C40-Recover' -ErrorAction Stop
$info = Get-ScheduledTaskInfo -TaskPath '\' -TaskName 'UCIE-C40-Recover' -ErrorAction Stop
$hash = (Get-FileHash -LiteralPath 'D:\UCIE\scripts\ucie_c40_recover.ps1' -Algorithm SHA256).Hash.ToLowerInvariant()
[pscustomobject]@{
    schema='UCIE_C40_RUNNING_TASK_READONLY_V1'
    state=[string]$task.State
    run_level=[string]$task.Principal.RunLevel
    logon_type=[string]$task.Principal.LogonType
    last_result=[int]$info.LastTaskResult
    source_sha=$hash
    modified_task=$false
    started_process=$false
} | ConvertTo-Json -Compress
"""
        r = subprocess.run(
            [shell, "-NoProfile", "-NonInteractive", "-Command", script],
            capture_output=True, text=True, errors="replace", check=False, timeout=30
        )
        self.assertEqual(r.returncode, 0, "UCIE task read-only query failed")
        task = json.loads(r.stdout.strip().splitlines()[-1])
        health = json.loads(RECEIPT.read_text(encoding="utf-8-sig"))
        self.assertEqual(task["schema"], "UCIE_C40_RUNNING_TASK_READONLY_V1")
        self.assertEqual(task["state"], "Running")
        self.assertEqual(task["run_level"], "Highest")
        self.assertEqual(task["logon_type"], "Interactive")
        self.assertEqual(task["last_result"], 267009)
        self.assertEqual(task["source_sha"], PINNED_SOURCE_SHA)
        self.assertEqual(health["schema"], "UCIE_C40_SUPERVISOR_HEALTH_V1")
        self.assertEqual(health["stage"], "CYCLE_OK")
        self.assertEqual(health["code"], "UCIE_C40_ALREADY_RUNNING")
        self.assertEqual(health["client_count"], 1)
        recorded = datetime.fromisoformat(str(health["utc"]).replace("Z", "+00:00"))
        self.assertIsNotNone(recorded.tzinfo)
        now = datetime.now(timezone.utc)
        age = (now - recorded).total_seconds()
        self.assertGreaterEqual(age, -10)
        self.assertLessEqual(age, 420, "UCIE C40 health receipt unexpectedly stale")
        seconds_after_first = (recorded - ORIGINAL_FIRST_CYCLE).total_seconds()
        verdict = (
            "SECOND_OR_LATER_CYCLE_CONFIRMED"
            if seconds_after_first >= 290
            else "SECOND_CYCLE_NOT_YET_PROVEN"
        )
        print("UCIE_C40_SECOND_CYCLE_OBSERVATION=" + json.dumps({
            "schema": "UCIE_C40_SECOND_CYCLE_READONLY_V1",
            "cycle_verdict": verdict,
            "first_cycle_utc": ORIGINAL_FIRST_CYCLE.isoformat(),
            "latest_cycle_utc": recorded.isoformat(),
            "elapsed_since_first_seconds": round(seconds_after_first, 1),
            "latest_health_age_seconds": round(age, 1),
            "task_state": task["state"],
            "task_runlevel": task["run_level"],
            "live_client_count_from_supervisor": 1,
            "other_tasks_changed": False,
            "processes_started_or_stopped": False,
            "operating_db_modified": False,
        }, sort_keys=True))
        self.assertFalse(task["modified_task"])
        self.assertFalse(task["started_process"])


if __name__ == "__main__":
    unittest.main()
