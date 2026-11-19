"""W26: pure W19 comparator on actual old owner tasks, safely inspect-only.

CI uses anonymous in-memory ScheduledTask-shaped values; NO real Tasks,
Windows owner archive, localhost, SQLite, C40, or service mutation.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
W26 = ROOT / "scripts" / "ucie_owner_w26_real_task_action_check_v01.ps1"
W19 = ROOT / "scripts" / "ucie_owner_w19_data_task_stage_v01.ps1"


class W26RealOwnerTaskComparatorContracts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = W26.read_text(encoding="utf-8")
        cls.w19 = W19.read_text(encoding="utf-8")

    def test_gate_before_every_host_access(self):
        s = self.source
        self.assertLess(s.index("if($ContractOnly){"), s.index("Get-Acl -LiteralPath $archive"))
        self.assertLess(s.index("UCIE_W26_EXPLICIT_READONLY_OWNER_APPROVAL_REQUIRED"),
                        s.index("Get-ScheduledTask -TaskPath"))
        self.assertIn("UCIE_W26_CONTRACT_ONLY_NO_HOST_ACCESS", s)
        self.assertIn("host_files_read=$false", s)
        self.assertIn("owner_tasks_queried=$false", s)
        self.assertIn("journal_written=$false", s)
        self.assertIn("operating_sqlite_opened=$false", s)
        self.assertIn("root_cause_verified=$false", s.replace("original_owner_failure_root_cause_verified=$false", "root_cause_verified=$false"))

    def test_w19_source_pinned_and_exact_function_extracted_not_owner_script(self):
        s = self.source
        self.assertIn("b5f3d05db9c2dd13e23a066c96a5c73dda5a2920", s)
        self.assertIn("17e1620659c15a570313c4d87fa425227f076839", s)
        self.assertIn("HEAD:scripts/ucie_owner_w19_data_task_stage_v01.ps1", s)
        self.assertIn("$env:GIT_OPTIONAL_LOCKS='0'", s)
        self.assertIn("UCIE_W26_WORKTREE_DRIFT_HOLD", s)
        self.assertIn("FunctionDefinitionAst", s)
        self.assertIn("ParseFile(", s)
        self.assertIn(". ([scriptblock]::Create($pure))", s)
        self.assertIn("$sameFunctionAsts=@($ast.FindAll({", s)
        self.assertNotIn("$matches=@($ast.FindAll({", s)
        self.assertIn("function Same($action,[string]$exe,[string]$expectedArguments,[string]$work)", s)
        self.assertIn("Same ($t.Actions[0]) $spec.Execute $spec.Arguments $old", s)
        self.assertNotIn("& $w19 -Apply", s)
        self.assertNotIn(". $w19", s)
        self.assertNotIn("& $w19", s)
        self.assertIn("$old='D:\\UCIE'", s)
        self.assertIn("UCIE-C40-Recover", self.w19)
        self.assertIn("original_owner_failure_root_cause_verified=$false", s)
        self.assertIn("original_writers_paused_for_test=$false", s)

    def test_no_unsafe_mutation_or_private_source_replay(self):
        s = self.source
        for forbidden in (
            "Disable-ScheduledTask", "Enable-ScheduledTask",
            "Start-ScheduledTask", "Stop-ScheduledTask",
            "Set-ScheduledTask", "Register-ScheduledTask",
            "Unregister-ScheduledTask", "Stop-Process",
            "taskkill", "Restart-Service", "Remove-Item",
            "Move-Item", "Copy-Item", "New-Item",
            "[IO.File]::Write", "git reset", "git clean",
            "git pull", "-ApplyLocal", "-RollbackLocal",
        ):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, s)

    def test_native_powershell_parser_default_and_missing_owner_approval(self):
        shell = "powershell.exe" if os.name == "nt" else shutil.which("pwsh")
        if not shell:
            self.skipTest("Native PowerShell unavailable")
        escaped = str(W26).replace("'", "''")
        parse = (
            "$tokens=$null;$errors=$null;"
            f"[Management.Automation.Language.Parser]::ParseFile('{escaped}',"
            "[ref]$tokens,[ref]$errors)|Out-Null;"
            "if(@($errors).Count -gt 0){$errors|ForEach-Object{$_.Message};exit 2};exit 0"
        )
        p = subprocess.run([shell, "-NoProfile", "-NonInteractive",
                            "-Command", parse],
                           text=True, capture_output=True, timeout=30)
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        cmd = [shell, "-NoProfile", "-NonInteractive"]
        if os.name == "nt":
            cmd.extend(["-ExecutionPolicy", "Bypass"])
        cmd.extend(["-File", str(W26)])
        safe = subprocess.run(cmd, text=True, capture_output=True, timeout=30)
        self.assertEqual(safe.returncode, 0, safe.stdout + safe.stderr)
        obj = json.loads(safe.stdout)
        self.assertEqual(obj["status"], "UCIE_W26_CONTRACT_ONLY_NO_HOST_ACCESS")
        self.assertFalse(obj["owner_tasks_queried"])
        self.assertFalse(obj["journal_written"])
        denied = subprocess.run(cmd + ["-CheckLocal"],
                                text=True, capture_output=True, timeout=30)
        self.assertNotEqual(denied.returncode, 0)
        self.assertIn("UCIE_W26_EXPLICIT_READONLY_OWNER_APPROVAL_REQUIRED",
                      denied.stdout + denied.stderr)

    def test_native_ast_extraction_executes_exact_w19_same_with_synthetic_actions(self):
        shell = "powershell.exe" if os.name == "nt" else shutil.which("pwsh")
        if not shell:
            self.skipTest("Native PowerShell unavailable")
        with tempfile.TemporaryDirectory(prefix="ucie_w26_native_ast_") as td:
            work = Path(td)
            fixture = work / "w19_same_ast_only.ps1"
            w19 = str(W19).replace("'", "''")
            fixture.write_text(
                "Set-StrictMode -Version Latest\n"
                "$ErrorActionPreference='Stop'\n"
                "$tokens=$null;$errors=$null\n"
                f"$ast=[Management.Automation.Language.Parser]::ParseFile('{w19}',[ref]$tokens,[ref]$errors)\n"
                "if(@($errors).Count -ne 0){throw 'UCIE_W26_PARSER_ERROR'}\n"
                "$items=@($ast.FindAll({param($node) ($node -is [Management.Automation.Language.FunctionDefinitionAst] -and $node.Name -ceq 'Same')},$true))\n"
                "if($items.Count -ne 1){throw 'UCIE_W26_MISSING_SAME'}\n"
                "$fn=$items[0].Extent.Text\n"
                "if(-not $fn.StartsWith('function Same($action,[string]$exe,[string]$expectedArguments,[string]$work) {',[StringComparison]::Ordinal)){throw 'UCIE_W26_SIGNATURE_DRIFT'}\n"
                ". ([scriptblock]::Create($fn))\n"
                "$task=[pscustomobject]@{Execute='D:\\UCIE\\.venv\\Scripts\\python.exe';Arguments='\"D:\\UCIE\\scripts\\public_miner_cycle.py\"';WorkingDirectory='D:\\UCIE'}\n"
                "if(-not (Same $task 'D:\\UCIE\\.venv\\Scripts\\python.exe' '\"D:\\UCIE\\scripts\\public_miner_cycle.py\"' 'D:\\UCIE')){throw 'UCIE_W26_FALSE_DRIFT'}\n"
                "if(Same $task 'D:\\UCIE\\.venv\\Scripts\\python.exe' '\"D:\\UCIE\\scripts\\WRONG.py\"' 'D:\\UCIE'){throw 'UCIE_W26_FALSE_MATCH'}\n"
                "Write-Output 'UCIE_W26_AST_EXACT_SAME_PASS__NO_HOST_TASKS'\n",
                encoding="utf-8",
            )
            cmd = [shell, "-NoProfile", "-NonInteractive"]
            if os.name == "nt":
                cmd.extend(["-ExecutionPolicy", "Bypass"])
            cmd.extend(["-File", str(fixture)])
            result = subprocess.run(cmd, text=True, capture_output=True, timeout=30)
            self.assertEqual(result.returncode, 0,
                             result.stdout + result.stderr)
            self.assertIn("UCIE_W26_AST_EXACT_SAME_PASS__NO_HOST_TASKS",
                          result.stdout)


if __name__ == "__main__":
    unittest.main()
