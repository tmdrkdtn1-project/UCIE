"""UCIE C40 only, owner-controlled activation contract and read-only preview.

The test never calls Apply, starts scheduled tasks, or terminates processes.
"""
from __future__ import annotations
import json
import os
from pathlib import Path
import shutil
import subprocess
import unittest

SCRIPT=Path(__file__).resolve().parents[1]/"scripts"/"ucie_c40_activate_owner_once.ps1"
PROFILE=Path(r"D:\UCIE_DATA\mcp_tunnel_profiles\ucie-private-c40.yaml")


class UCIEC40ActivationOneShotTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source=SCRIPT.read_text(encoding="utf-8")

    def test_preview_default_and_fixed_task_name(self):
        s=self.source
        self.assertIn("[string]$Mode='Preview'",s)
        self.assertIn("$name='UCIE-C40-Recover'",s)
        self.assertIn("$path='\\'",s)
        self.assertIn("UCIE_C40_ACTIVATION_PREVIEW_ONLY",s)
        self.assertIn("task_modified=$false",s)

    def test_exact_original_client_and_pinned_script(self):
        s=self.source
        self.assertIn("$ownerPid=57016",s)
        self.assertIn("2026-11-02T06:31:20.9199320Z",s)
        self.assertIn("D:\\UCIE_DATA\\tools\\tunnel-client-v0.0.16\\tunnel-client.exe",s)
        self.assertIn("D:\\UCIE\\scripts\\ucie_c40_recover.ps1",s)
        self.assertIn("23dcb08524b32c611b43c1136a444286d7dc776598a739a7152a651a5244e66f",s)
        self.assertIn("UCIE_C40_ACTIVATION_SOURCE_SHA_MISMATCH",s)
        self.assertIn("UCIE_C40_ACTIVATION_CLIENT_COUNT_NOT_ONE",s)
        self.assertIn("UCIE_C40_ACTIVATION_CLIENT_START_TIME_MISMATCH",s)

    def test_exact_owner_and_task_state(self):
        s=self.source
        self.assertIn("Get-ScheduledTask -TaskPath $path -TaskName $name",s)
        self.assertIn("UCIE_C40_ACTIVATION_TASK_NOT_DISABLED",s)
        self.assertIn("UCIE_C40_ACTIVATION_OWNER_TASK_NOT_HIGHEST_INTERACTIVE",s)
        self.assertIn("UCIE_C40_ACTIVATION_OWNER_SID_MISMATCH",s)
        self.assertIn("UCIE_C40_ACTIVATION_ELEVATED_OWNER_REQUIRED",s)
        self.assertIn("UCIE_C40_ACTIVATION_ACTION_MISMATCH",s)

    def test_explicit_owner_consent_and_no_process_control(self):
        s=self.source
        self.assertIn("if (-not $OwnerOnlyConfirmed)",s)
        self.assertIn("$approval=Read-Host",s)
        self.assertIn("if ($approval -cne 'APPROVE')",s)
        for not_allowed in (
            "Stop-Process","Start-Process","taskkill","Register-ScheduledTask",
            "Unregister-ScheduledTask","Set-ScheduledTask","UCIE-PublicMiner-Hourly",
            "UCIE-Internal-Minute", "New-Service", "Stop-Service",
        ):
            with self.subTest(not_allowed=not_allowed):
                self.assertNotIn(not_allowed,s)

    def test_first_cycle_and_disabled_on_error(self):
        s=self.source
        self.assertIn("Enable-ScheduledTask -TaskPath $path -TaskName $name",s)
        self.assertIn("Start-ScheduledTask -TaskPath $path -TaskName $name",s)
        self.assertIn("Stop-ScheduledTask -TaskPath $path -TaskName $name",s)
        self.assertIn("Disable-ScheduledTask -TaskPath $path -TaskName $name",s)
        self.assertIn("UCIE_C40_ACTIVATION_FAILED_TASK_DISABLED",s)
        self.assertIn("UCIE_C40_ACTIVATION_ROLLBACK_FAILED_OWNER_REVIEW",s)
        self.assertIn("c40_supervisor_health_v1.json",s)
        self.assertIn("UCIE_C40_ALREADY_RUNNING",s)
        self.assertIn("UCIE_C40_FIRST_CYCLE_RUNNING_ONE_CLIENT",s)
        self.assertIn("next_cycle_and_logon_validation_pending=$true",s)

    def test_powershell_parser(self):
        shell=shutil.which("pwsh") or shutil.which("powershell.exe")
        if not shell:
            self.skipTest("PowerShell not available")
        path=str(SCRIPT).replace("'","''")
        statement=(
            "$t=$null;$e=$null;"
            f"[void][System.Management.Automation.Language.Parser]::ParseFile('{path}',[ref]$t,[ref]$e);"
            "if($e.Count){$e|%{$_.Message};exit 2}"
        )
        out=subprocess.run([shell,"-NoProfile","-NonInteractive","-Command",statement],
                           capture_output=True,text=True,timeout=25,check=False)
        self.assertEqual(out.returncode,0,out.stdout+out.stderr)

    def test_owner_host_readonly_preview_when_elevated(self):
        if os.name!="nt" or not PROFILE.is_file():
            self.skipTest("Not UCIE owner Windows host")
        shell=shutil.which("powershell.exe")
        if shell is None:
            self.skipTest("Windows PowerShell missing")
        probe=subprocess.run(
            [shell,"-NoProfile","-NonInteractive","-Command",
             "$i=[Security.Principal.WindowsIdentity]::GetCurrent();"
             "$p=New-Object Security.Principal.WindowsPrincipal($i);"
             "[bool]$p.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)"],
            text=True,capture_output=True,check=False,timeout=20)
        self.assertEqual(probe.returncode,0,"UCIE owner privilege check failed")
        if probe.stdout.strip().lower()!="true":
            self.skipTest("UCIE owner test session not elevated")
        result=subprocess.run([shell,"-NoProfile","-NonInteractive",
                               "-File",str(SCRIPT),"-Mode","Preview"],
                              text=True,capture_output=True,timeout=30,check=False)
        self.assertEqual(result.returncode,0,"Read-only UCIE preview failed")
        d=json.loads(result.stdout.strip().splitlines()[-1])
        print("UCIE_C40_ACTIVATION_PREFLIGHT="+json.dumps(d,sort_keys=True))
        self.assertEqual(d["status"],"UCIE_C40_ACTIVATION_PREVIEW_ONLY")
        self.assertEqual(d["task_state"],"Disabled")
        self.assertEqual(d["task_runlevel"],"Highest")
        self.assertEqual(d["original_client_count"],1)
        self.assertEqual(d["original_client_pid"],57016)
        self.assertTrue(d["guarded_script_sha_matches"])
        for field in ("task_modified","client_modified","other_tasks_modified","operating_db_modified"):
            self.assertFalse(d[field])


if __name__=="__main__":
    unittest.main()
