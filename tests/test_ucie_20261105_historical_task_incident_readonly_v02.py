"""UCIE-only bounded historical TaskScheduler query with known-good timediff XPath.

Do NOT mutate tasks, logs, collector/DB, or inspect other task names. Unlike
the earlier absolute-SystemTime XPath, this exact-task predicate is the same
shape as the already-working scripts/task_status.ps1 -Evidence query.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]
TASK = r"\UCIE-PublicMiner-Hourly"
MAX_EVENTS = 256
PWSH = r"""
$ErrorActionPreference = 'Stop'
$taskName = '\UCIE-PublicMiner-Hourly'
$start = [DateTime]::Parse('2026-11-05T05:35:00Z').ToUniversalTime()
$end = [DateTime]::Parse('2026-11-05T05:50:00Z').ToUniversalTime()
# The Windows event service filters to THIS UCIE task before events are read.
$xpath = "*[System[(EventID=100 or EventID=102 or EventID=200 or EventID=201 or EventID=111) and TimeCreated[timediff(@SystemTime) <= 259200000]] and EventData[Data[@Name='TaskName']='\UCIE-PublicMiner-Hourly']]"
try {
    $events = @(Get-WinEvent -LogName 'Microsoft-Windows-TaskScheduler/Operational' -FilterXPath $xpath -MaxEvents 256 -ErrorAction Stop)
    $rows = @()
    foreach ($item in $events) {
        $utc = $item.TimeCreated.ToUniversalTime()
        if ($utc -lt $start -or $utc -gt $end) { continue }
        [xml]$xml = $item.ToXml()
        $taskNode = $xml.SelectSingleNode("//*[local-name()='EventData']/*[local-name()='Data' and @Name='TaskName']")
        if ($null -eq $taskNode -or $taskNode.InnerText -cne $taskName) { continue }
        $instanceNode = $xml.SelectSingleNode("//*[local-name()='EventData']/*[local-name()='Data' and (@Name='InstanceId' or @Name='TaskInstanceId')]")
        $resultNode = $xml.SelectSingleNode("//*[local-name()='EventData']/*[local-name()='Data' and @Name='ResultCode']")
        $rows += [pscustomobject]@{
            event_id = [int]$item.Id
            at_utc = $utc.ToString('o')
            instance = if ($null -ne $instanceNode) { [string]$instanceNode.InnerText } else { '' }
            result_code = if ($null -ne $resultNode) { [string]$resultNode.InnerText } else { $null }
        }
    }
    $startIds = @($rows | Where-Object {$_.event_id -eq 100} | ForEach-Object {$_.instance} | Where-Object {$_ -ne ''})
    $terminationIds = @($rows | Where-Object {$_.event_id -eq 111} | ForEach-Object {$_.instance} | Where-Object {$_ -ne ''})
    $matchedTermination = @($terminationIds | Where-Object {$startIds -contains $_}).Count -gt 0
    [pscustomobject]@{
        schema = 'UCIE_HISTORICAL_FIXED_TASK_TIMEDIFF_RETRY_V02'
        status = if ($rows.Count -eq 0) { 'HISTORICAL_EVENT_WINDOW_NOT_AVAILABLE_NO_GO' } else { 'HISTORICAL_FIXED_TASK_EVENT_WINDOW_OBSERVED' }
        fixed_task_only = $true
        exact_window_start_utc = '2026-11-05T05:35:00Z'
        exact_window_end_utc = '2026-11-05T05:50:00Z'
        events_returned_from_exact_task_query = $events.Count
        query_clipped_at_256 = ($events.Count -ge 256)
        incident_window_events = $rows.Count
        event_ids = @($rows | ForEach-Object {$_.event_id})
        event_utc = @($rows | ForEach-Object {$_.at_utc})
        exit_codes = @($rows | Where-Object {$null -ne $_.result_code} | ForEach-Object {$_.result_code})
        event111_for_exact_task = @($rows | Where-Object {$_.event_id -eq 111}).Count -gt 0
        event111_instance_matches_start100 = $matchedTermination
        historical_root_cause_proven = $false
        production_remediation_executed = $false
        task_scheduler_modified = $false
        operating_database_writes = 0
    } | ConvertTo-Json -Compress -Depth 4
} catch {
    [pscustomobject]@{
        schema = 'UCIE_HISTORICAL_FIXED_TASK_TIMEDIFF_RETRY_V02'
        status = 'FIXED_TASK_EVENT_QUERY_UNAVAILABLE_NO_GO'
        query_error_type = $_.Exception.GetType().Name
        fixed_task_only = $true
        incident_window_events = 0
        historical_root_cause_proven = $false
        task_scheduler_modified = $false
        operating_database_writes = 0
    } | ConvertTo-Json -Compress
}
"""


class FixedTaskHistoricalRetry(unittest.TestCase):
    def test_query_is_bounded_exact_ucie_task_and_read_only(self):
        self.assertIn("timediff(@SystemTime) <= 259200000", PWSH)
        self.assertIn(r"EventData[Data[@Name='TaskName']='\UCIE-PublicMiner-Hourly']", PWSH)
        self.assertIn("Get-WinEvent", PWSH)
        self.assertIn("-MaxEvents 256", PWSH)
        self.assertIn("2026-11-05T05:35:00Z", PWSH)
        self.assertIn("2026-11-05T05:50:00Z", PWSH)
        for command in (
            "Start-ScheduledTask", "Stop-ScheduledTask", "Set-ScheduledTask",
            "Register-ScheduledTask", "Unregister-ScheduledTask",
            "Stop-Process", "Start-Process", "Clear-EventLog", "Remove-Item",
        ):
            self.assertNotIn(command + " ", PWSH)
        self.assertFalse("Get-WinEvent -FilterHashtable" in PWSH)

    @unittest.skipUnless(os.name == "nt" and shutil.which("powershell.exe"),
                         "Owner Windows PowerShell 5.1 required")
    def test_owner_historical_incident_query(self):
        if ROOT.resolve() != Path("D:/UCIE").resolve() or ROOT.is_symlink():
            self.skipTest("UCIE owner root not mounted")
        child = subprocess.run(
            ["powershell.exe", "-NoProfile", "-NonInteractive",
             "-Command", PWSH],
            cwd=str(ROOT), check=False, capture_output=True,
            timeout=20, env={"SystemRoot": os.environ.get("SystemRoot", "C:\\Windows"),
                             "PATH": os.environ.get("PATH", "")},
        )
        self.assertEqual(child.returncode, 0)
        self.assertLessEqual(len(child.stdout), 25000)
        result = json.loads(child.stdout.decode("utf-8-sig", "strict"))
        self.assertEqual(result["schema"],
                         "UCIE_HISTORICAL_FIXED_TASK_TIMEDIFF_RETRY_V02")
        self.assertTrue(result["fixed_task_only"])
        self.assertFalse(result["historical_root_cause_proven"])
        self.assertFalse(result["task_scheduler_modified"])
        self.assertEqual(result["operating_database_writes"], 0)
        self.assertIn(result["status"], (
            "HISTORICAL_FIXED_TASK_EVENT_WINDOW_OBSERVED",
            "HISTORICAL_EVENT_WINDOW_NOT_AVAILABLE_NO_GO",
            "FIXED_TASK_EVENT_QUERY_UNAVAILABLE_NO_GO"))
        if result["status"] == "HISTORICAL_FIXED_TASK_EVENT_WINDOW_OBSERVED":
            self.assertGreater(result["incident_window_events"], 0)
        print("UCIE_HISTORICAL_FIXED_TASK_RETRY_V02=" +
              json.dumps(result, sort_keys=True, ensure_ascii=True))


if __name__ == "__main__":
    unittest.main()
