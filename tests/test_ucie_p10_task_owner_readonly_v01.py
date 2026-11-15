"""UCIE-only exact Windows minute-task registration and event read-only QA.

One fixed task name; bounded event IDs and no commands for task mutation.
An event-only success is NOT a P10 queue-job completion or approval to rearm.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]
TASK = r"\UCIE-Internal-Minute"
PS = r"""
$ErrorActionPreference='Stop'
$root='D:\UCIE'
$name='UCIE-Internal-Minute'
$task=Get-ScheduledTask -TaskPath '\' -TaskName $name -ErrorAction SilentlyContinue
if ($null -eq $task) {
    [pscustomobject]@{schema='UCIE_P10_FIXED_TASK_READONLY_V01';status='P10_TASK_NOT_FOUND_NO_GO';task_found=$false;task_changed=$false;other_tasks_queried=$false;instance_receipt_binding_proven=$false} | ConvertTo-Json -Compress
    exit 0
}
$info=Get-ScheduledTaskInfo -TaskPath '\' -TaskName $name
$expectedPy=Join-Path $root '.venv\Scripts\python.exe'
$expectedArg='-B "' + (Join-Path $root 'scripts\internal_minute_tick.py') + '"'
$actions=@($task.Actions)
$actionMatches=($actions.Count -eq 1 -and
    [string]::Equals([string]$actions[0].Execute,$expectedPy,[StringComparison]::OrdinalIgnoreCase) -and
    [string]::Equals([string]$actions[0].Arguments,$expectedArg,[StringComparison]::Ordinal) -and
    [string]::Equals(([string]$actions[0].WorkingDirectory).TrimEnd('\'),$root,[StringComparison]::OrdinalIgnoreCase))
$ownerMatch=$false
try {
    $localSid=[System.Security.Principal.WindowsIdentity]::GetCurrent().User
    $identity=[string]$task.Principal.UserId
    if ($identity -match '^S-[0-9]+-[0-9]+(-[0-9]+)+$') {
        $sid=[System.Security.Principal.SecurityIdentifier]::new($identity)
    } else {
        $sid=([System.Security.Principal.NTAccount]::new($identity)).Translate([System.Security.Principal.SecurityIdentifier])
    }
    $ownerMatch=$sid.Equals($localSid)
} catch { $ownerMatch=$false }
$intervals=@($task.Triggers | ForEach-Object {[string]$_.Repetition.Interval})
$cadenceMatches=($intervals.Count -eq 1 -and $intervals[0] -eq 'PT1M' -and [string]$task.Settings.MultipleInstances -eq 'IgnoreNew')
$principalMatches=($ownerMatch -and [string]$task.Principal.LogonType -eq 'Interactive' -and [string]$task.Principal.RunLevel -eq 'Limited')
$eventRead=$false
$boundedEventCount=0
$completeActionInstances=0
$eventsClipped=$false
$eventErrorType=$null
try {
    $xpath="*[System[(EventID=100 or EventID=102 or EventID=200 or EventID=201) and TimeCreated[timediff(@SystemTime) <= 7200000]] and EventData[Data[@Name='TaskName']='\UCIE-Internal-Minute']]"
    $events=@(Get-WinEvent -LogName 'Microsoft-Windows-TaskScheduler/Operational' -FilterXPath $xpath -MaxEvents 64 -ErrorAction Stop)
    $eventRead=$true
    $boundedEventCount=$events.Count
    $eventsClipped=$events.Count -ge 64
    $instances=@{}
    foreach ($ev in $events) {
        if ($ev.Id -notin @(100,102,200,201)) { continue }
        [xml]$xml=$ev.ToXml()
        $node=$xml.SelectSingleNode("//*[local-name()='EventData']/*[local-name()='Data' and (@Name='TaskInstanceId' or @Name='InstanceId')]")
        if ($null -eq $node) { continue }
        $id=[guid]::Empty
        if (-not [guid]::TryParse([string]$node.InnerText,[ref]$id)) { continue }
        $key=$id.ToString('D')
        if (-not $instances.ContainsKey($key)) {
            $instances[$key]=@{e100=$false;e102=$false;e200=$false;e201=$false;r201=$false}
        }
        $row=$instances[$key]
        if ($ev.Id -eq 100) {$row.e100=$true}
        if ($ev.Id -eq 102) {$row.e102=$true}
        if ($ev.Id -eq 200) {$row.e200=$true}
        if ($ev.Id -eq 201) {
            $row.e201=$true
            $result=$xml.SelectSingleNode("//*[local-name()='EventData']/*[local-name()='Data' and @Name='ResultCode']")
            if ($null -ne $result) {
                $number=[int64]0
                if ([int64]::TryParse([string]$result.InnerText,[ref]$number) -and $number -eq 0) {$row.r201=$true}
            }
        }
    }
    foreach ($row in $instances.Values) {
        if ($row.e100 -and $row.e102 -and $row.e200 -and $row.e201 -and $row.r201) {$completeActionInstances++}
    }
} catch { $eventErrorType=$_.Exception.GetType().Name }
[pscustomobject]@{
 schema='UCIE_P10_FIXED_TASK_READONLY_V01'
 status='P10_TASK_READONLY_OBSERVED_NOT_QUEUE_ATTESTED'
 task_found=$true
 task_state=[string]$task.State
 task_last_result_decimal=[int64]$info.LastTaskResult
 task_action_matches=$actionMatches
 task_owner_sid_matches=$ownerMatch
 task_principal_matches=$principalMatches
 task_cadence_matches=$cadenceMatches
 task_execution_time_limit=[string]$task.Settings.ExecutionTimeLimit
 last_run_utc=if($info.LastRunTime -gt [datetime]::MinValue){$info.LastRunTime.ToUniversalTime().ToString('o')}else{$null}
 next_run_utc=if($info.NextRunTime -gt [datetime]::MinValue){$info.NextRunTime.ToUniversalTime().ToString('o')}else{$null}
 exact_task_event_log_readable=$eventRead
 bounded_exact_task_events=$boundedEventCount
 event_query_clipped=$eventsClipped
 complete_action_instance_count=$completeActionInstances
 event_error_type=$eventErrorType
 instance_receipt_binding_proven=$false
 task_changed=$false
 other_tasks_queried=$false
 public_api_gets=0
 database_writes=0
} | ConvertTo-Json -Compress -Depth 4
"""


class UCIEOnlyP10TaskReadOnly(unittest.TestCase):
    def test_01_static_task_scope_has_no_mutators(self):
        self.assertIn(TASK, PS)
        self.assertIn("-MaxEvents 64", PS)
        self.assertIn("EventData[Data[@Name='TaskName']", PS)
        for command in (
            "Start-ScheduledTask", "Stop-ScheduledTask", "Set-ScheduledTask",
            "Register-ScheduledTask", "Unregister-ScheduledTask",
            "Stop-Process", "Start-Process", "Remove-Item",
            "Invoke-WebRequest", "Invoke-RestMethod",
        ):
            self.assertNotIn(command + " ", PS)

    @unittest.skipUnless(os.name == "nt" and shutil.which("powershell.exe"),
                         "real owner Windows PowerShell 5.1 needed")
    def test_02_real_exact_minute_task_readonly(self):
        if (ROOT.resolve() != Path("D:/UCIE").resolve()
                or ROOT.is_symlink() or not (ROOT / ".git").is_dir()):
            self.skipTest("exact owner UCIE source not present")
        done=subprocess.run(
            ["powershell.exe","-NoProfile","-NonInteractive","-Command",PS],
            cwd=str(ROOT), capture_output=True, timeout=30,
            env={"SystemRoot":os.environ.get("SystemRoot","C:\\Windows"),
                 "PATH":os.environ.get("PATH","")}, check=False)
        self.assertEqual(done.returncode,0)
        self.assertLessEqual(len(done.stdout), 14000)
        data=json.loads(done.stdout.decode("utf-8-sig","strict"))
        self.assertEqual(data["schema"],"UCIE_P10_FIXED_TASK_READONLY_V01")
        self.assertFalse(data["task_changed"])
        self.assertFalse(data["other_tasks_queried"])
        self.assertFalse(data["instance_receipt_binding_proven"])
        if data["task_found"]:
            self.assertIn(data["task_state"],
                          ("Ready","Running","Disabled","Queued","Unknown"))
            self.assertLessEqual(data["bounded_exact_task_events"],64)
        print("UCIE_P10_TASK_OWNER_READONLY=" +
              json.dumps(data,sort_keys=True,ensure_ascii=True))


if __name__=="__main__":
    unittest.main()
