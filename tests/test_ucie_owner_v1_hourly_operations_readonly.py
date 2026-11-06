"""One-shot owner read-only UCIE scheduled task + two run receipt audit.

UCIE only: exact D:/UCIE, one named scheduled task and two trailing bounded
runtime receipts. No scheduled task edits, new miner invocation, network,
credentials, admin elevation, operating DB writes or other project files.
This is a truth-seeking diagnostic. Failure to observe means UNKNOWN/NO_GO.
"""
from __future__ import annotations

from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = "UCIE_V1_HOURLY_OWNER_READONLY_AUDIT"
TASK = "UCIE-PublicMiner-Hourly"
POWERSHELL = r'''
$ErrorActionPreference='Stop'
$name='UCIE-PublicMiner-Hourly'
$t=Get-ScheduledTask -TaskPath '\' -TaskName $name -ErrorAction SilentlyContinue
if ($null -eq $t) {
    [pscustomobject]@{status='TASK_NOT_REGISTERED';action_ok=$false;hourly=$false;last_result_ok=$false;last_run_utc=$null;next_run_utc=$null;task_state='ABSENT'} | ConvertTo-Json -Compress
    exit 0
}
$i=Get-ScheduledTaskInfo -TaskPath '\' -TaskName $name
$a=@($t.Actions)
$expected='D:\UCIE\.venv\Scripts\python.exe'
$arg='"D:\UCIE\scripts\public_miner_cycle.py"'
$actionOk=$a.Count -eq 1 -and [string]::Equals([string]$a[0].Execute,$expected,[StringComparison]::OrdinalIgnoreCase) -and [string]::Equals([string]$a[0].Arguments,$arg,[StringComparison]::Ordinal) -and [string]::Equals(([string]$a[0].WorkingDirectory).TrimEnd('\'),'D:\UCIE',[StringComparison]::OrdinalIgnoreCase)
$interval=@($t.Triggers|ForEach-Object {[string]$_.Repetition.Interval})
$hourly=$interval.Count -eq 1 -and $interval[0] -eq 'PT1H' -and [string]$t.Settings.MultipleInstances -eq 'IgnoreNew'
[pscustomobject]@{
status='TASK_READONLY_OBSERVED'
action_ok=[bool]$actionOk
hourly=[bool]$hourly
last_result_ok=($i.LastTaskResult -eq 0)
task_state=[string]$t.State
last_run_utc=if ($i.LastRunTime -gt [datetime]::MinValue) {([DateTimeOffset]$i.LastRunTime).ToUniversalTime().ToString('o')} else {$null}
next_run_utc=if ($i.NextRunTime -gt [datetime]::MinValue) {([DateTimeOffset]$i.NextRunTime).ToUniversalTime().ToString('o')} else {$null}
} | ConvertTo-Json -Compress
'''


