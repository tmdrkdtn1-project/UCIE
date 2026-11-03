"""Read-only, privacy-bounded UCIE-only Windows ACL root-cause classification.

Reports safe category counts, never account names, raw SIDs, security
descriptors, credentials or non-UCIE filenames. No ACL/process/task writes.
"""
from __future__ import annotations
import json
import os
from pathlib import Path
import shutil
import subprocess
import unittest

UCIE_PROFILE=Path(r"D:\UCIE_DATA\mcp_tunnel_profiles\ucie-private-c40.yaml")

PS=r'''
$ErrorActionPreference='Stop'
$owner=[Security.Principal.WindowsIdentity]::GetCurrent().User.Value
$admin='S-1-5-32-544'
$system='S-1-5-18'
$trusted=@($owner,$admin,$system)
$broad=@('S-1-1-0','S-1-5-11','S-1-5-32-545','S-1-5-7')
$targets=@(
  @{label='UCIE_HUB';path='D:\UCIE_HUB'},
  @{label='UCIE_MIGRATION';path='D:\UCIE_HUB\04_MIGRATION'},
  @{label='UCIE_ROOT';path='D:\UCIE'},
  @{label='UCIE_DATA';path='D:\UCIE_DATA'},
  @{label='UCIE_BACKUPS';path='D:\UCIE_BACKUPS'}
)
$mask=([Security.AccessControl.FileSystemRights]::Write -bor
    [Security.AccessControl.FileSystemRights]::Modify -bor
    [Security.AccessControl.FileSystemRights]::FullControl -bor
    [Security.AccessControl.FileSystemRights]::Delete -bor
    [Security.AccessControl.FileSystemRights]::ChangePermissions -bor
    [Security.AccessControl.FileSystemRights]::TakeOwnership)
$rows=@()
foreach($target in $targets){
    $exists=Test-Path -LiteralPath $target.path -PathType Container
    $labels=@()
    $ownerSafe=$false
    $isReparse=$false
    if($exists){
        $item=Get-Item -LiteralPath $target.path -ErrorAction Stop
        $isReparse=(($item.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0)
        if(-not $isReparse){
            $acl=Get-Acl -LiteralPath $target.path -ErrorAction Stop
            $sid=''
            try {
                $sid=([Security.Principal.NTAccount]::new([string]$acl.Owner)).Translate(
                    [Security.Principal.SecurityIdentifier]).Value
            } catch {
                if([string]$acl.Owner -match '^S-1-'){$sid=[string]$acl.Owner}
            }
            $ownerSafe=($sid -in $trusted)
            foreach($ace in @($acl.Access)){
                if([string]$ace.AccessControlType -ne 'Allow'){continue}
                if(([int64]$ace.FileSystemRights -band [int64]$mask) -eq 0){continue}
                $sid=''
                try{$sid=$ace.IdentityReference.Translate(
                    [Security.Principal.SecurityIdentifier]).Value} catch {}
                if($sid -in $trusted){continue}
                if($sid -in $broad){$labels+= 'BROAD_WRITE';continue}
                if($sid -eq 'S-1-3-0'){
                    if(([int]$ace.PropagationFlags -band
                        [int][Security.AccessControl.PropagationFlags]::InheritOnly) -ne 0){
                        $labels+= 'CREATOR_OWNER_INHERIT_ONLY'
                    } else {
                        $labels+= 'CREATOR_OWNER_WRITE'
                    }
                    continue
                }
                if(-not $sid){$labels+= 'UNRESOLVED_WRITE';continue}
                $labels+= 'OTHER_WRITE'
            }
        }
    }
    $rows+=[pscustomobject]@{
        label=$target.label
        exists=[bool]$exists
        reparse=[bool]$isReparse
        owner_is_current_or_admin_or_system=[bool]$ownerSafe
        broad_writer_count=@($labels|Where-Object {$_ -eq 'BROAD_WRITE'}).Count
        creator_owner_inherit_only_count=@($labels|Where-Object {$_ -eq 'CREATOR_OWNER_INHERIT_ONLY'}).Count
        creator_owner_direct_write_count=@($labels|Where-Object {$_ -eq 'CREATOR_OWNER_WRITE'}).Count
        other_writer_count=@($labels|Where-Object {$_ -eq 'OTHER_WRITE'}).Count
        unresolved_writer_count=@($labels|Where-Object {$_ -eq 'UNRESOLVED_WRITE'}).Count
        credentials_or_raw_sids_emitted=$false
    }
}
[pscustomobject]@{
 schema='UCIE_OWNER_SCOPE_PARENT_ACL_CLASSES_READONLY_V1'
 candidates=$rows
 modified_acl=$false
 modified_any_file=$false
 inspected_other_projects=$false
} | ConvertTo-Json -Depth 5 -Compress
'''


class UCIEOwnerScopeParentACLReadonly(unittest.TestCase):
    def test_no_mutation_in_exact_scope_probe(self):
        for banned in (
            "Set-Acl", "New-Item", "Remove-Item", "Start-Process",
            "Stop-Process", "Register-ScheduledTask", "Set-ScheduledTask",
            "ICACLS", "takeown", "D:\\OFFICE_AGENT", "D:\\MYGAME"
        ):
            self.assertNotIn(banned, PS)
        self.assertIn("UCIE_MIGRATION", PS)
        self.assertIn("CREATOR_OWNER_INHERIT_ONLY", PS)

    def test_real_owner_ucie_host_acl_classes_observation_only(self):
        if os.name!="nt" or not UCIE_PROFILE.is_file():
            self.skipTest("Not UCIE owner Windows host")
        shell=shutil.which("powershell.exe")
        if not shell:
            self.skipTest("Windows PowerShell unavailable")
        r=subprocess.run(
            [shell,"-NoProfile","-NonInteractive","-Command",PS],
            text=True,errors="replace",capture_output=True,timeout=35,check=False
        )
        self.assertEqual(r.returncode,0,"UCIE ACL class probe failed without changes")
        lines=r.stdout.strip().splitlines()
        self.assertTrue(lines, "UCIE ACL class report missing")
        row=json.loads(lines[-1])
        self.assertEqual(row["schema"],"UCIE_OWNER_SCOPE_PARENT_ACL_CLASSES_READONLY_V1")
        self.assertEqual([x["label"] for x in row["candidates"]],
                         ["UCIE_HUB","UCIE_MIGRATION","UCIE_ROOT",
                          "UCIE_DATA","UCIE_BACKUPS"])
        self.assertFalse(row["modified_acl"])
        self.assertFalse(row["modified_any_file"])
        self.assertFalse(row["inspected_other_projects"])
        for item in row["candidates"]:
            self.assertFalse(item["credentials_or_raw_sids_emitted"])
            for key in (
                "broad_writer_count","creator_owner_inherit_only_count",
                "creator_owner_direct_write_count","other_writer_count",
                "unresolved_writer_count"
            ):
                self.assertIsInstance(item[key],int)
                self.assertGreaterEqual(item[key],0)
        print("UCIE_OWNER_SCOPE_PARENT_ACL_CATEGORIES="+json.dumps(row,sort_keys=True))


if __name__=="__main__":
    unittest.main()
