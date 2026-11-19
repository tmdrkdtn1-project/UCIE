"""Fail-closed UCIE-only real-loss drill contract and read-only owner preview.

Never invokes -Mode Apply; never stops processes or changes tasks.
"""
from __future__ import annotations
import json
import os
from pathlib import Path
import shutil
import subprocess
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "ucie_c40_owner_loss_drill_once.ps1"
PROFILE = Path(r"D:\UCIE_DATA\mcp_tunnel_profiles\ucie-private-c40.yaml")


class C40OwnerLossDrillContract(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.code = SCRIPT.read_text(encoding="utf-8")

    def test_default_preview_and_explicit_one_time_apply(self):
        code = self.code
        for expected in (
            "[string]$Mode = 'Preview'",
            "[switch]$OwnerOnlyConfirmed",
            "UCIE_C40_LOSS_DRILL_PREVIEW_ONLY",
            "UCIE_C40_DRILL_OWNER_SCOPE_REQUIRED",
            "UCIE_C40_LOSS_ONE_TIME",
            "UCIE_C40_DRILL_ONCE_ALREADY_ATTEMPTED",
            "[IO.FileMode]::CreateNew",
        ):
            self.assertIn(expected, code)

    def test_owner_task_source_and_client_exact_scope(self):
        code = self.code
        for expected in (
            "UCIE-C40-Recover",
            "D:\\UCIE\\scripts\\ucie_c40_recover.ps1",
            "23dcb08524b32c611b43c1136a444286d7dc776598a739a7152a651a5244e66f",
            "tunnel-client-v0.0.16\\tunnel-client.exe",
            "ucie-private-c40.yaml",
            "[string][char]92",
            "UCIE_C40_DRILL_ELEVATED_OWNER_REQUIRED",
            "UCIE_C40_DRILL_PROCESS_CHANGED_AFTER_APPROVAL",
            "UCIE_C40_DRILL_TARGET_HANDLE_MISMATCH",
        ):
            self.assertIn(expected, code)

    def test_no_secondary_client_or_task_control(self):
        for forbidden in (
            "Start-Process", "Start-ScheduledTask", "Enable-ScheduledTask",
            "Disable-ScheduledTask", "Register-ScheduledTask",
            "Unregister-ScheduledTask", "Set-ScheduledTask",
            "Stop-ScheduledTask", "Stop-Service", "New-Service",
            "Invoke-WebRequest", "Invoke-RestMethod", "D:\\OFFICE_AGENT",
            "D:\\MYGAME", "D:\\Skeleton", "UCIE-PublicMiner-Hourly",
            "UCIE-Internal-Minute",
        ):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, self.code)

    def test_monitor_requires_new_process_and_fresh_child_started_receipt(self):
        for expected in (
            "$process.Kill()",
            "$process.WaitForExit(5000)",
            "'UCIE_C40_CHILD_STARTED'",
            "CYCLE_OK",
            "SINGLE_CLIENT_RESTART_RECEIPT_OBSERVED",
            "CLIENT_RETURNED_WITHOUT_ATTRIBUTED_RESTART_RECEIPT",
            "AUTO_RESTART_NOT_OBSERVED_OWNER_MANUAL_REVIEW",
            "owner_logon_recovery_not_tested = $true",
        ):
            self.assertIn(expected, self.code)

    def test_powershell_parser(self):
        shell = shutil.which("powershell.exe") or shutil.which("pwsh")
        if not shell:
            self.skipTest("PowerShell not available")
        path = str(SCRIPT).replace("'", "''")
        command = (
            "$t=$null;$e=$null;"
            f"[void][System.Management.Automation.Language.Parser]::ParseFile('{path}',[ref]$t,[ref]$e);"
            "if($e.Count){$e|%{$_.Message};exit 2}"
        )
        result = subprocess.run(
            [shell, "-NoProfile", "-NonInteractive", "-Command", command],
            capture_output=True, text=True, errors="replace", timeout=25, check=False
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_owner_host_read_only_preview(self):
        if os.name != "nt" or not PROFILE.is_file():
            self.skipTest("UCIE owner Windows host required")
        shell = shutil.which("powershell.exe")
        if not shell:
            self.skipTest("Windows PowerShell unavailable")
        check = subprocess.run(
            [shell, "-NoProfile", "-NonInteractive", "-File", str(SCRIPT),
             "-Mode", "Preview"],
            capture_output=True, text=True, errors="replace", timeout=35, check=False
        )
        self.assertEqual(check.returncode, 0, 
                         "UCIE owner-only read-only preflight failed: " +
                         (check.stderr or "")[:500])
        lines = check.stdout.strip().splitlines()
        self.assertTrue(lines, "UCIE drill preview missing JSON")
        row = json.loads(lines[-1])
        print("UCIE_C40_OWNER_LOSS_DRILL_PREVIEW="+json.dumps(row,sort_keys=True))
        self.assertEqual(row["status"], "UCIE_C40_LOSS_DRILL_PREVIEW_ONLY")
        self.assertEqual(row["task_state"], "Running")
        self.assertEqual(row["client_count"], 1)
        self.assertTrue(row["owner_and_source_verified"])
        self.assertFalse(row["task_modified"])
        self.assertFalse(row["client_modified"])
        self.assertFalse(row["operating_database_modified"])


if __name__ == "__main__":
    unittest.main()