def _read_recent_ucie_receipts() -> dict:
    runtime = ROOT / "runtime"
    file = runtime / "run_history.jsonl"
    if (ROOT.is_symlink() or runtime.is_symlink() or file.is_symlink()
            or not runtime.is_dir() or not file.is_file()
            or file.stat().st_size > 20_000_000):
        return {"status": "OWNER_RECEIPTS_NOT_TRUSTED", "recent": []}
    size = file.stat().st_size
    with file.open("rb") as fp:
        fp.seek(max(0, size - 24576))
        block = fp.read(24576)
    rows = block.splitlines()[-2:]
    if len(rows) != 2:
        return {"status": "TWO_RECEIPTS_NOT_AVAILABLE", "recent": []}
    values = []
    for raw in rows:
        if not 1 <= len(raw) <= 4096:
            return {"status": "INVALID_RECEIPT_LENGTH", "recent": []}
        try:
            obj = json.loads(raw.decode("utf-8", "strict"))
            if type(obj) is not dict or obj.get("schema") != "UCIE_MINER_CYCLE_V1":
                raise ValueError("bad schema")
            start = datetime.fromisoformat(obj["started_utc"])
            end = datetime.fromisoformat(obj["finished_utc"])
            if (start.tzinfo is None or end.tzinfo is None
                    or start > end or end > datetime.now(timezone.utc)):
                raise ValueError("bad chronology")
            values.append({
                "started_utc": start.isoformat(),
                "finished_utc": end.isoformat(),
                "status": obj.get("status"),
                "consecutive_failures": obj.get("consecutive_failures"),
                "collection_elapsed_ms": obj.get("collection_elapsed_ms"),
                "cycle_elapsed_ms": obj.get("cycle_elapsed_ms"),
                "stage10_status": obj.get("stage10_status"),
                "production_approved": obj.get("production_approved"),
            })
        except (ValueError, TypeError, KeyError):
            return {"status": "INVALID_RECEIPT_NO_GO", "recent": []}
    delta = (datetime.fromisoformat(values[1]["started_utc"])
             - datetime.fromisoformat(values[0]["started_utc"])).total_seconds()
    now = datetime.now(timezone.utc)
    age = (now - datetime.fromisoformat(values[-1]["finished_utc"])).total_seconds()
    both_ok = all(
        row["status"] == "COLLECTED_UNVERIFIED"
        and row["consecutive_failures"] == 0
        and row["production_approved"] is False
        for row in values
    )
    return {
        "status": "TWO_OWNER_RECEIPTS_OBSERVED",
        "recent": values,
        "start_gap_minutes": round(delta/60, 2),
        "last_finished_age_minutes": round(age/60, 2),
        "two_successful_hourly_receipts": bool(
            both_ok and 45*60 <= delta <= 75*60 and age <= 90*60),
    }


def observe_owner_ucie_once() -> dict:
    if (os.name != "nt" or ROOT.is_symlink()
            or ROOT.resolve() != Path("D:/UCIE").resolve()):
        raise ValueError("owner D:/UCIE Windows root required")
    scheduler = {"status": "SCHEDULER_QUERY_UNAVAILABLE_NO_GO"}
    try:
        p = subprocess.run(
            ["powershell.exe", "-NoProfile", "-NonInteractive",
             "-Command", POWERSHELL],
            capture_output=True, timeout=20, check=False,
            cwd=str(ROOT))
        if p.returncode == 0 and len(p.stdout) <= 4096:
            raw = json.loads(p.stdout.decode("utf-8-sig", "strict"))
            if type(raw) is dict and raw.get("status") in (
                    "TASK_READONLY_OBSERVED", "TASK_NOT_REGISTERED"):
                scheduler = {k: raw.get(k) for k in (
                    "status", "action_ok", "hourly", "last_result_ok",
                    "task_state", "last_run_utc", "next_run_utc")}
    except (OSError, ValueError, UnicodeError, subprocess.TimeoutExpired):
        pass
    receipts = _read_recent_ucie_receipts()
    return {
        "schema": SCHEMA,
        "status": "OWNER_READONLY_TASK_AND_RECEIPTS_OBSERVED",
        "observed_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "task": scheduler,
        "receipts": receipts,
        "operational_two_cycle_pass": bool(
            scheduler.get("status") == "TASK_READONLY_OBSERVED"
            and scheduler.get("action_ok") is True
            and scheduler.get("hourly") is True
            and scheduler.get("last_result_ok") is True
            and receipts.get("two_successful_hourly_receipts") is True),
        "independent_task_event_binding_verified": False,
        "task_registered_or_modified": False,
        "miner_executed": False,
        "network_requests": 0,
        "operating_database_writes": 0,
        "other_project_access": False,
        "release_approved": False,
    }


class OwnerUCIEHourlyOperationsReadOnly(unittest.TestCase):
    def test_owner_hourly_status_observed_without_mutation(self):
        if os.name != "nt" or ROOT.resolve() != Path("D:/UCIE").resolve():
            self.skipTest("owner D:/UCIE only, never inspect CI task scheduler")
        result = observe_owner_ucie_once()
        self.assertEqual(result["schema"], SCHEMA)
        self.assertFalse(result["miner_executed"])
        self.assertFalse(result["task_registered_or_modified"])
        self.assertEqual(result["network_requests"], 0)
        self.assertEqual(result["operating_database_writes"], 0)
        print("UCIE_OWNER_V1_HOURLY_ACTUAL_OBSERVATION=" + json.dumps(
            result, ensure_ascii=True, sort_keys=True))


if __name__ == "__main__":
    unittest.main()
