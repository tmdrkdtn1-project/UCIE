"""UCIE W20 LocalV1 owner pilot: no-host contract and native PowerShell parser.

Actual Windows Task Scheduler, HTTP and C40 are not operated in CI.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "ucie_owner_w20_local_pilot_v01.ps1"


class W20LocalPilotContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.code = SCRIPT.read_text("utf-8")

    def test_only_localv1_task_can_be_enabled_started_or_stopped(self):
        code = self.code
        self.assertIn("Name='UCIE-PublicMiner-Hourly'", code)
        self.assertIn("Name='UCIE-Internal-Minute'", code)
        self.assertIn("Name='UCIE-LocalV1-Web'", code)
        self.assertEqual(code.count("Name='UCIE-"), 3)
        self.assertIn("Enable-ScheduledTask -TaskPath '\\' -TaskName $known[2].Name", code)
        self.assertIn("Start-ScheduledTask -TaskPath '\\' -TaskName $known[2].Name", code)
        self.assertIn("Stop-ScheduledTask -TaskPath '\\' -TaskName $known[2].Name", code)
        self.assertIn("Disable-ScheduledTask -TaskPath '\\' -TaskName $known[2].Name", code)
        self.assertNotIn("Set-ScheduledTask", code)
        self.assertNotIn("Enable-ScheduledTask -TaskPath '\\' -TaskName $known[0].Name", code)
        self.assertNotIn("Enable-ScheduledTask -TaskPath '\\' -TaskName $known[1].Name", code)

    def test_source_approval_before_host_access_and_powershell_default(self):
        code = self.code
        self.assertLess(code.index("if ($ContractOnly) {"),
                        code.index("Import-Module ScheduledTasks"))
        self.assertLess(code.index("UCIE_W20_EXPLICIT_OWNER_APPROVAL_REQUIRED"),
                        code.index("Import-Module ScheduledTasks"))
        self.assertIn("UCIE_W20_CONTRACT_ONLY_NO_HOST_ACCESS", code)
        self.assertIn("$stage.owner_sid_sha256", code)
        self.assertIn("W19_OWNER_DATA_TASK_STAGE_JOURNAL", code)
        self.assertIn("Get-FileHash -LiteralPath $manifest -Algorithm SHA256", code)
        self.assertIn("$originalC40 -ne $stage.c40_action_sha256", code)
        self.assertIn("UCIE_W20_SQLITE_POST_HANDOFF_DRIFT_HOLD", code)
        self.assertIn("RequireTwoDisabled", code)

    def test_no_c40_or_original_db_operation_and_fail_closed_rollback(self):
        code = self.code
        for forbidden in ("Restart-Service", "git clean", "git reset",
                          "git pull", "Remove-Item -LiteralPath $old",
                          "Set-ScheduledTask -TaskName 'UCIE-C40-Recover'"):
            self.assertNotIn(forbidden, code)
        self.assertIn("-Rollback -OwnerApproval $w19Approval", code)
        self.assertIn("StopDisableLocal", code)
        self.assertIn("UCIE_W20_C40_ACTION_DRIFT", code)
        self.assertIn("c40_mcp_round_trip_verified=$false", code)
        self.assertIn("live_cutover_authorized=$false", code)
        self.assertIn("old_sqlite_never_overwritten=$true", code)

    def test_known_local_health_exact_owner_only(self):
        code = self.code
        self.assertIn("http://127.0.0.1:18767/local/health", code)
        self.assertIn("'UCIE_OWNER_LOCAL_FOUR_PILLAR_APP_V01'", code)
        self.assertIn("'LOCAL_V1_OWNER_ACCEPTED_LOCAL_GO_NO_ONLINE_RELEASE'", code)
        self.assertIn("$h.owner_acceptance_verified -eq $true", code)
        self.assertIn("$h.online_release_authorized -eq $false", code)
        self.assertIn("$h.operating_database_writes -eq 0", code)
        self.assertIn("$h.bound_host -eq '127.0.0.1'", code)
        self.assertIn("UCIE_W20_LOCAL_LOOPBACK_PORT_IN_USE", code)

    def test_native_parser_contract_and_denied_actions(self):
        ps = "powershell.exe" if os.name == "nt" else shutil.which("pwsh")
        if not ps:
            self.skipTest("PowerShell not available")
        escaped = str(SCRIPT).replace("'", "''")
        syntax = (
            "$t=$null;$e=$null;"
            f"[Management.Automation.Language.Parser]::ParseFile('{escaped}',"
            "[ref]$t,[ref]$e)|Out-Null;"
            "if(@($e).Count -ne 0){$e|ForEach-Object{$_.Message};exit 2};exit 0"
        )
        result = subprocess.run([ps, "-NoProfile", "-NonInteractive",
                                 "-Command", syntax], capture_output=True,
                                text=True, timeout=25)
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        invoke = [ps, "-NoProfile", "-NonInteractive"]
        if os.name == "nt":
            invoke += ["-ExecutionPolicy", "Bypass"]
        invoke += ["-File", str(SCRIPT)]
        safe = subprocess.run(invoke, capture_output=True, text=True, timeout=25)
        self.assertEqual(safe.returncode, 0, safe.stderr + safe.stdout)
        record = json.loads(safe.stdout)
        self.assertEqual(record["status"], "UCIE_W20_CONTRACT_ONLY_NO_HOST_ACCESS")
        self.assertFalse(record["task_enabled"])
        self.assertFalse(record["local_http_probed"])
        for arg in ("-PilotLocal", "-RollbackLocal"):
            with self.subTest(arg=arg):
                denied = subprocess.run(invoke + [arg],
                                        capture_output=True, text=True, timeout=25)
                self.assertNotEqual(denied.returncode, 0)
                self.assertIn("UCIE_W20_EXPLICIT_OWNER_APPROVAL_REQUIRED",
                              denied.stdout + denied.stderr)


if __name__ == "__main__":
    unittest.main()
