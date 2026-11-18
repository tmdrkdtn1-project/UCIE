"""W19 PowerShell owner stage: static guards + cross-platform contract-only tests.

No real owner maintenance, ScheduledTask mutation, C40 reload or source DB
access is performed in CI. Windows interpreter tests are strictly no-host.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "ucie_owner_w19_data_task_stage_v01.ps1"
DATA = ROOT / "scripts" / "ucie_owner_w19_lockstep_handoff_v01.py"


class W19OwnerStageContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.src = SCRIPT.read_text("utf-8")

    def test_exact_roots_and_stable_c40_action(self):
        text = self.src
        self.assertIn("$old='D:\\UCIE'", text)
        self.assertIn("$root='D:\\UCIE_PROJECT\\UCIE'", text)
        self.assertIn("UCIE-C40-Recover", text)
        self.assertIn("C40Hash", text)
        self.assertIn("UCIE_W19_C40_ACTION_DRIFT", text)
        self.assertEqual(text.count("Name='UCIE-"), 3)
        self.assertIn("UCIE-PublicMiner-Hourly", text)
        self.assertIn("UCIE-Internal-Minute", text)
        self.assertIn("UCIE-LocalV1-Web", text)

    def test_default_contract_does_not_read_tasks_or_host(self):
        text = self.src
        self.assertLess(text.index("if ($ContractOnly) {"),
                        text.index("Import-Module ScheduledTasks"))
        self.assertLess(text.index("UCIE_W19_EXPLICIT_OWNER_APPROVAL_REQUIRED"),
                        text.index("Import-Module ScheduledTasks"))
        self.assertIn("UCIE_W19_CONTRACT_ONLY_NO_HOST_ACCESS", text)
        self.assertIn("tasks_queried=$false", text)
        self.assertIn("live_cutover_authorized=$false", text)

    def test_private_journal_before_final_db_handoff(self):
        text = self.src
        self.assertIn("UCIE_W19_OWNER_DATA_TASK_STAGE_JOURNAL_V01.json", text)
        self.assertLess(text.index("PrivateJson $journal"),
                        text.index("& $python -I -B $handoff --prepare"))
        self.assertLess(text.index("& $python -I -B $handoff --prepare"),
                        text.index("& powershell.exe -NoProfile -NonInteractive -File $rebinder -Apply"))
        self.assertIn("private_handoff_manifest.json", text)
        self.assertIn("UCIE_W13_TASK_REBIND_V01.json", text)
        self.assertIn("UCIE_W19_LOCKSTEP_FINAL_DATA_V01", text)
        self.assertIn("-Rollback -OwnerApproval $w13Approval", text)
        self.assertIn("Remove-Item -LiteralPath $marker", text)
        self.assertIn("UCIE_W19_OWNER_MARKER_DRIFT", text)

    def test_rebinding_stops_before_live_activation(self):
        text = self.src
        for forbidden in (
            "Enable-ScheduledTask", "Start-ScheduledTask", "Stop-ScheduledTask",
            "Restart-Service", "Stop-Process", "Remove-Item -LiteralPath $old",
            "git reset", "git clean", "git pull",
        ):
            self.assertNotIn(forbidden, text)
        self.assertIn("UCIE_W19_THREE_TASKS_REBOUND_DISABLED__LIVE_ACTIVATION_HOLD", text)
        self.assertIn("c40_tunnel_live_health_verified=$false", text)
        self.assertIn("tasks_enabled=0", text)

    def test_powershell_parser_contract_and_negative_approval(self):
        exe = ("powershell.exe" if os.name == "nt"
               else shutil.which("pwsh"))
        if exe is None:
            self.skipTest("PowerShell not installed on this CI system")
        if os.name == "nt":
            invoke = [exe, "-NoProfile", "-NonInteractive",
                      "-ExecutionPolicy", "Bypass", "-File", str(SCRIPT)]
        else:
            invoke = [exe, "-NoProfile", "-NonInteractive", "-File", str(SCRIPT)]
        escaped = str(SCRIPT).replace("'", "''")
        snippet = (
            "$tokens=$null;$errors=$null;"
            f"[System.Management.Automation.Language.Parser]::ParseFile('{escaped}',"
            "[ref]$tokens,[ref]$errors)|Out-Null;"
            "if(@($errors).Count -ne 0){$errors|ForEach-Object{$_.Message};exit 2};exit 0"
        )
        syntax = subprocess.run([exe, "-NoProfile", "-NonInteractive",
                                 "-Command", snippet], capture_output=True,
                                text=True, timeout=25, check=False)
        self.assertEqual(syntax.returncode, 0, syntax.stderr + syntax.stdout)
        safe = subprocess.run(invoke, capture_output=True, text=True,
                              timeout=25, check=False)
        self.assertEqual(safe.returncode, 0, safe.stderr + safe.stdout)
        obj = json.loads(safe.stdout.strip())
        self.assertEqual(obj["status"], "UCIE_W19_CONTRACT_ONLY_NO_HOST_ACCESS")
        self.assertFalse(obj["tasks_queried"])
        for arg in ("-Apply", "-Rollback"):
            with self.subTest(arg=arg):
                denied = subprocess.run(invoke + [arg], capture_output=True,
                                        text=True, timeout=25, check=False)
                self.assertNotEqual(denied.returncode, 0)
                self.assertIn("UCIE_W19_EXPLICIT_OWNER_APPROVAL_REQUIRED",
                              denied.stderr + denied.stdout)


if __name__ == "__main__":
    unittest.main()
