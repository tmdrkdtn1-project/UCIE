"""UCIE C40 one-time safe MCP reload contract and owner-only Preview.

NO Apply in tests. Never intentionally stop/restart processes.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess
import unittest

SCRIPT=(Path(__file__).resolve().parents[1]/
        "scripts"/"ucie_c40_slack_mcp_reload_owner_once.ps1")
PROFILE=Path(r"D:\UCIE_DATA\mcp_tunnel_profiles\ucie-private-c40.yaml")


class C40SlackMCPReloadOwnerSafety(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.src=SCRIPT.read_text(encoding="utf-8")

    def test_default_readonly_and_explicit_apply(self):
        for text in (
            "[string]$Mode = 'Preview'",
            "[switch]$OwnerOnlyConfirmed",
            "UCIE_C40_MCP_RELOAD_PREVIEW_READY",
            "UCIE_C40_MCP_RELOAD_ONCE",
            "UCIE_C40_MCP_RELOAD_ELEVATED_OWNER_REQUIRED",
            "UCIE_C40_MCP_RELOAD_TASK_NOT_RUNNING_HIGHEST_INTERACTIVE",
            "UCIE_C40_MCP_RELOAD_PINNED_RUNTIME_FILE_CHANGED",
            "c40_slack_mcp_reload_once_v1.json",
            "FileMode]::CreateNew",
        ):
            self.assertIn(text,self.src)

    def test_no_duplicate_client_or_other_runtime_mutations(self):
        for forbidden in (
            "Start-Process","Start-ScheduledTask",
            "Register-ScheduledTask","Unregister-ScheduledTask",
            "Stop-ScheduledTask","Restart-Service",
            "Enable-ScheduledTask","Disable-ScheduledTask",
            "Set-ScheduledTask","Stop-Process",
            "Invoke-WebRequest","Invoke-RestMethod",
            "D:\\OFFICE_AGENT","D:\\MYGAME",
            "xoxb-",
        ):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden,self.src)
        self.assertEqual(self.src.count("$process.Kill()"),1)
        self.assertIn("$process.WaitForExit(5000)",self.src)
        self.assertIn("Assert-Ready",self.src)
        self.assertIn("UCIE_C40_MCP_RELOAD_PROCESS_CHANGED_AFTER_APPROVAL",self.src)
        self.assertIn("UCIE_C40_MCP_RELOAD_CLIENT_RETURNED_WITHOUT_ATTRIBUTED_RESTART_RECEIPT",self.src)
        self.assertIn("UCIE_C40_MCP_RELOAD_AUTO_RESTART_NOT_PROVEN_USE_OWNER_MANUAL_RECOVERY",self.src)
        self.assertIn("new_mcp_tool_discovery_verified = $false",self.src)
        self.assertIn("restored_by_existing_supervisor = $true",self.src)

    def test_exact_ucie_source_pins(self):
        for pinned in (
            "UCIE-C40-Recover",
            "ucie-private-c40.yaml",
            "tunnel-client-v0.0.16",
            "ucie_c40_recover.ps1",
            "f75a9780bbf745b547af8a6d7ca830269aa3ebffb25cef690724d0ffe4184962",
            "92e273f93495bd2e0c0c6b4da70e70cc1c0406a81c1ce70b7ac169edce7f08ac",
            "83b58b68ad0c15a32991e03e82b3c309a5e045da1d4c9a4c8ca3101d8b010d8e",
        ):
            with self.subTest(pin=pinned[:20]):
                self.assertIn(pinned,self.src)

    def test_owner_powershell_parse(self):
        shell=shutil.which("powershell.exe") or shutil.which("pwsh")
        if not shell: self.skipTest("PowerShell unavailable")
        source=str(SCRIPT).replace("'","''")
        command=("$t=$null;$e=$null;"
                 f"[void][System.Management.Automation.Language.Parser]::ParseFile('{source}',[ref]$t,[ref]$e);"
                 "if($e.Count){$e|%{$_.Message};exit 2}")
        p=subprocess.run([shell,"-NoProfile","-NonInteractive","-Command",command],
              capture_output=True,text=True,errors="replace",timeout=20,check=False)
        self.assertEqual(p.returncode,0,p.stdout+p.stderr)

    def test_owner_host_preview_one_only(self):
        if os.name!="nt" or not PROFILE.is_file():
            self.skipTest("UCIE owner Windows host only")
        shell=shutil.which("powershell.exe")
        if not shell: self.skipTest("PowerShell unavailable")
        p=subprocess.run(
            [shell,"-NoProfile","-NonInteractive","-File",str(SCRIPT),
             "-Mode","Preview"],
            capture_output=True,text=True,errors="replace",timeout=30,
            check=False)
        self.assertEqual(p.returncode,0,
                         "UCIE_C40_MCP_RELOAD_PREVIEW_BLOCKED "+p.stderr[:400])
        items=p.stdout.strip().splitlines()
        self.assertEqual(len(items),1)
        d=json.loads(items[0])
        print("UCIE_C40_MCP_RELOAD_SAFE_PREVIEW="+json.dumps(d,sort_keys=True))
        self.assertEqual(d["status"],"UCIE_C40_MCP_RELOAD_PREVIEW_READY")
        self.assertEqual(d["client_count"],1)
        self.assertTrue(d["owner_and_source_verified"])
        self.assertFalse(d["task_modified"])
        self.assertFalse(d["client_modified"])
        self.assertFalse(d["operating_database_modified"])


if __name__=="__main__":
    unittest.main()
