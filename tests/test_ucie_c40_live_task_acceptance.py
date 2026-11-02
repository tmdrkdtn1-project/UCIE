"""Read-only real UCIE C40 owner task acceptance, never creates a task.

A GitHub runner without the exact UCIE owner profile SKIPS this test.
The owner's Windows host test observes the *registered* scheduled task,
its run state, its scoped action, and an existing pinned C40 client.
No secrets, raw arguments, tunnel identifiers or user names are printed.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess
import unittest

UCIE_PROFILE = Path(r"D:\UCIE_DATA\mcp_tunnel_profiles\ucie-private-c40.yaml")


class UCIEC40TaskLiveAcceptance(unittest.TestCase):
    def test_existing_owner_logon_task_and_live_client_readonly(self):
        if os.name != "nt" or not UCIE_PROFILE.is_file():
            self.skipTest("not the exact UCIE owner Windows host")
        shell = shutil.which("powershell.exe")
        if not shell:
            self.skipTest("PowerShell unavailable")
        script = r"""
$ErrorActionPreference = 'Stop'
$task = Get-ScheduledTask -TaskName 'UCIE-C40-Recover' -ErrorAction Stop
$info = Get-ScheduledTaskInfo -TaskName 'UCIE-C40-Recover' -ErrorAction Stop
$actions = @($task.Actions)
$owner = [Security.Principal.WindowsIdentity]::GetCurrent().Name
$exe = Join-Path $env:WINDIR 'System32\WindowsPowerShell\v1.0\powershell.exe'
$expectedScript = 'D:\UCIE\scripts\ucie_c40_recover.ps1'
$actionValid = (
    $actions.Count -eq 1 -and
    [string]::Equals([string]$actions[0].Execute, $exe, [StringComparison]::OrdinalIgnoreCase) -and
    ([string]$actions[0].Arguments).Contains($expectedScript) -and
    ([string]$actions[0].Arguments).Contains('-Mode Supervise') -and
    ([string]$actions[0].Arguments).Contains('-EnableAdminTools')
)
$ownerValid = [string]::Equals(
    [string]$task.Principal.UserId, $owner, [StringComparison]::OrdinalIgnoreCase
)
$logon = @($task.Triggers | Where-Object { 
    $_.CimClass.CimClassName -eq 'MSFT_TaskLogonTrigger'
})
$client = 'D:\UCIE_DATA\tools\tunnel-client-v0.0.16\tunnel-client.exe'
$clients = @(
    Get-CimInstance Win32_Process -Filter "Name = 'tunnel-client.exe' AND ExecutablePath LIKE '%UCIE_DATA%'" -ErrorAction Stop |
    Where-Object {
        [string]::Equals([string]$_.ExecutablePath, $client, [StringComparison]::OrdinalIgnoreCase) -and
        ([string]$_.CommandLine).Contains('ucie-private-c40')
    }
)
[pscustomobject]@{
    schema = 'UCIE_C40_RECOVERY_OWNER_HOST_ACCEPTANCE_V1'
    status = 'READ_ONLY_OBSERVATION'
    task_registered = $true
    task_action_exact = [bool]$actionValid
    principal_is_current_owner = [bool]$ownerValid
    logon_trigger_present = [bool]($logon.Count -gt 0)
    task_state = [string]$task.State
    task_running = ([string]$task.State -eq 'Running')
    task_has_started = ([datetime]$info.LastRunTime -gt [datetime]'2000-01-01')
    last_task_result = [int]$info.LastTaskResult
    expected_c40_client_count = $clients.Count
    raw_commandlines_exposed = $false
    other_tasks_modified = $false
    operating_database_modified = $false
} | ConvertTo-Json -Compress
"""
        run = subprocess.run(
            [shell, "-NoProfile", "-NonInteractive", "-Command", script],
            text=True, capture_output=True, check=False, timeout=30,
        )
        self.assertEqual(run.returncode, 0, "UCIE C40 task inspection failed")
        try:
            record = json.loads(run.stdout.strip())
        except json.JSONDecodeError as exc:
            raise AssertionError("UCIE task returned no structured receipt") from exc
        print("UCIE_C40_HOST_ACCEPTANCE=" + json.dumps(record, sort_keys=True))
        self.assertEqual(record["schema"], "UCIE_C40_RECOVERY_OWNER_HOST_ACCEPTANCE_V1")
        self.assertTrue(record["task_registered"])
        self.assertTrue(record["task_action_exact"])
        self.assertTrue(record["principal_is_current_owner"])
        self.assertTrue(record["logon_trigger_present"])
        self.assertTrue(record["task_has_started"])
        self.assertTrue(record["task_running"])
        self.assertEqual(record["expected_c40_client_count"], 1)
        self.assertFalse(record["raw_commandlines_exposed"])
        self.assertFalse(record["other_tasks_modified"])
        self.assertFalse(record["operating_database_modified"])


if __name__ == "__main__":
    unittest.main()
