"""W14 offline private runtime creation: single contract bundle.

No host root reads in default mode; CI does not provision a live venv, copy
SQLite, access owner D: or change Task/C40 actions.
"""
from __future__ import annotations
import json
import os
from pathlib import Path
import shutil
import subprocess
import unittest

ROOT=Path(__file__).resolve().parents[1]
SCRIPT=ROOT/'scripts'/'ucie_owner_offline_runtime_prepare_v01.ps1'
W13=ROOT/'scripts'/'ucie_owner_task_rebind_v01.ps1'


class W14OfflineRuntimeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text=SCRIPT.read_text('utf-8')

    def test_source_targets_only_exact_ucie_project(self):
        s=self.text
        for token in (
            "$root='D:\\UCIE_PROJECT\\UCIE'",
            "$archive='D:\\UCIE_PROJECT\\ARCHIVE'",
            "UCIE_W14_EXACT_STAGED_SCRIPT_PATH_REQUIRED",
            "UCIE_W14_W13_ANCESTRY_MISSING",
            "UCIE_W14_CANONICAL_MAIN_BRANCH_REQUIRED",
            "UCIE_W14_TRACKED_SOURCE_NOT_CLEAN",
        ):
            self.assertIn(token,s)

    def test_real_functionality_creates_fresh_offline_venv(self):
        s=self.text
        self.assertIn("UCIE_W14_ALREADY_PARTIALLY_OR_FULLY_PREPARED_NO_OVERWRITE",s)
        self.assertIn("& $basePython @baseArgs -m venv $venv",s)
        self.assertIn("-m pip install --no-index --no-cache-dir",s)
        self.assertIn("--only-binary ':all:'",s)
        self.assertIn("cryptography>=50.0.2,<51",s)
        self.assertIn("-m pip check",s)
        self.assertIn("import ucie_miner.local_v1_app_v01",s)
        self.assertIn("UCIE_W14_ISOLATED_OFFLINE_PYTHON_RUNTIME_PREPARED",s)

    def test_wheels_are_locally_sha_pinned_and_no_unsafe_cleanup(self):
        s=self.text
        self.assertIn("UCIE_W14_WHEEL_SHA256_V01",s)
        self.assertIn("Get-FileHash -LiteralPath $wheel -Algorithm SHA256",s)
        self.assertIn("UCIE_W14_WHEELHOUSE_UNLISTED_FILE_OR_SUBDIRECTORY",s)
        self.assertIn("UCIE_W14_PRIVATE_ARCHIVE_OWNER_ACL_REQUIRED",s)
        self.assertIn("UCIE_W14_EXPLICIT_OWNER_OFFLINE_PREP_APPROVAL_REQUIRED",s)
        self.assertNotIn("git clean",s)
        self.assertNotIn("git reset",s)
        self.assertNotIn("git fetch",s)
        self.assertNotIn("git pull",s)

    def test_no_task_c40_db_or_external_network_operations(self):
        s=self.text
        for forbid in ("Get-ScheduledTask","Set-ScheduledTask","Start-ScheduledTask",
                       "Stop-ScheduledTask","Register-ScheduledTask","Move-Item",
                       "Copy-Item","Invoke-WebRequest","Invoke-RestMethod",
                       "sqlite3.connect","cloudflared.exe","D:\\UCIE_DATA",
                       "D:\\UCIE_PREVIEW"):
            with self.subTest(forbid=forbid):
                self.assertNotIn(forbid,s)
        self.assertIn("runtime_database_migrated=$false",s)
        self.assertIn("live_cutover_authorized=$false",s)
        self.assertIn("owner_runtime_opt_in_marker_created=$false",s)

    def test_w13_rebind_requires_real_db_and_pinned_w14_environment(self):
        src=W13.read_text("utf-8")
        self.assertIn("runtime\\public_miner.sqlite3",src)
        self.assertIn("UCIE_W14_OFFLINE_RUNTIME_RECEIPT_V01.json",src)
        self.assertIn("UCIE_W14_ISOLATED_OFFLINE_PYTHON_RUNTIME_PREPARED",src)
        self.assertIn("if ($Apply)",src)
        self.assertIn("if ($Rollback)",src) if "if ($Rollback)" in src else None
        self.assertNotIn("Start-ScheduledTask",src)

    @unittest.skipUnless(os.name=='nt',"Native Windows PowerShell 5.1 only")
    def test_windows_contract_and_parser_deny_mutation_without_owner_approval(self):
        pwsh=shutil.which("powershell.exe")
        if not pwsh:
            self.skipTest("PowerShell unavailable")
        r=subprocess.run([pwsh,"-NoProfile","-NonInteractive","-File",str(SCRIPT)],
            capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=30)
        self.assertEqual(r.returncode,0,r.stderr)
        d=json.loads(r.stdout)
        self.assertEqual(d["status"],"UCIE_W14_CONTRACT_ONLY_NO_HOST_CHANGES")
        for key in ("operating_root_modified","operating_sqlite_opened",
                    "network_requested","c40_or_task_changed",
                    "new_environment_created","live_cutover_authorized"):
            self.assertFalse(d[key],key)
        c=("$tokens=$null;$errs=$null;"
           "[Management.Automation.Language.Parser]::ParseFile("
           "'"+str(SCRIPT).replace("'","''")+"',[ref]$tokens,[ref]$errs)|Out-Null;"
           "if($errs.Count -gt 0){$errs|ForEach-Object{$_.Message};exit 2};exit 0")
        parse=subprocess.run([pwsh,"-NoProfile","-NonInteractive","-Command",c],
            capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=30)
        self.assertEqual(parse.returncode,0,parse.stderr+parse.stdout)
        reject=subprocess.run([pwsh,"-NoProfile","-NonInteractive","-File",
            str(SCRIPT),"-Prepare"],capture_output=True,text=True,
            encoding='utf-8',errors='replace',timeout=30)
        self.assertNotEqual(reject.returncode,0)
        self.assertIn("UCIE_W14_EXPLICIT_OWNER_OFFLINE_PREP_APPROVAL_REQUIRED",
                      reject.stdout+reject.stderr)


if __name__=='__main__':
    unittest.main()
