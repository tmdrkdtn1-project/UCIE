"""W15 canonical Git source promotion: contract + Windows parser only.

CI never calls -Apply or -Rollback with approval, and cannot modify owner D:,
C40, ScheduledTasks, SQLite, data, private integrated archive or live scripts.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "ucie_owner_canonical_git_stage_v01.ps1"


class W15CanonicalGitSourceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.code = SCRIPT.read_text("utf-8")

    def test_git_clone_is_approved_public_ucie_and_not_shallow(self):
        code = self.code
        self.assertIn("$remote='https://github.com/tmdrkdtn1-project/UCIE.git'", code)
        self.assertIn("3515c14f5c82202ea13eac7b5a3e94fbb7ac94b9", code)
        self.assertIn("clone -q --no-tags --single-branch --branch main -- $remote $scratch", code)
        self.assertNotIn(" --depth ", code)
        self.assertNotIn("git fetch", code)
        self.assertNotIn("git pull", code)
        self.assertNotIn("git reset", code)
        self.assertNotIn("git clean", code)
        self.assertIn("UCIE_W15_REQUIRED_W14_ANCESTOR_MISSING", code)

    def test_prior_owner_stage_stays_preserved_and_never_overwritten(self):
        code = self.code
        self.assertIn("'UCIE_W15_ORIGINAL_CODE_STAGE_V01'", code)
        self.assertIn("'UCIE_CODE_ONLY_STAGE_VERIFIED_V01.json'", code)
        self.assertIn("'UCIE_CODE_ONLY_STAGE_232_FILES_VERIFIED__LIVE_CUTOVER_NO_GO'", code)
        self.assertIn("SaveJson $journal", code)
        self.assertLess(code.index("SaveJson $journal"), code.index("Move-Item -LiteralPath $target -Destination $preserved"))
        self.assertIn("UCIE_W15_SWAP_ABORTED_ORIGINAL_STAGE_RESTORED", code)
        self.assertIn("UCIE_W15_PARTIAL_SWAP_MANUAL_RECOVERY_REQUIRED", code)
        self.assertNotIn("Remove-Item -LiteralPath $target", code)
        self.assertNotIn("Remove-Item -LiteralPath $preserved", code)
        self.assertIn("Absent $scratch", code)

    def test_owner_exact_approval_only_after_default_contract(self):
        code = self.code
        self.assertIn("UCIE_W15_CONTRACT_ONLY_NO_HOST_ACCESS", code)
        self.assertIn("UCIE_W15_EXPLICIT_OWNER_APPROVAL_REQUIRED", code)
        self.assertIn("UCIE_W15_INTERACTIVE_OWNER_WINDOWS_REQUIRED", code)
        self.assertIn("UCIE_W15_PRIVATE_ARCHIVE_ACL_REQUIRED", code)
        self.assertIn("AUTHORIZE_UCIE_W15_CANONICAL_STAGE_SWAP", code)
        self.assertIn("AUTHORIZE_UCIE_W15_CANONICAL_STAGE_ROLLBACK", code)
        self.assertIn("UCIE_W15_ORIGINAL_CODE_STAGE_RESTORED", code)

    def test_live_task_c40_binding_is_read_only_and_new_root_forbidden(self):
        code = self.code
        self.assertIn("function NoTaskPointsAtTarget", code)
        for name in (
            "UCIE-PublicMiner-Hourly",
            "UCIE-Internal-Minute",
            "UCIE-LocalV1-Web",
            "UCIE-C40-Recover",
        ):
            self.assertIn(name, code)
        for forbidden in (
            "Set-ScheduledTask",
            "Start-ScheduledTask",
            "Stop-ScheduledTask",
            "Register-ScheduledTask",
            "Unregister-ScheduledTask",
            "cloudflared.exe",
            "sqlite3.connect",
            "D:\\UCIE_DATA",
            "D:\\UCIE_PREVIEW",
        ):
            self.assertNotIn(forbidden, code)
        self.assertIn("live_git_tasks_c40_sqlite_modified=$false", code)

    def test_no_runtime_or_user_marker_created_on_canonical_promote(self):
        code = self.code
        self.assertIn("NoRuntime $target", code)
        self.assertIn("NoRuntime $scratch", code)
        self.assertIn("'UCIE_W15_CANONICAL_GIT_STAGE_READY_NO_RUNTIME'", code)
        self.assertIn("new_runtime_or_venv_created=$false", code)
        self.assertIn("live_cutover_authorized=$false", code)

    def test_fileinfo_and_directoryinfo_ancestors_use_correct_members(self):
        code = self.code
        self.assertIn("$node -is [System.IO.FileInfo]", code)
        self.assertIn("$node=$node.Directory", code)
        self.assertIn("$node=$node.Parent", code)
        self.assertIn("Direct $sourceReceipt $false", code)

    @unittest.skipUnless(os.name == "nt", "Windows PowerShell 5.1 only")
    def test_windows_real_file_and_directory_direct_path_fixture(self):
        # Tests actual FileInfo/DirectoryInfo objects in a temporary CI folder.
        # Extracts only first-party Direct function; NEVER invokes W15 -Apply.
        ps = shutil.which("powershell.exe")
        if not ps:
            self.skipTest("Windows PowerShell unavailable")
        script_path = str(SCRIPT).replace("'", "''")
        command = (
            "$ErrorActionPreference='Stop';"
            "$t=$null;$e=$null;"
            "$ast=[Management.Automation.Language.Parser]::ParseFile("
            f"'{script_path}',[ref]$t,[ref]$e);"
            "if($e.Count -gt 0){throw 'UCIE_W15_SCRIPT_PARSE_FAILED'};"
            "$fn=$ast.Find({param($x) $x -is "
            "[Management.Automation.Language.FunctionDefinitionAst] -and "
            "$x.Name -eq 'Direct'},$true);"
            "if($null -eq $fn){throw 'UCIE_W15_DIRECT_MISSING'};"
            "Invoke-Expression $fn.Extent.Text;"
            "$tmp=Join-Path $env:TEMP ('UCIE_W15_FILEINFO_' + "
            "[guid]::NewGuid().ToString('N'));"
            "try {"
            "  [void](New-Item -ItemType Directory -Path $tmp -ErrorAction Stop);"
            "  $file=Join-Path $tmp 'accepted_receipt.json';"
            "  [IO.File]::WriteAllText($file,'{}');"
            "  if(-not ((Get-Item -LiteralPath $file) -is [IO.FileInfo]))"
            "  {throw 'UCIE_W15_FILE_FIXTURE_NOT_FILEINFO'};"
            "  Direct $tmp $true;"
            "  Direct $file $false;"
            "  'UCIE_W15_FILEINFO_DIRECTORYINFO_PATH_PASS';"
            "} finally {"
            "  if(Test-Path -LiteralPath $tmp){"
            "    Remove-Item -LiteralPath $tmp -Recurse -Force -ErrorAction Stop"
            "  }"
            "}"
        )
        result = subprocess.run(
            [ps, "-NoProfile", "-NonInteractive", "-Command", command],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            check=False, timeout=30)
        self.assertEqual(result.returncode, 0,
                         result.stderr + result.stdout)
        self.assertIn("UCIE_W15_FILEINFO_DIRECTORYINFO_PATH_PASS",
                      result.stdout)

    @unittest.skipUnless(os.name == "nt", "Windows PowerShell 5.1 only")
    def test_windows_powershell_contract_parser_and_approval_rejection(self):
        ps = shutil.which("powershell.exe")
        if not ps:
            self.skipTest("Windows PowerShell unavailable")
        done = subprocess.run([ps, "-NoProfile", "-NonInteractive", "-File", str(SCRIPT)],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            check=False, timeout=30)
        self.assertEqual(done.returncode, 0, done.stderr)
        report = json.loads(done.stdout)
        self.assertEqual(report["status"], "UCIE_W15_CONTRACT_ONLY_NO_HOST_ACCESS")
        self.assertFalse(report["live_git_tasks_c40_sqlite_modified"])
        self.assertFalse(report["network_used"])
        script_path = str(SCRIPT).replace("'", "''")
        command = ("$tok=$null;$errs=$null;"
                   "[Management.Automation.Language.Parser]::ParseFile("
                   f"'{script_path}',[ref]$tok,[ref]$errs)|Out-Null;"
                   "if($errs.Count -gt 0){$errs|ForEach-Object{$_.Message};exit 2};exit 0")
        parsed = subprocess.run([ps, "-NoProfile", "-NonInteractive", "-Command", command],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            check=False, timeout=30)
        self.assertEqual(parsed.returncode, 0, parsed.stderr + parsed.stdout)
        for mode in ("-Apply", "-Rollback"):
            with self.subTest(mode=mode):
                refused = subprocess.run(
                    [ps, "-NoProfile", "-NonInteractive", "-File", str(SCRIPT), mode],
                    capture_output=True, text=True, encoding="utf-8",
                    errors="replace", check=False, timeout=30)
                self.assertNotEqual(refused.returncode, 0)
                self.assertIn("UCIE_W15_EXPLICIT_OWNER_APPROVAL_REQUIRED",
                              refused.stderr + refused.stdout)


if __name__ == "__main__":
    unittest.main()
