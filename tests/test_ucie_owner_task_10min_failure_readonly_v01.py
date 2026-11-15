"""Read-only diagnosis of exactly one UCIE Windows TaskScheduler update failure.

No attempt to Set/Start/Stop/Register/Delete any task or touch operating DB.
Never serialize user names, SIDs, task XML, raw exceptions, or file contents.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]
POWERSHELL = r"""
$ErrorActionPreference = 'Stop'
$name = 'UCIE-PublicMiner-Hourly'
$task = Get-ScheduledTask -TaskPath '\' -TaskName $name -ErrorAction Stop
$info = Get-ScheduledTaskInfo -TaskPath '\' -TaskName $name -ErrorAction Stop
$owner = [string]$task.Principal.UserId
try {
    $ownerSid = if ($owner -match '^S-[0-9]+-[0-9]+(-[0-9]+)+$') {
        [System.Security.Principal.SecurityIdentifier]::new($owner)
    } else {
        ([System.Security.Principal.NTAccount]::new($owner)).Translate(
            [System.Security.Principal.SecurityIdentifier])
    }
    $sameOwner = $ownerSid.Equals([System.Security.Principal.WindowsIdentity]::GetCurrent().User)
} catch { $sameOwner = $false }
$who = [System.Security.Principal.WindowsPrincipal]::new(
    [System.Security.Principal.WindowsIdentity]::GetCurrent())
$elevated = $who.IsInRole([System.Security.Principal.WindowsBuiltInRole]::Administrator)
$taskFile = Join-Path $env:SystemRoot 'System32\Tasks\UCIE-PublicMiner-Hourly'
$fileAclReadable = $false
try {
    $acl = Get-Acl -LiteralPath $taskFile -ErrorAction Stop
    $fileAclReadable = ($null -ne $acl)
} catch { $fileAclReadable = $false }
$descriptorReadable = $false
$descriptorErrorType = $null
try {
    $svc = New-Object -ComObject Schedule.Service
    $svc.Connect()
    $folder = $svc.GetFolder('\')
    $registered = $folder.GetTask($name)
    $sddl = $registered.GetSecurityDescriptor(4)
    $descriptorReadable = -not [string]::IsNullOrWhiteSpace([string]$sddl)
} catch { $descriptorErrorType = $_.Exception.GetType().Name }
$triggers = @($task.Triggers)
$previewTriggerValid = $false
$previewTriggerErrorType = $null
$oldDurationDays = $null
try {
    if ($triggers.Count -eq 1) {
        $duration = [System.Xml.XmlConvert]::ToTimeSpan(
            [string]$triggers[0].Repetition.Duration)
        $oldDurationDays = [math]::Round($duration.TotalDays, 1)
        $candidate = New-ScheduledTaskTrigger -Once -At (Get-Date).AddMinutes(10) -RepetitionInterval (New-TimeSpan -Minutes 10) -RepetitionDuration $duration -ErrorAction Stop
        $previewTriggerValid = ([string]$candidate.Repetition.Interval -eq 'PT10M')
    }
} catch {
    $previewTriggerErrorType = $_.Exception.GetType().Name
}
[pscustomobject]@{
 schema = 'UCIE_EXACT_OWNER_TASK_10MIN_FAILURE_READONLY_V01'
 status = 'OWNER_TASK_PERMISSION_DIAGNOSTIC_ONLY_NO_GO'
 task_found = $true
 task_state = [string]$task.State
 actual_interval = if ($triggers.Count -eq 1) { [string]$triggers[0].Repetition.Interval } else { 'AMBIGUOUS_TRIGGERS' }
 trigger_count = $triggers.Count
 last_result_decimal = [int64]$info.LastTaskResult
 owner_matches_current_sid = $sameOwner
 current_process_has_elevated_admin_token = $elevated
 exact_task_file_acl_readable = $fileAclReadable
 task_dacl_descriptor_readable = $descriptorReadable
 descriptor_error_type = $descriptorErrorType
 task_modify_permission_proven = $false
 original_mutation_error_hresult_known = $false
 original_duration_days = $oldDurationDays
 in_memory_new_trigger_pt10m_valid = $previewTriggerValid
 in_memory_trigger_error_type = $previewTriggerErrorType
 scheduler_modified = $false
 operating_db_modified = $false
 other_tasks_read = $false
} | ConvertTo-Json -Compress
"""


class TaskPermissionsReadOnlyTests(unittest.TestCase):
    def test_01_fixed_scope_and_no_mutations(self):
        self.assertIn("UCIE-PublicMiner-Hourly", POWERSHELL)
        self.assertIn("Get-ScheduledTaskInfo", POWERSHELL)
        self.assertIn("Get-Acl", POWERSHELL)
        for mutation in (
            "Set-ScheduledTask ", "Register-ScheduledTask ",
            "Unregister-ScheduledTask ", "Start-ScheduledTask ",
            "Stop-ScheduledTask ", "Remove-Item ", "Invoke-WebRequest ",
        ):
            self.assertNotIn(mutation, POWERSHELL)

    @unittest.skipUnless(os.name == "nt" and shutil.which("powershell.exe"),
                         "exact owner Windows only")
    def test_02_real_owner_exact_task_permission_evidence(self):
        if (ROOT.resolve() != Path("D:/UCIE").resolve()
                or ROOT.is_symlink() or not (ROOT / ".git").is_dir()):
            self.skipTest("exact UCIE owner repository unavailable")
        child = subprocess.run(
            ["powershell.exe", "-NoProfile", "-NonInteractive",
             "-Command", POWERSHELL],
            cwd=str(ROOT), capture_output=True, timeout=30, check=False,
            env={"SystemRoot": os.environ.get("SystemRoot", "C:\\Windows"),
                 "PATH": os.environ.get("PATH", "")},
        )
        self.assertEqual(child.returncode, 0)
        self.assertLessEqual(len(child.stdout), 3200)
        data = json.loads(child.stdout.decode("utf-8-sig"))
        self.assertEqual(data["schema"],
                         "UCIE_EXACT_OWNER_TASK_10MIN_FAILURE_READONLY_V01")
        self.assertTrue(data["task_found"])
        self.assertFalse(data["scheduler_modified"])
        self.assertFalse(data["operating_db_modified"])
        self.assertFalse(data["other_tasks_read"])
        self.assertFalse(data["task_modify_permission_proven"])
        self.assertFalse(data["original_mutation_error_hresult_known"])
        print("UCIE_OWNER_TASK_PERMISSION_READONLY=" +
              json.dumps(data, sort_keys=True, ensure_ascii=True))


if __name__ == "__main__":
    unittest.main()
