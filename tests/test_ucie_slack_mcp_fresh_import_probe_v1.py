"""UCIE-only fresh MCP tool-list diagnostics, no live C40 modifications."""
from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import unittest

ROOT=Path(__file__).resolve().parents[1]
PYTHON_SCRIPT=ROOT/"scripts"/"ucie_slack_mcp_fresh_import_probe_v1.py"
PS_SCRIPT=ROOT/"scripts"/"ucie_slack_mcp_power_shell_probe_v1.ps1"
MCP_PY=Path(r"D:\UCIE_DATA\.venv_mcp\Scripts\python.exe")
REG=Path(r"D:\UCIE_PREVIEW\UCIE_ADMIN\src\ucie_admin\mcp_registration.py")


class UCIESlackMCPFreshImportReadOnly(unittest.TestCase):
    def test_powershell_is_readonly_fixed_scope(self):
        s=PS_SCRIPT.read_text(encoding="utf-8")
        self.assertIn("[string]$Mode='Status'",s)
        self.assertIn("UCIE-C40-Recover",s)
        self.assertIn("Get-FileHash",s)
        self.assertIn("Get-ScheduledTask",s)
        self.assertIn("ucie_slack_mcp_fresh_import_probe_v1.py",s)
        for forbidden in ("Stop-Process", "Start-Process", "Start-ScheduledTask",
            "Stop-ScheduledTask","Restart-Service","Register-ScheduledTask",
            "Remove-Item","Set-Acl","xoxb-", "D:\\OFFICE_AGENT","D:\\MYGAME"):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden,s)

    def test_python_probe_does_not_call_slack_or_tools(self):
        s=PYTHON_SCRIPT.read_text(encoding="utf-8")
        self.assertIn("FakeFastMCP",s)
        self.assertIn("registered_handler_invoked",s)
        self.assertNotIn("subprocess",s)
        self.assertNotIn("requests",s)
        self.assertNotIn("CredReadW",s)
        self.assertNotIn("getpass",s)
        self.assertNotIn("urllib",s)
        self.assertNotIn("Start-Process",s)

    def test_owner_windows_fresh_mcp_interpreter_import(self):
        if os.name!="nt" or not REG.is_file() or not MCP_PY.is_file():
            self.skipTest("Exact UCIE owner Windows MCP stage unavailable")
        # A bounded child process in the trusted fixed UCIE MCP venv. No
        # environment markers, tokens, Slack API, registration or C40 startup.
        try:
            child=subprocess.run(
                [str(MCP_PY),"-B",str(PYTHON_SCRIPT)],
                capture_output=True,text=True,errors="replace",
                check=False,timeout=30)
        except (OSError, subprocess.SubprocessError) as exc:
            self.fail("UCIE_MCP_PINNED_PYTHON_NOT_AVAILABLE")
        self.assertLess(len(child.stdout),5000)
        self.assertEqual(len(child.stdout.strip().splitlines()),1)
        record=json.loads(child.stdout.strip())
        print("UCIE_MCP_FRESH_IMPORT_DIAGNOSTIC="+json.dumps(record,sort_keys=True))
        self.assertEqual(record["schema"],"UCIE_MCP_FRESH_REGISTRATION_IMPORT_V1")
        self.assertEqual(child.returncode,0,record.get("block_code","UCIE_MCP_PROBE_FAILED"))
        self.assertEqual(record["status"],"UCIE_FRESH_PROCESS_TEN_TOOLS_PASS")
        self.assertTrue(record["new_slack_tool_registered_in_fresh_python"])
        self.assertFalse(record["actual_running_c40_tools_list_verified"])
        self.assertFalse(record["slack_token_or_message_read"])
        self.assertFalse(record["c40_or_task_modified"])


if __name__ == "__main__":
    unittest.main()
