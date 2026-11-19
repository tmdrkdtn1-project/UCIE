"""W27 native PS simulation of W21 pre-rebind, record-only rollback gate.

No Windows Task Scheduler, SQLite, C40, owner archive or local endpoint calls.
Extract and execute exactly the pure W21 function bodies on disposable data.
"""
from __future__ import annotations
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
W21 = ROOT / "scripts" / "ucie_owner_w21_single_local_maintenance_v01.ps1"


def shell() -> str | None:
    return "powershell.exe" if os.name == "nt" else shutil.which("pwsh")


def execute_file(path: Path) -> subprocess.CompletedProcess[str]:
    ps = shell()
    assert ps
    cmd = [ps, "-NoProfile", "-NonInteractive"]
    if os.name == "nt":
        cmd += ["-ExecutionPolicy", "Bypass"]
    return subprocess.run(cmd + ["-File", str(path)], capture_output=True,
                          text=True, timeout=30, check=False)


def extract_source() -> str:
    return f"""
Set-StrictMode -Version Latest
$ErrorActionPreference='Stop'
$tokens=$null;$errors=$null
$ast=[Management.Automation.Language.Parser]::ParseFile('{str(W21).replace("'", "''")}',[ref]$tokens,[ref]$errors)
if(@($errors).Count -ne 0){{throw 'UCIE_W27_W21_PARSE_FAILED'}}
function SourceFunction([string]$name){{
  $found=@($ast.FindAll({{param($n) ($n -is [Management.Automation.Language.FunctionDefinitionAst] -and $n.Name -ceq $name)}},$true))
  if($found.Count -ne 1){{throw 'UCIE_W27_SOURCE_FUNCTION_MISSING'}}
  . ([scriptblock]::Create($found[0].Extent.Text))
}}
"""


