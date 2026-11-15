"""UCIE owner P11 PowerShell wrapper: parser, static safety, real safe preview.

Never run -Approve / -AcceptUnknownSharedQuota or perform a network GET.
Only actual local P11 held row is compared; other P10 jobs may advance.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess
import unittest

from ucie_miner import pending_queue as q

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "p11_owner_exact_one_get_trial_v01.ps1"


class OwnerP11WrapperPreview(unittest.TestCase):
    def test_01_exact_one_source_and_two_explicit_flags(self):
        source = SCRIPT.read_text(encoding="utf-8-sig")
        for approved in ("[switch]$Approve",
                         "[switch]$AcceptUnknownSharedQuota",
                         "UCIE_OWNER_APPROVES_ONE_PUBLIC_GET_ACCEPTING_UNKNOWN_SHARED_QUOTA",
                         "repo:python/cpython", "--expected-sha256",
                         "READONLY_PREVIEW_ONE_GET_NOT_EXECUTED"):
            self.assertIn(approved, source)
        for banned in ("Start-ScheduledTask ", "Set-ScheduledTask ",
                       "Unregister-ScheduledTask ", "Invoke-WebRequest ",
                       "Invoke-RestMethod ", "git push ", "Remove-Item "):
            self.assertNotIn(banned, source)

    @unittest.skipUnless(os.name == "nt" and shutil.which("powershell.exe"),
                         "Windows PowerShell required")
    def test_02_ps_syntax_without_execution(self):
        command = ("$t=$null;$e=$null;"
                   "[Management.Automation.Language.Parser]::ParseFile("
                   "'" + str(SCRIPT).replace("'", "''") +
                   "',[ref]$t,[ref]$e) | Out-Null;"
                   "if($e.Count -gt 0){exit 2};'UCIE_ONE_GET_PS_SYNTAX_OK'")
        p = subprocess.run(
            ["powershell.exe", "-NoProfile", "-NonInteractive",
             "-Command", command], timeout=20, cwd=str(ROOT),
            capture_output=True, check=False)
        self.assertEqual(p.returncode, 0, p.stderr.decode("utf-8","replace"))
        self.assertIn(b"UCIE_ONE_GET_PS_SYNTAX_OK", p.stdout)

    @unittest.skipUnless(os.name == "nt" and shutil.which("powershell.exe"),
                         "exact owner Windows required")
    def test_03_real_owner_default_preview_is_zero_get(self):
        if ROOT.resolve() != Path("D:/UCIE").resolve() or ROOT.is_symlink():
            self.skipTest("exact UCIE owner checkout unavailable")
        first = q.inspect_queue(ROOT)
        p = subprocess.run(
            ["powershell.exe", "-NoProfile", "-NonInteractive",
             "-File", str(SCRIPT)],
            timeout=40, cwd=str(ROOT), capture_output=True,
            check=False, env={**os.environ,
                              "PYTHONPATH":str(ROOT/"src")})
        second = q.inspect_queue(ROOT)
        a = [x for x in first["jobs"]
             if x["kind"]=="PUBLIC_INCREMENTAL_MINING"]
        b = [x for x in second["jobs"]
             if x["kind"]=="PUBLIC_INCREMENTAL_MINING"]
        self.assertEqual(a, b, "P11 held queue job must be unchanged")
        if p.returncode == 0:
            data=json.loads(p.stdout.decode("utf-8-sig"))
            self.assertEqual(data["status"],
                             "READONLY_PREVIEW_ONE_GET_NOT_EXECUTED")
            self.assertEqual(data["source_id"], "repo:python/cpython")
            self.assertEqual(data["public_gets_requested"],0)
            outcome = data["status"]
        else:
            # Current owner PublicMiner HTTP 403 is a reason to refuse
            # even a one-off P11 metadata GET. No bypass.
            stderr = p.stderr.decode("utf-8", "replace")
            self.assertIn("UCIE_P11_OWNER_READONLY_PREFLIGHT_DENIED",stderr)
            outcome = "OWNER_PREFLIGHT_FAIL_CLOSED_NO_GET"
        print("UCIE_P11_OWNER_WRAPPER_READONLY="+json.dumps({
            "schema":"UCIE_P11_OWNER_ONE_GET_PS_CHECK_V01",
            "status":outcome,
            "public_gets_requested":0,
            "p11_queue_modified":False,"task_modified":False,
        },sort_keys=True))


if __name__ == "__main__":
    unittest.main()
