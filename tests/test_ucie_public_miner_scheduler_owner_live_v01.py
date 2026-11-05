"""Owner-only fixed UCIE task read-only diagnostic acceptance test.

Runs ONLY the UCIE-authored fixed-path diagnostic .ps1 once, with no
arguments or shell expansion. Does not start the miner or change a task.
Other CI checkouts skip; no attempt to impersonate owner permissions.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess
import unittest


class UcieOwnerTaskReadOnlyDiagnosticTests(unittest.TestCase):
    def test_exact_owner_public_miner_task_report(self):
        root = Path(__file__).resolve().parents[1]
        if (os.name != "nt" or root.is_symlink() or
                root.resolve() != Path("D:/UCIE").resolve()):
            self.skipTest("OWNER_D_UCIE_WINDOWS_ONLY")
        executable = shutil.which("powershell.exe")
        if executable is None:
            self.skipTest("POWERSHELL_EXECUTABLE_UNAVAILABLE_NO_HOST_ATTESTATION")
        ps = root / "scripts" / "ucie_public_miner_scheduler_diagnostic_v01.ps1"
        self.assertTrue(ps.is_file() and not ps.is_symlink())
        result = subprocess.run(
            [executable, "-NoProfile", "-NonInteractive", "-File", str(ps)],
            capture_output=True, text=True, timeout=35, check=False,
        )
        self.assertEqual(result.returncode, 0,
                         "UCIE_OWNER_FIXED_SCHEDULER_DIAGNOSTIC_NO_GO")
        response = json.loads(result.stdout.strip())
        self.assertEqual(
            response["schema"], "UCIE_PUBLIC_MINER_SCHEDULER_DIAGNOSTIC_V01")
        self.assertIn(response["status"], (
            "PUBLIC_MINER_SCHEDULER_NOT_ATTESTED_NO_GO",
            "PUBLIC_MINER_TWO_CYCLE_SCHEDULED_EVIDENCE_OBSERVED"))
        self.assertEqual(response["fixed_task"],
                         r"\UCIE-PublicMiner-Hourly")
        self.assertFalse(response["actual_task_mutation"])
        self.assertEqual(response["operating_database_writes"], 0)
        self.assertEqual(response["public_network_requests"], 0)
        self.assertFalse(response["other_project_access"])
        self.assertFalse(response["remediation_executed"])
        safe = {
            "status": response["status"],
            "task_state": response["task_state"],
            "last_task_result_decimal":
                response["last_task_result_decimal"],
            "last_task_result_hex": response["last_task_result_hex"],
            "last_task_result_interpretation":
                response["last_task_result_interpretation"],
            "task_evidence_status": response["task_evidence_status"],
            "matched_event_instances": response["matched_event_instances"],
            "required_event_instances": response["required_event_instances"],
            "blocker_codes": response["blocker_codes"],
            "task_mutation": False,
        }
        print("UCIE_OWNER_PUBLIC_MINER_SCHEDULER_LIVE_V01="
              + json.dumps(safe, sort_keys=True, ensure_ascii=True))


if __name__ == "__main__":
    unittest.main()
