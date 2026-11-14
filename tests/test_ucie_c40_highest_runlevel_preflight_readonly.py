"""UCIE-only in-memory C40 task principal preflight; no scheduler mutation.

No Set-ScheduledTask, Register-ScheduledTask or process operations.
"""
import json
import os
from pathlib import Path
import shutil
import subprocess
import unittest

PROFILE = Path(r"D:\UCIE_DATA\mcp_tunnel_profiles\ucie-private-c40.yaml")


class C40RunLevelInMemoryPreflight(unittest.TestCase):
    def test_owner_task_highest_candidate_without_registration(self):
        if os.name != "nt" or not PROFILE.is_file():
            self.skipTest("Not UCIE Windows owner host")
        shell = shutil.which("powershell.exe")
        if shell is None:
            self.skipTest("Windows PowerShell absent")
        program = r"""
$ErrorActionPreference = 'Stop'
$task = Get-ScheduledTask -TaskName 'UCIE-C40-Recover' -ErrorAction Stop
$existing = [string]$task.Principal.UserId
$current = [Security.Principal.WindowsIdentity]::GetCurrent()
function Resolve-Sid([string]$id) {
    if ($id -match '^S-1-[0-9]+(?:-[0-9]+)+$') { return $id }
    return ([Security.Principal.NTAccount]::new($id)).Translate(
        [Security.Principal.SecurityIdentifier]).Value
}
$taskOwnerIsCurrent = [string]::Equals(
    (Resolve-Sid $existing), $current.User.Value,
    [StringComparison]::OrdinalIgnoreCase)
$candidate = New-ScheduledTaskPrincipal -UserId $existing -LogonType Interactive -RunLevel Highest
$acts = @($task.Actions)
$correctAction = ($acts.Count -eq 1 -and
    ([string]$acts[0].Arguments).Contains('D:\UCIE\scripts\ucie_c40_recover.ps1') -and
    ([string]$acts[0].Arguments).Contains('-Mode Supervise') -and
    ([string]$acts[0].Arguments).Contains('-EnableAdminTools'))
$identity = New-Object Security.Principal.WindowsPrincipal($current)
[pscustomobject]@{
 schema='UCIE_C40_INMEMORY_RUNLEVEL_PREFLIGHT_V1'
 task_state=[string]$task.State
 existing_runlevel=[string]$task.Principal.RunLevel
 existing_logon=[string]$task.Principal.LogonType
 task_owner_matches_caller=[bool]$taskOwnerIsCurrent
 original_action_matches=[bool]$correctAction
 elevated_context_in_this_probe=[bool]$identity.IsInRole(
    [Security.Principal.WindowsBuiltInRole]::Administrator)
 candidate_runlevel=[string]$candidate.RunLevel
 candidate_logon=[string]$candidate.LogonType
 candidate_owner_matches_existing=([string]::Equals(
    [string]$candidate.UserId,$existing,[StringComparison]::OrdinalIgnoreCase))
 modified_registered_task=$false
 ran_client_process=$false
 changed_operating_db=$false
} | ConvertTo-Json -Compress
"""
        r=subprocess.run([shell,"-NoProfile","-NonInteractive","-Command",program],
                         capture_output=True,text=True,check=False,timeout=30)
        self.assertEqual(r.returncode,0,"UCIE-only in-memory preflight failed")
        row=json.loads(r.stdout.strip().splitlines()[-1])
        print("UCIE_C40_RUNLEVEL_PREFLIGHT="+json.dumps(row,sort_keys=True))
        self.assertEqual(row["schema"],"UCIE_C40_INMEMORY_RUNLEVEL_PREFLIGHT_V1")
        self.assertEqual(row["task_state"],"Disabled")
        self.assertTrue(row["task_owner_matches_caller"])
        self.assertTrue(row["original_action_matches"])
        self.assertTrue(row["candidate_owner_matches_existing"])
        self.assertEqual(row["candidate_runlevel"],"Highest")
        self.assertEqual(row["candidate_logon"],"Interactive")
        self.assertFalse(row["modified_registered_task"])
        self.assertFalse(row["ran_client_process"])
        self.assertFalse(row["changed_operating_db"])


if __name__=="__main__":
    unittest.main()
