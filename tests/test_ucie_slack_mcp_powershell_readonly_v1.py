"""UCIE owner Windows PowerShell read-only diagnostics integration.

It invokes only the fixed PowerShell diagnosis modes Status and FreshImport:
no C40 restart, task change, mutating MCP handler, credential or Slack access.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "ucie_slack_mcp_power_shell_probe_v1.ps1"
HOST_FILE = Path(r"D:\UCIE_PREVIEW\UCIE_ADMIN\src\ucie_admin\mcp_registration.py")


class UCIEMCPPowershellOwnerReadOnly(unittest.TestCase):
    def test_static_powershell_contract(self):
        src=SCRIPT.read_text(encoding="utf-8")
        self.assertIn("Mode='Status'",src)
        self.assertIn("UCIE-C40-Recover",src)
        self.assertIn("Get-FileHash",src)
        self.assertIn("Get-ScheduledTask",src)
        self.assertIn("'FreshImport'",src)
        for forbidden in (
            "Stop-Process","Start-Process","Start-ScheduledTask",
            "Stop-ScheduledTask","Restart-Service","Stop-Service",
            "Set-ScheduledTask","Enable-ScheduledTask","Disable-ScheduledTask",
            "Register-ScheduledTask","Unregister-ScheduledTask",
            "Get-Credential","ConvertTo-SecureString","xoxb-",
            "D:\\OFFICE_AGENT","D:\\MYGAME",
        ):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden,src)

    def test_only_owner_host_readonly_powershell_diagnosis(self):
        if os.name!="nt" or not HOST_FILE.is_file():
            self.skipTest("UCIE owner stage not mounted")
        shell=shutil.which("powershell.exe")
        if shell is None:
            self.skipTest("Windows PowerShell unavailable")
        for mode in ("Status","FreshImport"):
            with self.subTest(mode=mode):
                child=subprocess.run(
                    [shell,"-NoProfile","-NonInteractive","-File",
                     str(SCRIPT),"-Mode",mode],
                    capture_output=True,text=True,errors="replace",
                    check=False,timeout=40,
                )
                # A blocked precondition remains a real failure, not a PASS.
                self.assertLess(len(child.stdout),4500)
                self.assertEqual(child.returncode,0,
                                 "UCIE_PS_READONLY_PROBE_FAILED")
                rows=child.stdout.strip().splitlines()
                self.assertEqual(len(rows),1)
                record=json.loads(rows[0])
                print("UCIE_MCP_PS_"+mode.upper()+"="+json.dumps(record,sort_keys=True))
                self.assertEqual(record["schema"],
                                 "UCIE_C40_MCP_READONLY_POWER_SHELL_DIAGNOSTIC_V1")
                self.assertTrue(record["registration_sha256_matches"])
                self.assertTrue(record["new_reader_sha256_matches"])
                self.assertTrue(record["task_running_highest_interactive"])
                self.assertFalse(record["service_or_client_restarted"])
                self.assertFalse(record["operating_database_modified"])
                self.assertFalse(record["slack_credentials_or_messages_read"])
                if mode=="FreshImport":
                    self.assertEqual(record["status"],
                                     "UCIE_FRESH_PROCESS_TEN_TOOLS_PASS")
                    self.assertEqual(record["fresh_admin_tools"],9)
                    self.assertEqual(record["fresh_extra_slack_tools"],1)


if __name__ == "__main__":
    unittest.main()
