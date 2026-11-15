"""UCIE-only task ACL evidence; never reads other tasks or mutates privileges.

Task principal (run-as account) is NOT equivalent to task file owner/DACL.
The matched ACE counts below are diagnostic evidence, not an effective
access check: Windows deny-only token groups and TaskScheduler rules matter.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]
PS = r"""
$ErrorActionPreference='Stop'
$name='UCIE-PublicMiner-Hourly'
$task=Get-ScheduledTask -TaskPath '\' -TaskName $name -ErrorAction Stop
$identity=[Security.Principal.WindowsIdentity]::GetCurrent()
$principal=[Security.Principal.WindowsPrincipal]::new($identity)
$isAdmin=$principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
$tokenSids=New-Object 'System.Collections.Generic.HashSet[string]' ([StringComparer]::OrdinalIgnoreCase)
[void]$tokenSids.Add($identity.User.Value)
foreach ($g in $identity.Groups) { [void]$tokenSids.Add($g.Value) }
$file=Join-Path $env:SystemRoot 'System32\Tasks\UCIE-PublicMiner-Hourly'
$pathExists=Test-Path -LiteralPath $file -PathType Leaf
$fileAclReadable=$false
$fileOwnerMatches=$false
$fileAllowWriteAceCount=0
$fileDenyWriteAceCount=0
$fileAllowWriteDacCount=0
$fileDenyWriteDacCount=0
$fileAclErrorType=$null
try {
    $acl=Get-Acl -LiteralPath $file -ErrorAction Stop
    $fileAclReadable=$true
    try {
        $fileOwnerSid=([Security.Principal.NTAccount]::new([string]$acl.Owner)).Translate(
            [Security.Principal.SecurityIdentifier])
        $fileOwnerMatches=$fileOwnerSid.Equals($identity.User)
    } catch { $fileOwnerMatches=$false }
    $rules=$acl.GetAccessRules($true,$true,[Security.Principal.SecurityIdentifier])
    foreach ($rule in $rules) {
        if (-not $tokenSids.Contains($rule.IdentityReference.Value)) { continue }
        $mask=[int64]$rule.FileSystemRights
        $allowsFileWrite= (($mask -band 0x00000002) -ne 0) -or
            (($mask -band 0x40000000) -ne 0) -or
            (($mask -band 0x10000000) -ne 0)
        $allowsDaclWrite= (($mask -band 0x00040000) -ne 0) -or
            (($mask -band 0x10000000) -ne 0)
        if ([string]$rule.AccessControlType -eq 'Allow') {
            if ($allowsFileWrite) { $fileAllowWriteAceCount++ }
            if ($allowsDaclWrite) { $fileAllowWriteDacCount++ }
        } elseif ([string]$rule.AccessControlType -eq 'Deny') {
            if ($allowsFileWrite) { $fileDenyWriteAceCount++ }
            if ($allowsDaclWrite) { $fileDenyWriteDacCount++ }
        }
    }
} catch { $fileAclErrorType=$_.Exception.GetType().Name }
$comDescriptorReadable=$false
$taskDaclAllowAceCount=0
$taskDaclDenyAceCount=0
$comErrorType=$null
try {
    $svc=New-Object -ComObject Schedule.Service
    $svc.Connect()
    $registered=$svc.GetFolder('\').GetTask($name)
    $sddl=$registered.GetSecurityDescriptor(4)
    $raw=[Security.AccessControl.RawSecurityDescriptor]::new([string]$sddl)
    $comDescriptorReadable=($null -ne $raw.DiscretionaryAcl)
    if ($comDescriptorReadable) {
        foreach ($ace in $raw.DiscretionaryAcl) {
            if ($ace -isnot [Security.AccessControl.KnownAce]) { continue }
            if (-not $tokenSids.Contains($ace.SecurityIdentifier.Value)) { continue }
            if ([string]$ace.AceType -match 'AccessAllowed') {
                $taskDaclAllowAceCount++
            } elseif ([string]$ace.AceType -match 'AccessDenied') {
                $taskDaclDenyAceCount++
            }
        }
    }
} catch { $comErrorType=$_.Exception.GetType().Name }
$trigger=@($task.Triggers)
[pscustomobject]@{
 schema='UCIE_EXACT_OWNER_TASK_ACL_READONLY_V02'
 status='ACL_AND_TOKEN_EVIDENCE_ONLY_NO_GO'
 task_found=$true
 task_state=[string]$task.State
 interval=if($trigger.Count -eq 1){[string]$trigger[0].Repetition.Interval}else{'AMBIGUOUS'}
 process_is_elevated_admin=$isAdmin
 exact_task_file_exists=$pathExists
 task_file_acl_readable=$fileAclReadable
 task_file_owner_matches_process=$fileOwnerMatches
 matching_token_file_write_allow_ace_count=$fileAllowWriteAceCount
 matching_token_file_write_deny_ace_count=$fileDenyWriteAceCount
 matching_token_write_dacl_allow_ace_count=$fileAllowWriteDacCount
 matching_token_write_dacl_deny_ace_count=$fileDenyWriteDacCount
 task_com_dacl_readable=$comDescriptorReadable
 matching_token_task_com_dacl_allow_ace_count=$taskDaclAllowAceCount
 matching_token_task_com_dacl_deny_ace_count=$taskDaclDenyAceCount
 file_acl_error_type=$fileAclErrorType
 com_acl_error_type=$comErrorType
 effective_modify_permission_proven=$false
 task_modified=$false
 other_tasks_queried=$false
} | ConvertTo-Json -Compress
"""


class UCIEOwnerTaskACLDiagnosticTests(unittest.TestCase):
    def test_01_scope_is_exact_and_readonly(self):
        self.assertIn("UCIE-PublicMiner-Hourly", PS)
        self.assertIn("GetAccessRules", PS)
        self.assertIn("GetSecurityDescriptor(4)", PS)
        for verb in ("Set-ScheduledTask ", "SetSecurityDescriptor(",
                     "Unregister-ScheduledTask ", "Register-ScheduledTask ",
                     "Remove-Item ", "Start-ScheduledTask ",
                     "Stop-ScheduledTask ", "icacls.exe "):
            self.assertNotIn(verb, PS)

    @unittest.skipUnless(os.name == "nt" and shutil.which("powershell.exe"),
                         "owner Windows PowerShell only")
    def test_02_owner_windows_exact_task_dacl(self):
        if (ROOT.resolve() != Path("D:/UCIE").resolve() or ROOT.is_symlink()
                or not (ROOT / ".git").is_dir()):
            self.skipTest("exact UCIE owner checkout not present")
        out = subprocess.run(
            ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", PS],
            capture_output=True, cwd=str(ROOT), timeout=30, check=False,
            env={"SystemRoot":os.environ.get("SystemRoot","C:\\Windows"),
                 "PATH":os.environ.get("PATH","")},
        )
        self.assertEqual(out.returncode, 0,
                         "read-only Windows task ACL inspection failed")
        self.assertLess(len(out.stdout), 4500)
        receipt = json.loads(out.stdout.decode("utf-8-sig","strict"))
        self.assertEqual(receipt["schema"],
                         "UCIE_EXACT_OWNER_TASK_ACL_READONLY_V02")
        self.assertFalse(receipt["task_modified"])
        self.assertFalse(receipt["other_tasks_queried"])
        self.assertFalse(receipt["effective_modify_permission_proven"])
        print("UCIE_EXACT_TASK_ACL_READONLY=" +
              json.dumps(receipt, sort_keys=True, ensure_ascii=True))


if __name__ == "__main__":
    unittest.main()
