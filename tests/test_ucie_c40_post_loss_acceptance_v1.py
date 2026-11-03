"""Read-only UCIE C40 real fault recovery acceptance: owner journal + live PID.

Does not start/stop processes, modify tasks or read non-UCIE assets.
Host-only acceptance. CI without the owner UCIE profile skips.
"""
from __future__ import annotations

from datetime import datetime, timezone
import json
import os
from pathlib import Path
import shutil
import subprocess
import unittest

ROOT = Path(r"D:\UCIE")
PROFILE = Path(r"D:\UCIE_DATA\mcp_tunnel_profiles\ucie-private-c40.yaml")
JOURNAL = ROOT / ".ucie_bridge_state" / "c40_owner_loss_drill_v1.json"
HEALTH = ROOT / ".ucie_bridge_state" / "c40_supervisor_health_v1.json"
PINNED_SCRIPT_SHA = "23dcb08524b32c611b43c1136a444286d7dc776598a739a7152a651a5244e66f"


def utc(value):
    parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("UTC timestamp missing offset")
    return parsed.astimezone(timezone.utc)


def guarded_json(path, limit):
    if not path.is_file() or path.is_symlink() or path.stat().st_size > limit:
        raise AssertionError("UCIE bounded receipt missing, linked, or oversized: " + path.name)
    obj = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(obj, dict):
        raise AssertionError("UCIE receipt is not an object: " + path.name)
    return obj