class W27PreRebindRollbackGateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.code = W21.read_text("utf-8")

    def test_no_stage_branch_guard_and_record_fields(self):
        s = self.code
        begin = s.index("function AssertPreRebindNoStage {")
        end = s.index("function C40Hash {", begin)
        section = s[begin:end]
        for value in ("$w19Journal", "$w13Journal", "$w20Journal",
                      "$w20Rollback", "$w19Rollback", "$marker",
                      "$privateData", "$targetRuntime", "OriginalDisabled",
                      "UCIE_W27_PRE_REBIND_C40_ACTION_DRIFT_HOLD"):
            with self.subTest(value=value):
                self.assertIn(value, section)
        self.assertIn("AssertPreRebindNoStage\n    $rollbackPhase=", s)
        self.assertIn("W27_PRE_REBIND_ORIGINAL_DISABLED_NO_DATA_STAGE", s)
        self.assertIn("rollback_phase=$rollbackPhase", s)
        self.assertIn("pre_rebind_no_w19_stage=", s)
        self.assertIn("new_private_sqlite_kept=($rollbackPhase -cne", s)
        self.assertIn("UCIE_W21_EXPLICIT_OWNER_MAINTENANCE_APPROVAL_REQUIRED", s)
        self.assertIn("UCIE_W21_ROLLBACK_INTENT_INVALID", s)
        self.assertLess(s.index("AssertPreRebindNoStage\n    $rollbackPhase="),
                        s.index("SavePrivate $rollbackReceipt ([ordered]@{"))
        self.assertNotIn("Remove-Item -LiteralPath $journal", s)
        self.assertNotIn("Stop-Process", s)

    def test_native_powershell_guard_synthetic_positive_and_negatives(self):
        if not shell():
            self.skipTest("Native PowerShell unavailable")
        with tempfile.TemporaryDirectory(prefix="ucie_w27_guards_") as td:
            p = Path(td) / "w21_guard.ps1"
            code = extract_source() + r"""
$w19Journal='w19';$w13Journal='w13';$w20Journal='w20'
$w20Rollback='w20rb';$w19Rollback='w19rb';$marker='marker'
$privateData='data';$targetRuntime='runtime'
$script:present=@{};$script:tasksDisabled=$true
$script:currentC40='BASE';$c40Before='BASE'
function Absent([string]$path){if($script:present.ContainsKey($path)){throw 'UCIE_W27_PARTIAL_STAGE_FOUND'}}
function OriginalDisabled{if(-not $script:tasksDisabled){throw 'UCIE_W27_ORIGINAL_TASK_ACTION_OR_DISABLED_DRIFT'}}
function C40Hash {return $script:currentC40}
# SourceFunction's dot-source scope is local, so extract directly in this scope.
$fun=@($ast.FindAll({param($n) ($n -is [Management.Automation.Language.FunctionDefinitionAst] -and $n.Name -ceq 'AssertPreRebindNoStage')},$true))
if($fun.Count -ne 1){throw 'UCIE_W27_GUARD_MISSING'}
. ([scriptblock]::Create($fun[0].Extent.Text))
function Case([string]$label,[string]$expected){
  $actual='PASS'
  try{AssertPreRebindNoStage}catch{$actual=[string]$_.Exception.Message}
  if($actual -cne $expected){throw ('UCIE_W27_BAD_DECISION_'+$label+'_'+$actual)}
}
Case 'exact' 'PASS'
$script:present['w19']=$true;Case 'w19' 'UCIE_W27_PARTIAL_STAGE_FOUND';$script:present.Remove('w19')
$script:present['runtime']=$true;Case 'runtime' 'UCIE_W27_PARTIAL_STAGE_FOUND';$script:present.Remove('runtime')
$script:present['marker']=$true;Case 'marker' 'UCIE_W27_PARTIAL_STAGE_FOUND';$script:present.Remove('marker')
$script:tasksDisabled=$false;Case 'old-drift' 'UCIE_W27_ORIGINAL_TASK_ACTION_OR_DISABLED_DRIFT';$script:tasksDisabled=$true
$script:currentC40='DRIFT';Case 'c40-drift' 'UCIE_W27_PRE_REBIND_C40_ACTION_DRIFT_HOLD'
Write-Output 'UCIE_W27_GUARD_TEST_POSITIVE_NEGATIVE_PASS'
"""
            p.write_text(code, encoding="utf-8")
            r = execute_file(p)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            self.assertIn("UCIE_W27_GUARD_TEST_POSITIVE_NEGATIVE_PASS", r.stdout)

    def test_w21_action_equals_pure_function_on_synthetic_fixture(self):
        if not shell():
            self.skipTest("Native PowerShell unavailable")
        with tempfile.TemporaryDirectory(prefix="ucie_w27_action_") as td:
            p = Path(td) / "w21_action.ps1"
            code = extract_source() + r"""
$fn=@($ast.FindAll({param($n) ($n -is [Management.Automation.Language.FunctionDefinitionAst] -and $n.Name -ceq 'ActionEquals')},$true))
if($fn.Count -ne 1){throw 'UCIE_W27_ACTION_EQUALS_NOT_FOUND'}
. ([scriptblock]::Create($fn[0].Extent.Text))
$old='D:\UCIE';$root='D:\UCIE_PROJECT\UCIE'
$spec=[pscustomobject]@{OldExe='D:\UCIE\.venv\Scripts\python.exe';OldArgs='"D:\UCIE\scripts\public_miner_cycle.py"';NewExe='D:\UCIE_PROJECT\UCIE\.venv\Scripts\python.exe';NewArgs='"D:\UCIE_PROJECT\UCIE\scripts\public_miner_cycle.py" --owner-relocated-runtime'}
$task=[pscustomobject]@{Actions=@([pscustomobject]@{Execute=$spec.OldExe;Arguments=$spec.OldArgs;WorkingDirectory=$old})}
if(-not (ActionEquals $task $spec $false)){throw 'UCIE_W27_FALSE_DRIFT'}
$task.Actions[0].Arguments='INCORRECT'
if(ActionEquals $task $spec $false){throw 'UCIE_W27_FALSE_MATCH'}
Write-Output 'UCIE_W27_W21_ACTION_EQUALS_SYNTHETIC_PASS'
"""
            p.write_text(code, encoding="utf-8")
            r = execute_file(p)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            self.assertIn("UCIE_W27_W21_ACTION_EQUALS_SYNTHETIC_PASS", r.stdout)

    def test_original_w21_default_and_missing_approval_denials(self):
        if not shell():
            self.skipTest("Native PowerShell unavailable")
        with tempfile.TemporaryDirectory(prefix="ucie_w27_decline_") as td:
            p = Path(td) / "contract.ps1"
            quoted = str(W21).replace("'", "''")
            p.write_text(
                f"$t=$null;$e=$null;[Management.Automation.Language.Parser]::ParseFile('{quoted}',[ref]$t,[ref]$e)|Out-Null;"
                "if(@($e).Count -gt 0){$e|ForEach-Object{$_.Message};exit 2};exit 0",
                encoding="utf-8")
            ps = shell()
            assert ps
            parse = subprocess.run([ps, "-NoProfile", "-NonInteractive",
                                    "-File", str(p)], text=True,
                                   capture_output=True, timeout=30)
            self.assertEqual(parse.returncode, 0, parse.stdout + parse.stderr)
        ps = shell()
        cmd = [ps, "-NoProfile", "-NonInteractive"]
        if os.name == "nt":
            cmd += ["-ExecutionPolicy", "Bypass"]
        cmd += ["-File", str(W21)]
        safe = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        self.assertEqual(safe.returncode, 0, safe.stdout + safe.stderr)
        self.assertIn("UCIE_W21_CONTRACT_ONLY_NO_HOST_ACCESS", safe.stdout)
        deny = subprocess.run(cmd + ["-RollbackLocal"], capture_output=True,
                              text=True, timeout=30)
        self.assertNotEqual(deny.returncode, 0)
        self.assertIn("UCIE_W21_EXPLICIT_OWNER_MAINTENANCE_APPROVAL_REQUIRED",
                      deny.stdout + deny.stderr)


if __name__ == "__main__":
    unittest.main()
