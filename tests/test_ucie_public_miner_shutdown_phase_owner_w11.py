"""UCIE W11 owner-only disposable synthetic phase runner acceptance.

Only exact D:/UCIE Windows owner host. CI temporary checkouts SKIP.
It never invokes the real miner, TaskScheduler or other project sources.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess
import unittest


class UCIEW11OwnerSyntheticShutdownTests(unittest.TestCase):
    def _owner(self):
        root = Path(__file__).resolve().parents[1]
        if (os.name != "nt" or root.is_symlink()
                or root.resolve() != Path("D:/UCIE").resolve()):
            self.skipTest("OWNER_D_UCIE_WINDOWS_ONLY")
        pwsh = shutil.which("powershell.exe")
        if pwsh is None:
            self.skipTest("POWERSHELL_UNAVAILABLE_NO_ATTESTATION")
        script = root / "scripts" / "ucie_public_miner_shutdown_phase_w11.ps1"
        self.assertTrue(script.is_file() and not script.is_symlink())
        return pwsh, script

    def _run(self, synthetic):
        pwsh, script = self._owner()
        cmd = [pwsh, "-NoProfile", "-NonInteractive", "-File", str(script)]
        if synthetic:
            cmd.append("-RunSynthetic")
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=40, check=False)
        self.assertEqual(result.returncode, 0,
                         "OWNER_W11_DISPOSABLE_PHASE_REPORT_UNAVAILABLE_NO_GO")
        data = json.loads(result.stdout.strip())
        self.assertEqual(data["schema"],
                         "UCIE_W11_PUBLIC_MINER_SHUTDOWN_PHASE_SYNTHETIC_V01")
        self.assertEqual(data["task_scheduler_mutations"], 0)
        self.assertEqual(data["owner_operating_db_writes"], 0)
        self.assertFalse(data["production_termination_root_cause_proven"])
        return data

    def test_owner_preview_has_no_process(self):
        report = self._run(False)
        self.assertEqual(report["status"],
                         "SYNTHETIC_PHASE_LAB_NOT_RUN_NO_SCHEDULER_PROOF")
        self.assertEqual(report["synthetic_subprocesses_started"], 0)

    def test_owner_synthetic_four_modes_and_no_production_change(self):
        report = self._run(True)
        self.assertEqual(report["status"],
                         "FIRST_PARTY_SYNTHETIC_PHASES_CLASSIFIED_NO_PRODUCTION_CLAIM")
        self.assertEqual(report["passed"], 4)
        self.assertEqual(report["cases"], 4)
        self.assertFalse(report["real_public_miner_executed"])
        self.assertFalse(report["real_task_scheduler_verified"])
        self.assertFalse(report["other_project_access"])
        self.assertEqual(report["network_requests"], 0)
        self.assertFalse(report["released"])
        names = [x["mode"] for x in report["results"]]
        self.assertEqual(names, [
            "clean", "fsync_error", "stdout_error", "post_stdout_hold"])
        clean = {"schema": report["schema"], "status": report["status"],
                 "passed": report["passed"], "cases": report["cases"],
                 "modes": [
                     {"mode": x["mode"],
                      "child_returncode": x["child_returncode"],
                      "timed_out": x["child_timeout_observed"],
                      "fsync_returned": x["fsync_returned"],
                      "receipt_write_returned": x["receipt_write_returned"],
                      "worker_returned": x["worker_returned"],
                      "stdout_flush_returned": x["stdout_flush_returned"],
                      "python_atexit_observed": x["python_atexit_observed"]}
                     for x in report["results"]],
                 "production_root_cause_proven": False,
                 "task_scheduler_mutations": 0}
        print("UCIE_W11_OWNER_SYNTHETIC_PHASE_QA="
              + json.dumps(clean, sort_keys=True, ensure_ascii=True))


if __name__ == "__main__":
    unittest.main()
