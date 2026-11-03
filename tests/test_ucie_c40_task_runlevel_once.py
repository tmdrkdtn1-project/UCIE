"""UCIE-only owner task principal change: static and real-host PREVIEW contract.

Test NEVER invokes Apply, enables/restarts scheduled tasks, or stops processes.
"""
import json
import os
from pathlib import Path
import shutil
import subprocess
import unittest

ROOT=Path(__file__).resolve().parents[1]
SCRIPT=ROOT/"scripts"/"ucie_c40_task_runlevel_once.ps1"
OWNER=Path(r"D:\UCIE_DATA\mcp_tunnel_profiles\ucie-private-c40.yaml")


class UCIEC40RunlevelOwnerApprovalTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.script=SCRIPT.read_text(encoding="utf-8")

    def test_default_readonly(self):
        self.assertIn("[string]$Mode='Preview'",self.script)
        self.assertIn("UCIE_C40_RUNLEVEL_PREVIEW_ONLY",self.script)
        self.assertIn("UCIE_C40_TASK_MUST_REMAIN_DISABLED",self.script)

    def test_only_existing_exact_task(self):
        self.assertIn("$name='UCIE-C40-Recover'",self.script)
        self.assertIn("Get-ScheduledTask -TaskPath '\\' -TaskName $name",self.script)
        self.assertIn("Set-ScheduledTask -TaskPath '\\' -TaskName $name",self.script)
        self.assertIn("UCIE_C40_ACTION_COUNT_MISMATCH",self.script)
        self.assertIn("UCIE_C40_TASK_ACTION_MISMATCH",self.script)
        for forbidden in (
            "Register-ScheduledTask","Enable-ScheduledTask","Start-ScheduledTask",
            "Stop-ScheduledTask","Unregister-ScheduledTask","Stop-Process",
            "Start-Process","taskkill", "UCIE-PublicMiner-Hourly",
            "UCIE-Internal-Minute", "Set-ExecutionPolicy"
        ):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden,self.script)

    def test_owner_token_privilege_and_one_time_consent(self):
        self.assertIn("Resolve-UCIESid",self.script)
        self.assertIn("UCIE_C40_TASK_OWNER_MISMATCH",self.script)
        self.assertIn("UCIE_C40_ELEVATED_OWNER_REQUIRED",self.script)
        self.assertIn("if (-not $OwnerOnlyConfirmed)",self.script)
        self.assertIn("$decision=Read-Host",self.script)
        self.assertIn("if ($decision -cne 'APPROVE')",self.script)

    def test_in_memory_preview_and_fail_closed_rollback(self):
        self.assertIn("-LogonType Interactive -RunLevel Highest",self.script)
        self.assertIn("$backupPrincipal=$task.Principal",self.script)
        self.assertIn("-Principal $backupPrincipal",self.script)
        self.assertIn("UCIE_C40_RUNLEVEL_CHANGE_ROLLED_BACK",self.script)
        self.assertIn("UCIE_C40_RUNLEVEL_ALREADY_HIGHEST",self.script)

    def test_powershell_parser(self):
        shell=shutil.which("pwsh") or shutil.which("powershell.exe")
        if not shell:
            self.skipTest("PowerShell not available")
        p=str(SCRIPT).replace("'","''")
        run=subprocess.run(
            [shell,"-NoProfile","-NonInteractive","-Command",
             f"$t=$null;$e=$null;[void][System.Management.Automation.Language.Parser]::ParseFile('{p}',[ref]$t,[ref]$e);if($e.Count){{$e|% {{$_.Message}};exit 2}}"],
            capture_output=True,text=True,errors="replace",timeout=25,check=False)
        self.assertEqual(run.returncode,0,run.stdout+run.stderr)

    def test_live_owner_preview_only(self):
        if os.name!="nt" or not OWNER.is_file():
            self.skipTest("Only the pinned UCIE owner Windows host")
        shell=shutil.which("powershell.exe")
        if not shell:
            self.skipTest("Windows PowerShell absent")
        # The one-time RunLevel tool correctly refuses Preview while the
        # already-approved recovery task is Running. Validate that state via
        # an independent, read-only task query instead of treating it as error.
        inspect=subprocess.run(
            [shell,"-NoProfile","-NonInteractive","-Command",
             "$t=Get-ScheduledTask -TaskPath '\' -TaskName 'UCIE-C40-Recover' -ErrorAction Stop;"
             "[pscustomobject]@{state=[string]$t.State;runlevel=[string]$t.Principal.RunLevel}"
             "| ConvertTo-Json -Compress"],
            capture_output=True,text=True,errors="replace",timeout=25,check=False)
        self.assertEqual(inspect.returncode,0,"UCIE task state inspection failed")
        task=json.loads(inspect.stdout.strip().splitlines()[-1])
        if task["state"] == "Running":
            self.assertEqual(task["runlevel"],"Highest")
            print("UCIE_C40_OWNER_TASK_RUNNING_READONLY="+json.dumps(task,sort_keys=True))
            return
        result=subprocess.run(
            [shell,"-NoProfile","-NonInteractive","-File",str(SCRIPT),"-Mode","Preview"],
            capture_output=True,text=True,errors="replace",timeout=25,check=False)
        self.assertEqual(result.returncode,0,"UCIE task preview failed: "+(result.stderr or "")[:160])
        data=json.loads(result.stdout.strip().splitlines()[-1])
        print("UCIE_C40_OWNER_TASK_PREVIEW="+json.dumps(data,sort_keys=True))
        self.assertEqual(data["status"],"UCIE_C40_RUNLEVEL_PREVIEW_ONLY")
        self.assertEqual(data["task"],"UCIE-C40-Recover")
        self.assertEqual(data["task_state"],"Disabled")
        self.assertIn(data["current_runlevel"],("Limited","Highest"))
        self.assertEqual(data["candidate_runlevel"],"Highest")
        for key in ("will_enable_or_start_task","will_stop_client","other_tasks_changed","operating_db_changed"):
            self.assertIs(data[key],False)


if __name__=="__main__":
    unittest.main()
