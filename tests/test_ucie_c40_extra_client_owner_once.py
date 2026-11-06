"""UCIE-only one-off C40 cleanup regression tests.

Offline tests never invoke Apply, Stop-Process or any task mutation.
On UCIE owner Windows host only, Preview checks exact identities if elevated.
"""
from __future__ import annotations
import json
import os
from pathlib import Path
import shutil
import subprocess
import unittest

ROOT=Path(__file__).resolve().parents[1]
SCRIPT=ROOT/"scripts"/"ucie_c40_extra_client_owner_once.ps1"
PROFILE=Path(r"D:\UCIE_DATA\mcp_tunnel_profiles\ucie-private-c40.yaml")


class UCIEC40PinnedCleanupContract(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source=SCRIPT.read_text(encoding="utf-8")

    def test_readonly_by_default(self):
        self.assertIn("[string]$Mode='Preview'",self.source)
        self.assertIn("UCIE_C40_DUPLICATE_OWNER_PREVIEW_ONLY",self.source)
        self.assertIn("if ($Mode -eq 'Preview')",self.source)

    def test_exact_ucie_scope_and_historical_anchors(self):
        for string in (
            "UCIE-C40-Recover","-TaskPath '\\'","57016","53556",
            "D:\\UCIE_DATA\\tools\\tunnel-client-v0.0.16\\tunnel-client.exe",
            "2026-11-02T06:31:20.9199320Z",
            "2026-11-02T07:45:35.3567200Z",
            "ucie-private-c40.yaml",
            "UCIE_C40_PROCESS_START_TIME_MISMATCH",
            "UCIE_C40_CLIENT_CENSUS_NOT_EXACTLY_TWO",
        ):
            with self.subTest(string=string):
                self.assertIn(string,self.source)

    def test_only_one_exact_process_can_be_terminated(self):
        self.assertEqual(self.source.count("Stop-Process -Id $extraPid"),1)
        self.assertIn("$extraPid=53556",self.source)
        self.assertIn("$originalPid=57016",self.source)
        self.assertIn("UCIE_C40_EXTRA_CLIENT_STOPPED_ORIGINAL_PRESERVED",self.source)
        for forbidden in (
            "Start-Process","Enable-ScheduledTask","Start-ScheduledTask",
            "Stop-ScheduledTask","Set-ScheduledTask","Register-ScheduledTask",
            "Unregister-ScheduledTask","taskkill","Remove-Item",
            "Get-Process -Name","UCIE-PublicMiner-Hourly","UCIE-Internal-Minute"
        ):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden,self.source)

    def test_elevated_owner_and_disabled_task_preconditions(self):
        self.assertIn("UCIE_C40_ELEVATED_OWNER_REQUIRED",self.source)
        self.assertIn("UCIE_C40_RECOVERY_TASK_NOT_DISABLED_HIGHEST",self.source)
        self.assertIn("UCIE_C40_OWNER_SID_MISMATCH",self.source)
        self.assertIn("UCIE_C40_EXPLICIT_OWNER_SCOPE_REQUIRED",self.source)
        self.assertIn("if ($consent -cne 'STOP_UCIE_53556')",self.source)
        self.assertIn("UCIE_C40_CLIENT_CENSUS_NOT_EXACTLY_TWO",self.source)
        self.assertIn("UCIE_C40_TASK_CHANGED_AFTER_OWNER_CONSENT",self.source)
        self.assertIn("UCIE_C40_CLIENT_CENSUS_CHANGED_AFTER_OWNER_CONSENT",self.source)
        self.assertIn("Assert-C40Identity $originalPid $originalStart",self.source)
        self.assertIn("Assert-C40Identity $extraPid $extraStart",self.source)

    def test_parser(self):
        shell=shutil.which("pwsh") or shutil.which("powershell.exe")
        if not shell:
            self.skipTest("PowerShell absent")
        p=str(SCRIPT).replace("'","''")
        code=(
            "$t=$null;$e=$null;"
            f"[void][System.Management.Automation.Language.Parser]::ParseFile('{p}',[ref]$t,[ref]$e);"
            "if($e.Count){$e|% {$_.Message};exit 2}"
        )
        r=subprocess.run(
            [shell,"-NoProfile","-NonInteractive","-Command",code],
            capture_output=True,text=True,timeout=25,check=False)
        self.assertEqual(r.returncode,0,r.stdout+r.stderr)

    def test_live_ucie_owner_preview_only(self):
        if os.name!="nt" or not PROFILE.is_file():
            self.skipTest("not the exact UCIE owner host")
        shell=shutil.which("powershell.exe")
        if not shell:
            self.skipTest("Windows PowerShell absent")
        # Permission is observed; this test never elevates or changes permissions.
        probe=subprocess.run(
            [shell,"-NoProfile","-NonInteractive","-Command",
             "$id=[Security.Principal.WindowsIdentity]::GetCurrent();"
             "$p=New-Object Security.Principal.WindowsPrincipal($id);"
             "[bool]$p.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)"],
            capture_output=True,text=True,timeout=20,check=False
        )
        self.assertEqual(probe.returncode,0,"UCIE preview privilege check error")
        if probe.stdout.strip().lower()!="true":
            self.skipTest("UCIE MCP host test call is not elevated; elevated owner Preview needed")
        r=subprocess.run(
            [shell,"-NoProfile","-NonInteractive","-File",str(SCRIPT),"-Mode","Preview"],
            capture_output=True,text=True,timeout=35,check=False)
        self.assertEqual(r.returncode,0,"UCIE preview failed closed: "+r.stderr[:250])
        d=json.loads(r.stdout.strip().splitlines()[-1])
        print("UCIE_C40_CLEANUP_PREVIEW="+json.dumps(d,sort_keys=True))
        self.assertEqual(d["status"],"UCIE_C40_DUPLICATE_OWNER_PREVIEW_ONLY")
        self.assertEqual(d["original_pid"],57016)
        self.assertEqual(d["extra_pid"],53556)
        self.assertTrue(d["original_verified"])
        self.assertTrue(d["extra_verified"])
        self.assertFalse(d["stopped_process"])
        self.assertEqual(d["task_state"],"Disabled")
        self.assertEqual(d["task_runlevel"],"Highest")


if __name__=="__main__":
    unittest.main()
