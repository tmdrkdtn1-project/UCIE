"""UCIE-only owner scope ACL bootstrap preview/guard tests.

Never calls Apply, creates scope dirs, modifies permissions or logs off.
Windows host Preview is observation only; readiness may be NO_GO.
"""
import json
import os
from pathlib import Path
import shutil
import subprocess
import unittest

SCRIPT=Path(__file__).resolve().parents[1] / "scripts" / "ucie_owner_scope_acl_bootstrap_once.ps1"
PROFILE=Path(r"D:\UCIE_DATA\mcp_tunnel_profiles\ucie-private-c40.yaml")


class OwnerScopeACLBootstrapV1(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.code=SCRIPT.read_text(encoding="utf-8")

    def test_inert_preview_and_local_once_confirmation(self):
        for part in (
            "[string]$Mode = 'Preview'",
            "[switch]$OwnerOnlyConfirmed",
            "UCIE_OWNER_SCOPE_ACL_PREVIEW_ONLY",
            "UCIE_OWNER_SCOPE_ACL_ONLY",
            "UCIE_OWNER_ACL_OWNER_CONFIRM_REQUIRED",
            "UCIE_OWNER_ACL_CONFIRMATION_REJECTED",
            "UCIE_OWNER_ACL_SCOPE_ALREADY_EXISTS",
        ):
            self.assertIn(part,self.code)

    def test_ucie_only_paths_no_unrelated_changes(self):
        for part in (
            r"D:\UCIE_HUB\04_MIGRATION\UCIE_OWNER_SCOPED_QA_V1",
            "UCIE-C40-Recover",
            "[string][char]92",
            "UCIE_OWNER_ACL_PRINCIPAL_MISMATCH",
            "UCIE_OWNER_ACL_UNTRUSTED_WRITE_PRINCIPAL",
            "UCIE_OWNER_ACL_UNRESOLVED_WRITE_PRINCIPAL",
            "DirectorySecurity",
            "[IO.Directory]::CreateDirectory($target,$security)",
        ):
            self.assertIn(part,self.code)
        for forbidden in (
            "D:\\OFFICE_AGENT", "D:\\MYGAME", "UCIE-PublicMiner-Hourly",
            "Stop-Process", "Start-Process", "Start-ScheduledTask",
            "Register-ScheduledTask", "Enable-ScheduledTask",
            "Set-ScheduledTask", "Set-Acl", "Remove-Item", "Unregister-ScheduledTask",
        ):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden,self.code)

    def test_never_auto_enroll_or_register_mcp(self):
        self.assertIn("grant_created=$false",self.code)
        self.assertIn("owner_authenticated_mcp_tools_registered=$false",self.code)
        self.assertIn("UCIE_OWNER_ACL_PREVIEW_NOT_READY",self.code)
        self.assertNotIn("AUTHORIZE_UCIE_SCOPED_DEV_QA_ONLY",self.code)

    def test_powershell_parser(self):
        shell=shutil.which("powershell.exe") or shutil.which("pwsh")
        if not shell:self.skipTest("PowerShell unavailable")
        path=str(SCRIPT).replace("'","''")
        command=(
            "$t=$null;$e=$null;"
            f"[void][System.Management.Automation.Language.Parser]::ParseFile('{path}',[ref]$t,[ref]$e);"
            "if($e.Count -gt 0){throw 'UCIE_SCOPE_ACL_PARSE_FAILED'}"
        )
        p=subprocess.run([shell,"-NoProfile","-NonInteractive","-Command",command],
            capture_output=True,text=True,errors="replace",timeout=25,check=False)
        self.assertEqual(p.returncode,0,p.stdout+p.stderr)

    def test_windows_acl_creation_api_simulated_in_memory_only(self):
        if os.name!="nt":
            self.skipTest("Windows .NET Framework ACL constructors only")
        shell=shutil.which("powershell.exe")
        if not shell:
            self.skipTest("Windows PowerShell unavailable")
        ps=r"""
$ErrorActionPreference='Stop'
$id=[Security.Principal.SecurityIdentifier]::new('S-1-5-32-544')
$acl=New-Object System.Security.AccessControl.DirectorySecurity
$acl.SetAccessRuleProtection($true,$false)
$acl.SetOwner($id)
$flags=([Security.AccessControl.InheritanceFlags]::ContainerInherit -bor
    [Security.AccessControl.InheritanceFlags]::ObjectInherit)
$rule=[Security.AccessControl.FileSystemAccessRule]::new(
    $id,[Security.AccessControl.FileSystemRights]::FullControl,$flags,
    [Security.AccessControl.PropagationFlags]::None,
    [Security.AccessControl.AccessControlType]::Allow)
$acl.AddAccessRule($rule)
$twoArgs=@([IO.Directory].GetMethods() | Where-Object {
    $_.Name -eq 'CreateDirectory' -and
    $_.GetParameters().Count -eq 2 -and
    $_.GetParameters()[1].ParameterType.FullName -eq
      'System.Security.AccessControl.DirectorySecurity'
})
[pscustomobject]@{
 schema='UCIE_OWNER_ACL_INMEMORY_API_SIM_V1'
 directory_security_created=($null -ne $acl)
 rule_created=($null -ne $rule)
 create_directory_explicit_acl_overload=($twoArgs.Count -gt 0)
 filesystem_modified=$false
} | ConvertTo-Json -Compress
"""
        r=subprocess.run(
            [shell,"-NoProfile","-NonInteractive","-Command",ps],
            capture_output=True,text=True,errors="replace",timeout=25,check=False)
        self.assertEqual(r.returncode,0,"UCIE ACL in-memory .NET probe failed: "+
                         (r.stderr or "")[:600])
        row=json.loads(r.stdout.strip().splitlines()[-1])
        self.assertEqual(row["schema"],"UCIE_OWNER_ACL_INMEMORY_API_SIM_V1")
        self.assertTrue(row["directory_security_created"])
        self.assertTrue(row["rule_created"])
        self.assertTrue(row["create_directory_explicit_acl_overload"])
        self.assertFalse(row["filesystem_modified"])

    def test_live_ucie_owner_host_preview_no_mutations(self):
        if os.name!="nt" or not PROFILE.is_file():
            self.skipTest("not UCIE owner Windows host")
        shell=shutil.which("powershell.exe")
        if not shell:self.skipTest("Windows PowerShell absent")
        r=subprocess.run(
            [shell,"-NoProfile","-NonInteractive","-File",str(SCRIPT),"-Mode","Preview"],
            capture_output=True,text=True,errors="replace",timeout=30,check=False)
        self.assertEqual(r.returncode,0,"UCIE ACL Preview query failed: "+(r.stderr or "")[:700])
        lines=r.stdout.strip().splitlines()
        self.assertTrue(lines,"UCIE ACL Preview missing JSON")
        record=json.loads(lines[-1])
        print("UCIE_OWNER_SCOPE_ACL_BOOTSTRAP_PREVIEW="+json.dumps(record,sort_keys=True))
        self.assertEqual(record["schema"],"UCIE_OWNER_SCOPED_ACL_BOOTSTRAP_V1")
        self.assertEqual(record["status"],"UCIE_OWNER_SCOPE_ACL_PREVIEW_ONLY")
        self.assertIsInstance(record["ready_to_create"],bool)
        self.assertFalse(record["task_or_process_modified"])
        self.assertFalse(record["grant_created"])
        self.assertFalse(record["directory_created"])
        self.assertFalse(record["operating_db_modified"])


if __name__=="__main__":
    unittest.main()
