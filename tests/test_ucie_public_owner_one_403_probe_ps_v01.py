"""UCIE-only PowerShell owner 403 diagnostic wrapper: SAFE PREVIEW tests.

Never use -Approve nor -AcceptUnknownSharedQuota. Never sends public
GET, mutates queued P10/P11 jobs, starts Windows task or edits last_run.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess
import unittest

from ucie_miner import pending_queue as q
from ucie_miner import public_owner_one_403_probe_v01 as probe

ROOT=Path(__file__).resolve().parents[1]
SCRIPT=ROOT/"scripts"/"public_owner_one_403_probe_v01.ps1"


class OwnerOne403PowerShellPreviewTests(unittest.TestCase):
    def test_01_fixed_allowed_source_two_consent_flags_and_no_task_mutation(self):
        text=SCRIPT.read_text(encoding="utf-8-sig")
        for phrase in (
                "[switch]$Approve",
                "[switch]$AcceptUnknownSharedQuota",
                "UCIE_OWNER_ACCEPTS_ONE_GET_AFTER_HTTP403_WITH_UNKNOWN_SHARED_BUDGET",
                "python/cpython", "FETCH_PR_LIST",
                "UCIE_PUBLIC_MINER_ONE_HTTP403_OWNER_PROBE_V01",
                "OWNER_PREVIEW_NO_GET",
                "original_receipt_sha256",
                "public_owner_one_403_probe_v01",
        ):
            self.assertIn(phrase,text)
        for banned in (
                "Set-ScheduledTask ", "Start-ScheduledTask ",
                "Unregister-ScheduledTask ", "Remove-Item ",
                "Invoke-WebRequest ", "Invoke-RestMethod ",
                "git push ", "git reset ", "OPENAI_API_KEY"):
            self.assertNotIn(banned,text)
        self.assertEqual(probe.SOURCE,"python/cpython")
        self.assertEqual(probe.OPERATION,"FETCH_PR_LIST")

    @unittest.skipUnless(os.name=="nt" and shutil.which("powershell.exe"),
                         "Windows PowerShell required")
    def test_02_real_ps_parser_does_not_execute(self):
        command = (
            "$t=$null;$e=$null;"
            "[Management.Automation.Language.Parser]::ParseFile("
            "'" + str(SCRIPT).replace("'","''") +
            "',[ref]$t,[ref]$e) | Out-Null;"
            "if($e.Count -gt 0){exit 2};'UCIE_403_ONE_PS_PARSE_OK'")
        p=subprocess.run(
            ["powershell.exe","-NoProfile","-NonInteractive",
             "-Command",command],timeout=20,cwd=str(ROOT),
            stdout=subprocess.PIPE,stderr=subprocess.PIPE,check=False)
        self.assertEqual(p.returncode,0,p.stderr.decode("utf-8","replace"))
        self.assertIn(b"UCIE_403_ONE_PS_PARSE_OK",p.stdout)

    @unittest.skipUnless(os.name=="nt" and shutil.which("powershell.exe"),
                         "exact UCIE owner Windows only")
    def test_03_owner_default_preview_no_get_and_no_queue_change(self):
        if (ROOT.resolve()!=Path("D:/UCIE").resolve()
                or ROOT.is_symlink() or not (ROOT/".git").is_dir()):
            self.skipTest("exact D:/UCIE checkout unavailable")
        last=ROOT/"runtime"/"last_run.json"
        if not last.is_file() or last.is_symlink():
            self.skipTest("current UCIE last_run absent or unsafe")
        before=last.read_bytes()
        before_queue=q.inspect_queue(ROOT)
        result=subprocess.run(
            ["powershell.exe","-NoProfile","-NonInteractive",
             "-File",str(SCRIPT)],
            timeout=35,cwd=str(ROOT),stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,check=False,
            env={**os.environ,"PYTHONPATH":str(ROOT/"src")})
        after_queue=q.inspect_queue(ROOT)
        # Existing minute worker may naturally advance unrelated job rows.
        held_before=[x for x in before_queue["jobs"]
                     if x["kind"]=="PUBLIC_INCREMENTAL_MINING"]
        held_after=[x for x in after_queue["jobs"]
                    if x["kind"]=="PUBLIC_INCREMENTAL_MINING"]
        self.assertEqual(held_before,held_after)
        self.assertEqual(before,last.read_bytes(),
                         "403 failed receipt must remain unchanged")
        if result.returncode==0:
            response=json.loads(result.stdout.decode("utf-8-sig"))
            self.assertEqual(response["schema"],
                             "UCIE_PUBLIC403_OWNER_ONESHOT_PS_V01")
            self.assertEqual(response["status"],"OWNER_PREVIEW_NO_GET")
            self.assertEqual(response["approved_source"],"python/cpython")
            self.assertEqual(response["public_gets_requested"],0)
            outcome=response["status"]
        else:
            stderr=result.stderr.decode("utf-8","replace")
            self.assertIn("UCIE_PUBLIC403_OWNER_DIAGNOSTIC_PREFLIGHT_NO_GO",
                          stderr)
            outcome="OWNER_403_PREFLIGHT_FAIL_CLOSED_ZERO_GET"
        print("UCIE_PUBLIC403_OWNER_PS_READONLY="+json.dumps({
            "schema":"UCIE_PUBLIC403_OWNER_ONE_SHOT_PS_READONLY_TEST_V01",
            "status":outcome,
            "p11_held_queue_unchanged":True,
            "last_public_miner_receipt_unchanged":True,
            "public_gets_requested":0,
            "task_modified":False,"model_trained":False
        },ensure_ascii=True,sort_keys=True))


if __name__=="__main__":
    unittest.main()
