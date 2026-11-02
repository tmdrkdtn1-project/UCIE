"""UCIE-only Windows C40 scheduled-task read-only failure evidence.

Never launches or modifies a process, task, service or database. Prints only
bounded technical status, UTC times, event IDs and outcome codes.
"""
from __future__ import annotations
import json
import os
from pathlib import Path
import shutil
import subprocess
import unittest

HOST_PROFILE = Path(r"D:\UCIE_DATA\mcp_tunnel_profiles\ucie-private-c40.yaml")


class UCIEC40FailureEvidence(unittest.TestCase):
    def test_ucie_only_scheduler_diagnostic(self):
        if os.name != "nt" or not HOST_PROFILE.is_file():
            self.skipTest("not the UCIE owner Windows host")
        shell = shutil.which("powershell.exe")
        if not shell:
            self.skipTest("Windows PowerShell absent")
        program = r"""
$ErrorActionPreference = 'Stop'
$taskName = 'UCIE-C40-Recover'
$task = Get-ScheduledTask -TaskName $taskName -ErrorAction Stop
$info = Get-ScheduledTaskInfo -TaskName $taskName -ErrorAction Stop
$action = @($task.Actions)[0]
$path = 'D:\UCIE\scripts\ucie_c40_recover.ps1'
$expected = 'db7bd2529a42679399f19ddbdb005d4d9985867c7343824d12e83879b06e491a'
$shaOK = ((Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToLowerInvariant() -eq $expected)
$ownerSid = [Security.Principal.WindowsIdentity]::GetCurrent().User.Value
$p = [string]$task.Principal.UserId
try {
    if ($p -match '^S-1-[0-9]+(?:-[0-9]+)+$') { $sid = $p }
    else {
        $sid = ([Security.Principal.NTAccount]::new($p)).Translate(
            [Security.Principal.SecurityIdentifier]).Value
    }
    $ownerMatch = [string]::Equals($ownerSid,$sid,[StringComparison]::OrdinalIgnoreCase)
}
catch { $ownerMatch = $false }
$eventRows = @()
$eventRead = 'NO_EVENTS_OR_HISTORY_NOT_ENABLED'
try {
    $events = @(Get-WinEvent -FilterHashtable @{
        LogName='Microsoft-Windows-TaskScheduler/Operational'
        StartTime=(Get-Date).AddHours(-5)
        Id=@(100,101,102,103,106,107,110,111,129,140,200,201,202,203)
    } -MaxEvents 350 -ErrorAction Stop)
    $events = @($events | Where-Object { ([string]$_.Message).Contains($taskName) } |
        Select-Object -First 12)
    $eventRows = @($events | ForEach-Object {
        $fields = @($_.Properties | ForEach-Object {
            $value = [string]$_.Value
            if ($value -match '^(0x[0-9a-fA-F]{1,10}|-?[0-9]{1,10})$') {
                $value
            }
        } | Where-Object { $_ })
        [pscustomobject]@{
            id = [int]$_.Id
            level = [int]$_.Level
            utc = $_.TimeCreated.ToUniversalTime().ToString('o')
            numeric_properties = @($fields | Select-Object -First 4)
        }
    })
    $eventRead = 'READ'
} catch {
    $eventRead = 'UNAVAILABLE_OR_EMPTY'
}
$client = 'D:\UCIE_DATA\tools\tunnel-client-v0.0.16\tunnel-client.exe'
$clients = @(Get-CimInstance Win32_Process -Filter "Name = 'tunnel-client.exe' AND ExecutablePath LIKE '%UCIE_DATA%'" -ErrorAction Stop |
 Where-Object { [string]::Equals([string]$_.ExecutablePath,$client,[StringComparison]::OrdinalIgnoreCase) -and
    ([string]$_.CommandLine).Contains('ucie-private-c40') })
[pscustomobject]@{
 schema='UCIE_C40_TASK_FAILURE_READONLY_V1'
 task_state=[string]$task.State
 last_result=[int]$info.LastTaskResult
 last_run_utc=$info.LastRunTime.ToUniversalTime().ToString('o')
 start_utc=(Get-Date).ToUniversalTime().ToString('o')
 action_program_matches=([string]$action.Execute -match '(?i)WindowsPowerShell.*powershell.exe')
 action_arguments_supervise=([string]$action.Arguments).Contains('-Mode Supervise')
 action_arguments_admin=([string]$action.Arguments).Contains('-EnableAdminTools')
 task_owner_sid_matches=[bool]$ownerMatch
 task_run_level=[string]$task.Principal.RunLevel
 task_logon_type=[string]$task.Principal.LogonType
 client_count=$clients.Count
 pinned_script_sha_matches=[bool]$shaOK
 event_history_status=$eventRead
 events=$eventRows
 other_tasks_changed=$false
 task_changed=$false
 live_db_changed=$false
} | ConvertTo-Json -Depth 6 -Compress
"""
        run = subprocess.run([shell,"-NoProfile","-NonInteractive","-Command",program],
                             text=True,capture_output=True,timeout=35,check=False)
        self.assertEqual(run.returncode,0,
                         "UCIE C40 read-only diagnostic could not complete")
        try:
            data=json.loads(run.stdout.strip())
        except json.JSONDecodeError as exc:
            raise AssertionError("no UCIE C40 structured diagnostic output") from exc
        print("UCIE_C40_READONLY_DIAGNOSTIC="+json.dumps(data,sort_keys=True))
        self.assertEqual(data["schema"],"UCIE_C40_TASK_FAILURE_READONLY_V1")
        self.assertTrue(data["pinned_script_sha_matches"])
        self.assertTrue(data["task_owner_sid_matches"])
        self.assertEqual(data["client_count"],1)
        self.assertFalse(data["task_changed"])
        self.assertFalse(data["other_tasks_changed"])
        self.assertFalse(data["live_db_changed"])


if __name__=="__main__":
    unittest.main()