class C40PostLossOwnerAcceptance(unittest.TestCase):
    def test_live_restoration_matches_one_time_journal(self):
        if os.name != "nt" or not PROFILE.is_file():
            self.skipTest("UCIE owner Windows host only")
        shell = shutil.which("powershell.exe")
        if shell is None:
            self.skipTest("Windows PowerShell unavailable")
        journal = guarded_json(JOURNAL, 4096)
        self.assertEqual(journal.get("schema"), "UCIE_C40_OWNER_LOSS_DRILL_V1")
        self.assertEqual(journal.get("status"), "SINGLE_CLIENT_RESTART_RECEIPT_OBSERVED")
        self.assertIs(journal.get("other_tasks_modified"), False)
        self.assertIs(journal.get("operating_database_modified"), False)
        self.assertIs(journal.get("requires_chatgpt_bridge_recheck"), True)
        fault = utc(journal["fault_utc"])
        updated = utc(journal["updated_utc"])
        now = datetime.now(timezone.utc)
        self.assertLessEqual(fault, updated)
        self.assertLessEqual(updated, now.replace(microsecond=now.microsecond))
        self.assertLess((now - fault).total_seconds(), 86400, "UCIE fault receipt is old")
        old_pid = int(journal["original_pid"])
        new_pid = int(journal["recovered_pid"])
        self.assertGreater(old_pid, 0)
        self.assertGreater(new_pid, 0)
        self.assertNotEqual(old_pid, new_pid)

        health = guarded_json(HEALTH, 2048)
        self.assertEqual(health.get("schema"), "UCIE_C40_SUPERVISOR_HEALTH_V1")
        self.assertEqual(health.get("stage"), "CYCLE_OK")
        self.assertIn(health.get("code"),
                      {"UCIE_C40_CHILD_STARTED", "UCIE_C40_ALREADY_RUNNING"})
        self.assertEqual(health.get("client_count"), 1)
        recorded = utc(health["utc"])
        age = (now - recorded).total_seconds()
        self.assertGreaterEqual(age, -10)
        self.assertLessEqual(age, 420, "UCIE supervisor receipt stale")
        self.assertGreaterEqual((recorded - fault).total_seconds(), -3)

        ps = r"""
$ErrorActionPreference='Stop'
$taskList=@(Get-ScheduledTask -TaskName 'UCIE-C40-Recover' -ErrorAction Stop |
    Where-Object { [string]$_.TaskPath -eq [string][char]92 })
if($taskList.Count -ne 1){throw 'UCIE_POSTLOSS_EXACT_ROOT_TASK_REQUIRED'}
$task=$taskList[0]
$info=Get-ScheduledTaskInfo -TaskName 'UCIE-C40-Recover' -ErrorAction Stop
$sid=[Security.Principal.WindowsIdentity]::GetCurrent().User.Value
$id=[string]$task.Principal.UserId
if($id -match '^S-1-[0-9]+(?:-[0-9]+)+$'){$taskSid=$id}
else{$taskSid=([Security.Principal.NTAccount]::new($id)).Translate(
    [Security.Principal.SecurityIdentifier]).Value}
$actions=@($task.Actions)
$expectPS=Join-Path $env:WINDIR 'System32\WindowsPowerShell\v1.0\powershell.exe'
$script='D:\UCIE\scripts\ucie_c40_recover.ps1'
$actionOK=($actions.Count -eq 1 -and
    [string]::Equals([string]$actions[0].Execute,$expectPS,
        [StringComparison]::OrdinalIgnoreCase) -and
    ([string]$actions[0].Arguments).Contains($script) -and
    ([string]$actions[0].Arguments).Contains('-Mode Supervise') -and
    ([string]$actions[0].Arguments).Contains('-EnableAdminTools'))
$clientExe='D:\UCIE_DATA\tools\tunnel-client-v0.0.16\tunnel-client.exe'
$rows=@(Get-CimInstance Win32_Process -Filter
    "Name = 'tunnel-client.exe' AND ExecutablePath LIKE '%UCIE_DATA%'" -ErrorAction Stop |
    Where-Object {
        [string]::Equals([string]$_.ExecutablePath,$clientExe,
           [StringComparison]::OrdinalIgnoreCase)
    })
$pidValue=0
$startUtc=''
$exact=$false
if($rows.Count -eq 1){
    $c=$rows[0]
    $native=Get-Process -Id ([int]$c.ProcessId) -ErrorAction Stop
    $exact=([string]::Equals([string]$native.Path,$clientExe,
        [StringComparison]::OrdinalIgnoreCase) -and
        ([string]$c.CommandLine).Contains('--profile-file') -and
        ([string]$c.CommandLine).Contains('ucie-private-c40') -and
        [math]::Abs((([datetime]$native.StartTime).ToUniversalTime() -
                     ([datetime]$c.CreationDate).ToUniversalTime()).TotalSeconds) -le 2)
    $pidValue=[int]$c.ProcessId
    $startUtc=([datetime]$c.CreationDate).ToUniversalTime().ToString('o')
}
[pscustomobject]@{
 schema='UCIE_C40_POST_LOSS_LIVE_PROCESS_READONLY_V1'
 owner_matches=[string]::Equals($sid,$taskSid,
    [StringComparison]::OrdinalIgnoreCase)
 task_state=[string]$task.State
 task_runlevel=[string]$task.Principal.RunLevel
 task_logontype=[string]$task.Principal.LogonType
 task_action_matches=[bool]$actionOK
 task_last_result=[int]$info.LastTaskResult
 recovery_source_sha=(Get-FileHash -LiteralPath $script -Algorithm SHA256).Hash.ToLowerInvariant()
 exact_client_count=$rows.Count
 exact_client_identity=[bool]$exact
 exact_client_pid=$pidValue
 exact_client_started_utc=$startUtc
 no_process_or_task_control=$true
} | ConvertTo-Json -Compress
"""
        result = subprocess.run(
            [shell, "-NoProfile", "-NonInteractive", "-Command", ps],
            capture_output=True, text=True, errors="replace", timeout=40, check=False
        )
        self.assertEqual(result.returncode, 0, "UCIE exact live owner query failed")
        rows = result.stdout.strip().splitlines()
        self.assertTrue(rows, "UCIE owner query returned no JSON")
        live = json.loads(rows[-1])
        self.assertEqual(live["schema"], "UCIE_C40_POST_LOSS_LIVE_PROCESS_READONLY_V1")
        self.assertTrue(live["owner_matches"])
        self.assertEqual(live["task_state"], "Running")
        self.assertEqual(live["task_runlevel"], "Highest")
        self.assertEqual(live["task_logontype"], "Interactive")
        self.assertTrue(live["task_action_matches"])
        self.assertEqual(live["task_last_result"], 267009)
        self.assertEqual(live["recovery_source_sha"], PINNED_SCRIPT_SHA)
        self.assertEqual(live["exact_client_count"], 1)
        self.assertTrue(live["exact_client_identity"])
        self.assertEqual(live["exact_client_pid"], new_pid)
        started = utc(live["exact_client_started_utc"])
        self.assertGreaterEqual((started - fault).total_seconds(), -3)
        self.assertTrue(live["no_process_or_task_control"])

        print("UCIE_C40_POST_LOSS_ACCEPTANCE=" + json.dumps({
            "schema": "UCIE_C40_POST_LOSS_ACCEPTANCE_V1",
            "verdict": "LIVE_LOSS_AUTO_RESTART_HOST_CONFIRMED",
            "old_pid": old_pid,
            "new_pid": new_pid,
            "fault_utc": fault.isoformat(),
            "journal_updated_utc": updated.isoformat(),
            "new_client_created_utc": started.isoformat(),
            "supervisor_utc": recorded.isoformat(),
            "supervisor_code": health["code"],
            "supervisor_age_seconds": round(age, 1),
            "task_state": live["task_state"],
            "task_runlevel": live["task_runlevel"],
            "client_count": 1,
            "mcp_bridge_reconnect_verification_external": True,
            "relogin_acceptance_pending": True,
            "no_process_or_task_control": True,
        }, sort_keys=True))


if __name__ == "__main__":
    unittest.main()
