"""One-command PowerShell owner wrapper: source QA and real preview only.

Do not invoke -Approve during this test. All task/database queries read-only.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess
import unittest

from ucie_miner.pending_queue import inspect_queue
from ucie_miner.p11_closed_loop import status as p11_status

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "p10_owner_rearm_one_v02.ps1"


class P10OwnerWrapperTests(unittest.TestCase):
    def test_01_script_has_explicit_approval_and_no_task_mutator(self):
        self.assertTrue(SCRIPT.is_file())
        source = SCRIPT.read_text(encoding="utf-8-sig")
        self.assertIn("[switch]$Approve", source)
        self.assertIn("if (-not $Approve)", source)
        self.assertIn("EXACT_OWNER_P10_SINGLE_JOB_PREVIEW_ONLY", source)
        self.assertIn("ONE_DELAYED_OWNER_REARM_COMMITTED", source)
        self.assertIn("UCIE_OWNER_APPROVES_EXACT_ONE_NONNETWORK_JOB_REARM",
                      source)
        self.assertIn("PUBLIC_METADATA_REVIEW", source)
        self.assertIn("UCIE_REPORT_PREPARATION", source)
        self.assertIn("ucie_miner.p10_owner_single_live_rearm_v02", source)
        self.assertIn("--expected-sha256", source)
        self.assertIn("--job-id", source)
        self.assertIn("$env:PYTHONPATH = Join-Path $root 'src'", source)
        for command in ("Set-ScheduledTask ", "Start-ScheduledTask ",
                        "Unregister-ScheduledTask ", "Remove-Item ",
                        "Invoke-WebRequest ", "Invoke-RestMethod "):
            self.assertNotIn(command, source)

    @unittest.skipUnless(os.name == "nt" and shutil.which("powershell.exe"),
                         "exact Windows PowerShell required")
    def test_02_source_powershell_parser_no_code_execution(self):
        cmd = (
            "$t=$null; $e=$null; "
            "[Management.Automation.Language.Parser]::ParseFile("
            "'" + str(SCRIPT).replace("'", "''") + "',[ref]$t,"
            "[ref]$e) | Out-Null; "
            "if ($e.Count -gt 0) { exit 2 }; 'UCIE_PS_SYNTAX_OK'"
        )
        p = subprocess.run(
            ["powershell.exe", "-NoProfile", "-NonInteractive",
             "-Command", cmd], timeout=20, cwd=str(ROOT),
            capture_output=True, check=False)
        self.assertEqual(p.returncode, 0, p.stderr.decode("utf-8", "replace"))
        self.assertIn(b"UCIE_PS_SYNTAX_OK", p.stdout)

    @unittest.skipUnless(os.name == "nt" and shutil.which("powershell.exe"),
                         "exact owner Windows only")
    def test_03_owner_default_preview_never_applies(self):
        if (ROOT.resolve() != Path("D:/UCIE").resolve()
                or ROOT.is_symlink() or not (ROOT / ".git").is_dir()):
            self.skipTest("exact UCIE owner root unavailable")
        before = (inspect_queue(ROOT, limit=20), p11_status(ROOT))
        p = subprocess.run(
            ["powershell.exe", "-NoProfile", "-NonInteractive",
             "-File", str(SCRIPT), "-Kind", "PUBLIC_METADATA_REVIEW"],
            timeout=30, cwd=str(ROOT), capture_output=True, check=False,
            env={**os.environ, "PYTHONPATH": str(ROOT / "src")},
        )
        if p.returncode != 0:
            env = {**os.environ, "PYTHONPATH": str(ROOT / "src")}
            direct = subprocess.run(
                [str(ROOT / ".venv" / "Scripts" / "python.exe"), "-B",
                 "-m", "ucie_miner.p10_owner_single_live_rearm_v02",
                 "--ucie-root", str(ROOT), "--kind",
                 "PUBLIC_METADATA_REVIEW"],
                cwd=str(ROOT), env=env, capture_output=True,
                timeout=30, check=False)
            result_text = direct.stdout.decode("utf-8", "replace")[:800]
            raise AssertionError(
                "WRAPPER_FAILED_AND_READONLY_DIRECT_DIAG "
                + json.dumps({"direct_exit": direct.returncode,
                              "direct_stdout": result_text,
                              "stderr_has_traceback":
                                  b"Traceback" in direct.stderr,
                              "stderr_has_module_not_found":
                                  b"ModuleNotFoundError" in direct.stderr,
                              "stderr_has_import_error":
                                  b"ImportError" in direct.stderr},
                             sort_keys=True))
        self.assertEqual(p.returncode, 0)
        self.assertLess(len(p.stdout), 2400)
        result = json.loads(p.stdout.decode("utf-8-sig"))
        self.assertEqual(result["schema"], "UCIE_P10_OWNER_ONE_JOB_PS_V02")
        self.assertEqual(result["status"], "PREVIEW_ONLY_NO_QUEUE_CHANGE")
        self.assertEqual(result["kind"], "PUBLIC_METADATA_REVIEW")
        self.assertEqual(result["job_id"], 2)
        self.assertTrue(result["owner_task_verified"])
        self.assertEqual(len(result["exact_row_fingerprint_sha256"]), 64)
        self.assertFalse(result["scheduler_changed"])
        self.assertFalse(result["queue_modified"])
        self.assertEqual(result["public_gets"], 0)
        self.assertFalse(result["auto_promoted"])
        after = (inspect_queue(ROOT, limit=20), p11_status(ROOT))
        self.assertEqual(before, after)
        print("UCIE_P10_OWNER_WRAPPER_PREVIEW=" +
              json.dumps(result, sort_keys=True, ensure_ascii=True))


if __name__ == "__main__":
    unittest.main()
