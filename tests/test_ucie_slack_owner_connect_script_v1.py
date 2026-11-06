"""UCIE Slack owner PowerShell launcher fixed paths, only Preview is tested."""
from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess
import unittest

UCIE_ROOT=Path(r"D:\UCIE")
PROFILE=Path(r"D:\UCIE_DATA\mcp_tunnel_profiles\ucie-private-c40.yaml")
SCRIPT=Path(__file__).resolve().parents[1] / "scripts" / "ucie_slack_owner_connect.ps1"


class UCIENoSecretOwnerLauncherTests(unittest.TestCase):
    def test_static_fixed_paths_and_no_background_mutations(self):
        code=SCRIPT.read_text(encoding="utf-8")
        self.assertIn("[string]$Mode = 'Preview'",code)
        self.assertIn("PYTHONPATH = $src",code)
        self.assertIn("ucie_slack_windows_reader_v1",code)
        self.assertIn("UCIE_SLACK_OWNER_LAUNCHER_REPARSE_REJECTED",code)
        for banned in (
            "D:\\OFFICE_AGENT", "D:\\MYGAME", "D:\\UCIE_HUB",
            "Register-ScheduledTask", "Stop-Process", "Restart-Service",
            "Set-Acl", "Remove-Item", "Invoke-WebRequest",
            "xoxb-", "Start-ScheduledTask", "Set-ScheduledTask",
        ):
            self.assertNotIn(banned,code)

    def test_windows_powershell_syntax(self):
        shell=shutil.which("powershell.exe") or shutil.which("pwsh")
        if not shell:
            self.skipTest("PowerShell unavailable")
        file=str(SCRIPT).replace("'","''")
        expression=(
            "$t=$null;$e=$null;"
            f"[void][System.Management.Automation.Language.Parser]::ParseFile('{file}',[ref]$t,[ref]$e);"
            "if($e.Count -gt 0){throw 'UCIE_SLACK_OWNER_PS_PARSE_FAILED'}"
        )
        p=subprocess.run(
            [shell,"-NoProfile","-NonInteractive","-Command",expression],
            capture_output=True,text=True,errors="replace",timeout=25,check=False)
        self.assertEqual(p.returncode,0,"UCIE PowerShell launcher parse error")

    def test_owner_windows_preview_status_no_token_or_slack_http(self):
        if os.name!="nt" or not UCIE_ROOT.is_dir() or not PROFILE.is_file():
            self.skipTest("UCIE owner Windows host only")
        shell=shutil.which("powershell.exe")
        if not shell:
            self.skipTest("Windows PowerShell unavailable")
        p=subprocess.run([shell,"-NoProfile","-NonInteractive","-File",
                          str(SCRIPT),"-Mode","Preview"],
                         capture_output=True,text=True,errors="replace",
                         timeout=35,check=False)
        self.assertEqual(p.returncode,0,
                         "UCIE Slack Preview could not read fixed WinCred status")
        lines=p.stdout.strip().splitlines()
        self.assertTrue(lines)
        result=json.loads(lines[-1])
        self.assertEqual(result["schema"],
                         "UCIE_SLACK_WINDOWS_EVIDENCE_READER_V1")
        self.assertIn(result["status"],
                      ("UCIE_SLACK_TOKEN_PRESENT","UCIE_SLACK_TOKEN_NOT_ENROLLED"))
        self.assertFalse(result["remote_slack_call"])
        self.assertFalse(result["token_exposed"])
        print("UCIE_SLACK_OWNER_PREVIEW="+json.dumps(result,sort_keys=True))


if __name__=="__main__":
    unittest.main()
