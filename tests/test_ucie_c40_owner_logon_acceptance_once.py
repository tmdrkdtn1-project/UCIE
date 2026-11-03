"""UCIE-only real owner logon acceptance preflight; never logs off, mutates task or stops client."""
from pathlib import Path
import json
import os
import shutil
import subprocess
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "ucie_c40_owner_logon_acceptance_once.ps1"
PROFILE = Path(r"D:\UCIE_DATA\mcp_tunnel_profiles\ucie-private-c40.yaml")


class OwnerLogonProbeContract(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.code = SCRIPT.read_text(encoding="utf-8")

    def test_preview_is_default_and_owner_only_marker(self):
        for snippet in (
            "[string]$Mode='Preview'",
            "'Prepare'","'Verify'",
            "UCIE_C40_OWNER_LOGON_PREVIEW_ONLY",
            "UCIE_C40_OWNER_LOGON_PREPARED",
            "UCIE_C40_OWNER_LOGON_RESTART_HOST_VERIFIED",
            "OwnerSignedOutAndBackInConfirmed",
            "[IO.FileMode]::CreateNew",
            "UCIE_C40_LOGON_ALREADY_PREPARED",
        ):
            self.assertIn(snippet,self.code)

    def test_only_pinned_existing_ucie_c40_used(self):
        for snippet in (
            "23dcb08524b32c611b43c1136a444286d7dc776598a739a7152a651a5244e66f",
            "D:\\UCIE\\scripts\\ucie_c40_recover.ps1",
            "D:\\UCIE\\.ucie_bridge_state",
            "UCIE-C40-Recover",
            ". $source -Mode Status -EnableAdminTools",
            "Assert-ApprovedRecoveryTask",
            "Find-C40",
            "UCIE_C40_LOGON_CLIENT_IDENTITY_MISMATCH",
            "UCIE_C40_LOGON_FRESH_TASK_AND_CLIENT_NOT_PROVEN",
        ):
            self.assertIn(snippet,self.code)

    def test_no_logoff_or_process_scheduler_mutation(self):
        import re
        forbidden = (
            r"\b(?:shutdown|logoff|Restart-Computer|Stop-Process|Start-Process|"
            r"Stop-ScheduledTask|Start-ScheduledTask|Register-ScheduledTask|"
            r"Unregister-ScheduledTask|Enable-ScheduledTask|Disable-ScheduledTask"
            r"|Set-ScheduledTask)\s+"
        )
        self.assertIsNone(re.search(forbidden,self.code,re.I))
        self.assertNotIn("D:\\OFFICE_AGENT",self.code)
        self.assertNotIn("UCIE-PublicMiner-Hourly",self.code)
        self.assertNotIn("UCIE-Internal-Minute",self.code)

    def test_verify_requires_real_fresh_task_and_client_evidence(self):
        for expected in (
            "$currentTask -le $prepared",
            "$newCreated -le $prepared",
            "$newCreated -le $oldCreated",
            "$healthUtc -lt $prepared",
            "OwnerSignedOutAndBackInConfirmed",
            "mcp_reconnect_requires_independent_check=$true",
        ):
            self.assertIn(expected,self.code)

    def test_powershell_parser(self):
        shell=shutil.which("powershell.exe") or shutil.which("pwsh")
        if not shell:self.skipTest("no PowerShell")
        path=str(SCRIPT).replace("'","''")
        command=(
           "$t=$null;$e=$null;"
           f"[void][System.Management.Automation.Language.Parser]::ParseFile('{path}',[ref]$t,[ref]$e);"
           "if($e.Count -gt 0){throw 'UCIE_C40_LOGON_PARSE_FAILED'}"
        )
        p=subprocess.run(
           [shell,"-NoProfile","-NonInteractive","-Command",command],
           capture_output=True,text=True,errors="replace",timeout=30,check=False
        )
        self.assertEqual(p.returncode,0,p.stdout+p.stderr)

    def test_real_ucie_owner_host_preview_only(self):
        if os.name!="nt" or not PROFILE.is_file():
            self.skipTest("not owner Windows host")
        shell=shutil.which("powershell.exe")
        if not shell:self.skipTest("no Windows PowerShell")
        p=subprocess.run(
           [shell,"-NoProfile","-NonInteractive","-File",str(SCRIPT),"-Mode","Preview"],
           capture_output=True,text=True,errors="replace",timeout=40,check=False
        )
        self.assertEqual(p.returncode,0,"UCIE logon Preview failed: "+(p.stderr or "")[:700])
        lines=p.stdout.strip().splitlines()
        self.assertTrue(lines)
        row=json.loads(lines[-1])
        print("UCIE_C40_LOGON_PREVIEW="+json.dumps(row,sort_keys=True))
        self.assertEqual(row["status"],"UCIE_C40_OWNER_LOGON_PREVIEW_ONLY")
        self.assertTrue(row["task_running_highest_owner"])
        self.assertTrue(row["task_logon_trigger_present"])
        self.assertEqual(row["exact_client_count"],1)
        self.assertFalse(row["task_or_process_modified"])


if __name__=="__main__":
    unittest.main()
