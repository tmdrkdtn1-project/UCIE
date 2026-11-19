"""W30 actual first-party functions on disposable in-memory PowerShell mocks.

No owner Windows, real ScheduledTasks, protected archive, localhost, C40 or
SQLite contact. Actual W29 RestoreOld function is AST-extracted together with
actual W30 candidate, receipt lineage, and recovery flow for failure injection.
"""
from __future__ import annotations

import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
W29 = ROOT / "scripts" / "ucie_owner_w29_oldroot_rehearsal_restore_v01.ps1"
W30 = ROOT / "scripts" / "ucie_owner_w30_secondary_oldroot_restore_v01.ps1"


def ps_shell() -> str | None:
    return "powershell.exe" if os.name == "nt" else shutil.which("pwsh")


def invoke(code: str) -> subprocess.CompletedProcess[str]:
    ps = ps_shell()
    assert ps is not None
    with tempfile.TemporaryDirectory(prefix="ucie_w30_inmemory_") as tmp:
        path = Path(tmp) / "inmemory.ps1"
        path.write_text(code, encoding="utf-8")
        args = [ps, "-NoProfile", "-NonInteractive"]
        if os.name == "nt":
            args += ["-ExecutionPolicy", "Bypass"]
        return subprocess.run(
            args + ["-File", str(path)],
            capture_output=True, text=True, timeout=45, check=False,
        )


def setup() -> str:
    w29 = str(W29).replace("'", "''")
    w30 = str(W30).replace("'", "''")
    return rf"""
Set-StrictMode -Version Latest
$ErrorActionPreference='Stop'
foreach($src in @('{w29}','{w30}')){{
  $tokens=$null;$errors=$null
  $ast=[Management.Automation.Language.Parser]::ParseFile($src,[ref]$tokens,[ref]$errors)
  if(@($errors).Count -ne 0){{throw 'UCIE_W30_AST_PARSE_FAILED'}}
  $functionNames=if($src -ceq '{w29}'){{@('InvokeW29RestoreOld')}}else{{
      @('VerifyW29FailedRecovery','CheckRecoveryCandidate','VerifyOldRestored',
        'ValidateW30InitialIntent','InvokeW30JournaledRecovery')
  }}
  foreach($name in $functionNames){{
    $found=@($ast.FindAll({{param($n)
        ($n -is [Management.Automation.Language.FunctionDefinitionAst] -and
         $n.Name -ceq $name)}},$true))
    if($found.Count -ne 1){{throw 'UCIE_W30_CORE_FUNCTION_NOT_UNIQUE'}}
    . ([scriptblock]::Create($found[0].Extent.Text))
  }}
}}
$names=@('UCIE-PublicMiner-Hourly','UCIE-Internal-Minute','UCIE-LocalV1-Web')
$schema='UCIE_W30_OWNER_SECONDARY_OLDROOT_RESTORE_V01'
$w29Schema='UCIE_W29_OWNER_OLDROOT_REHEARSAL_AND_RESTORE_V01'
$priorW29Intent='W29_INTENT';$priorW29Recovery='W29_RECOVERY'
$priorW29Restored='W29_RESTORED'
$w30Intent='W30_INTENT';$w30Retry='W30_RETRY';$w30Restored='W30_RESTORED'
$script:ownerSid='SYNTHETIC_OWNER'
$script:states=@('Disabled','Disabled','Disabled')
$script:actionValid=@($true,$true,$true)
$script:port='FREE';$script:http=$false
$script:c40='BASE';$script:stage=$false
$script:failEnable='';$script:failStart=$false
$script:log=[System.Collections.Generic.List[string]]::new()
$script:receipts=@{{}}
$script:receipts[$priorW29Intent]=[pscustomobject]@{{
    schema=$w29Schema;status='UCIE_W29_OWNER_REHEARSAL_INTENT'
    owner_sid_sha256='MOCK_HASH';c40_action_sha256='BASE'
    original_old_actions_verified=$true;sqlite_copy_or_task_rebind_authorized=$false
    full_cutover_authorized=$false
    original_task_names=@($names);original_task_states=@('Ready','Ready','Running')
}}
$script:receipts[$priorW29Recovery]=[pscustomobject]@{{
    schema=$w29Schema;status='UCIE_W29_OWNER_OLD_RESTORE_INTENT'
    owner_sid_sha256='MOCK_HASH';c40_action_sha256='BASE'
    original_old_task_actions_verified=$true;full_cutover_authorized=$false
}}
function ShaText([string]$value){{return 'MOCK_HASH'}}
function Absent([string]$path){{
    if($script:receipts.ContainsKey($path)){{
        throw 'UCIE_W30_ALREADY_EXISTS_NO_BLIND_RETRY'
    }}
}}
function ReadBounded([string]$path){{
    if(-not $script:receipts.ContainsKey($path)){{
        throw 'UCIE_W30_MISSING_PRIOR_RECEIPT'
    }}
    return $script:receipts[$path]
}}
function SaveW30([string]$path,$value){{
    Absent $path
    $script:receipts[$path]=[pscustomobject]$value
    $script:log.Add('SAVE_'+$path)
}}
function AssertNoStagedData{{
    if($script:stage){{throw 'UCIE_W30_STAGED_OUTPUT_PRESENT'}}
}}
function CheckOld([int]$i){{
    if(-not $script:actionValid[$i]){{throw 'UCIE_W30_OLD_ACTION_MISMATCH'}}
    return [pscustomobject]@{{State=$script:states[$i]}}
}}
function C40Hash{{return $script:c40}}
function PortState{{return $script:port}}
function HealthyOld{{return $script:http}}
function WaitHealthyOld{{
    return ($script:states[2] -ceq 'Running' -and
            $script:port -ceq 'ONE_LOOPBACK_LISTENER' -and $script:http)
}}
function Enable-ScheduledTask {{
    [CmdletBinding()]
    param([string]$TaskPath,[string]$TaskName)
    if($script:failEnable -ceq $TaskName){{
        throw 'UCIE_W30_INJECTED_ENABLE_DENIED'
    }}
    $i=[array]::IndexOf($names,$TaskName)
    if($i -lt 0){{throw 'UCIE_W30_UNKNOWN_TASK_DENIED'}}
    $script:states[$i]='Ready'
    $script:log.Add('ENABLE_'+$TaskName)
}}
function Start-ScheduledTask {{
    [CmdletBinding()]
    param([string]$TaskPath,[string]$TaskName)
    if($TaskName -cne $names[2]){{throw 'UCIE_W30_WRITER_FORCE_START_DENIED'}}
    if($script:failStart){{throw 'UCIE_W30_INJECTED_START_DENIED'}}
    $script:states[2]='Running'
    $script:port='ONE_LOOPBACK_LISTENER'
    $script:http=$true
    $script:log.Add('START_LOCAL')
}}
"""


class W30SecondaryRestoreNativeSyntheticTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = W30.read_text("utf-8")

    def native(self, code: str) -> str:
        if not ps_shell():
            self.skipTest("Native PowerShell unavailable")
        result = invoke(setup() + code)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        return result.stdout

    def test_default_no_host_and_owner_approval_denial(self):
        if not ps_shell():
            self.skipTest("Native PowerShell unavailable")
        sh = ps_shell()
        args = [sh, "-NoProfile", "-NonInteractive"]
        if os.name == "nt":
            args += ["-ExecutionPolicy", "Bypass"]
        args += ["-File", str(W30)]
        default = subprocess.run(args, capture_output=True, text=True, timeout=30)
        self.assertEqual(default.returncode, 0, default.stdout + default.stderr)
        self.assertIn("UCIE_W30_CONTRACT_ONLY_NO_HOST_ACCESS", default.stdout)
        self.assertIn('"journal_written":false', default.stdout)
        denied = subprocess.run(args + ["-RecoverPartial"],
                                capture_output=True, text=True, timeout=30)
        self.assertNotEqual(denied.returncode, 0)
        self.assertIn("UCIE_W30_EXPLICIT_OWNER_MODE_APPROVAL_REQUIRED",
                      denied.stdout + denied.stderr)

    def test_exact_failed_w29_receipts_pass_but_missing_or_changed_hold(self):
        out = self.native(r"""
VerifyW29FailedRecovery 'BASE'
$script:receipts[$priorW29Recovery].c40_action_sha256='OTHER'
try{VerifyW29FailedRecovery 'BASE';throw 'UCIE_W30_ACCEPTED_BAD_W29'}
catch{if($_.Exception.Message -cne 'UCIE_W30_FAILED_W29_RECEIPT_LINEAGE_HOLD'){throw}}
$script:receipts[$priorW29Recovery].c40_action_sha256='BASE'
$script:receipts[$priorW29Restored]=[pscustomobject]@{status='DONE'}
try{VerifyW29FailedRecovery 'BASE';throw 'UCIE_W30_ACCEPTED_COMPLETED_W29'}
catch{if($_.Exception.Message -cne 'UCIE_W30_ALREADY_EXISTS_NO_BLIND_RETRY'){throw}}
Write-Output 'UCIE_W30_W29_FAILED_RECEIPT_LINEAGE_PASS'
""")
        self.assertIn("UCIE_W30_W29_FAILED_RECEIPT_LINEAGE_PASS", out)

    def test_local_first_then_writers_and_receipt_after_both(self):
        out = self.native(r"""
[void](InvokeW30JournaledRecovery 'BASE' $w30Intent 'UCIE_W30_SECONDARY_RECOVERY_INTENT')
if(($script:states -join ',') -cne 'Ready,Ready,Running'){
    throw 'UCIE_W30_NOT_RESTORED'
}
$expected=@(
 'SAVE_W30_INTENT','ENABLE_UCIE-LocalV1-Web','START_LOCAL',
 'ENABLE_UCIE-PublicMiner-Hourly','ENABLE_UCIE-Internal-Minute','SAVE_W30_RESTORED'
)
if(($script:log -join ',') -cne ($expected -join ',')){
    throw ('UCIE_W30_WRONG_ORDER_'+($script:log -join ','))
}
Write-Output 'UCIE_W30_REAL_W29_CORE_LOCAL_BEFORE_WRITERS_PASS'
""")
        self.assertIn("UCIE_W30_REAL_W29_CORE_LOCAL_BEFORE_WRITERS_PASS", out)

    def test_partial_healthy_local_enables_only_missing_writer(self):
        out = self.native(r"""
$script:states=@('Ready','Disabled','Running')
$script:port='ONE_LOOPBACK_LISTENER';$script:http=$true
[void](InvokeW30JournaledRecovery 'BASE' $w30Intent 'UCIE_W30_SECONDARY_RECOVERY_INTENT')
$expected='SAVE_W30_INTENT,ENABLE_UCIE-Internal-Minute,SAVE_W30_RESTORED'
if(($script:log -join ',') -cne $expected){
    throw 'UCIE_W30_RESTARTED_HEALTHY_LOCAL_OR_WRITER'
}
Write-Output 'UCIE_W30_REAL_W29_CORE_PARTIAL_WRITER_RESTORE_PASS'
""")
        self.assertIn("UCIE_W30_REAL_W29_CORE_PARTIAL_WRITER_RESTORE_PASS", out)

    def test_refuses_foreign_port_stage_c40_action_or_invalid_local_state_prewrite(self):
        out = self.native(r"""
function ExpectHold([string]$why){
 $before=$script:log.Count
 try{
   [void](InvokeW30JournaledRecovery 'BASE' $w30Intent 'UCIE_W30_SECONDARY_RECOVERY_INTENT')
   throw 'UCIE_W30_UNEXPECTED_ACCEPT'
 } catch {
   if($_.Exception.Message -cne $why){throw}
 }
 if($script:log.Count -ne $before){throw 'UCIE_W30_MUTATED_BEFORE_REJECTION'}
}
$script:port='OTHER_OR_MULTIPLE';ExpectHold 'UCIE_W30_FOREIGN_PORT_NO_UNKNOWN_PID_KILL'
$script:port='FREE';$script:stage=$true;ExpectHold 'UCIE_W30_STAGED_OUTPUT_PRESENT'
$script:stage=$false;$script:c40='OTHER';ExpectHold 'UCIE_W30_C40_CHANGED_SECONDARY_RECOVERY_HOLD'
$script:c40='BASE';$script:actionValid[0]=$false;ExpectHold 'UCIE_W30_OLD_ACTION_MISMATCH'
$script:actionValid[0]=$true;$script:states[2]='Running';ExpectHold 'UCIE_W30_LOCAL_TASK_AND_PORT_INCONSISTENT_HOLD'
Write-Output 'UCIE_W30_NO_MUTATION_ON_FOREIGN_PORT_STAGE_C40_OR_ACTION_PASS'
""")
        self.assertIn("UCIE_W30_NO_MUTATION_ON_FOREIGN_PORT_STAGE_C40_OR_ACTION_PASS", out)

    def test_first_failed_enable_then_one_validated_bounded_retry(self):
        out = self.native(r"""
$script:failEnable='UCIE-Internal-Minute'
try{
 [void](InvokeW30JournaledRecovery 'BASE' $w30Intent 'UCIE_W30_SECONDARY_RECOVERY_INTENT')
 throw 'UCIE_W30_FIRST_ATTEMPT_FALSE_SUCCESS'
}catch{if($_.Exception.Message -cne 'UCIE_W30_INJECTED_ENABLE_DENIED'){throw}}
if(-not $script:receipts.ContainsKey($w30Intent) -or
   $script:receipts.ContainsKey($w30Restored)){
    throw 'UCIE_W30_FALSE_SUCCESS_OR_NO_RECOVERY_INTENT'
}
ValidateW30InitialIntent 'BASE'
$script:failEnable=''
[void](InvokeW30JournaledRecovery 'BASE' $w30Retry 'UCIE_W30_SECONDARY_BOUNDED_RETRY_INTENT')
if(-not $script:receipts.ContainsKey($w30Retry) -or
   -not $script:receipts.ContainsKey($w30Restored)){
    throw 'UCIE_W30_RETRY_NOT_RECORDED'
}
if(($script:states -join ',') -cne 'Ready,Ready,Running'){
    throw 'UCIE_W30_RETRY_NOT_RESTORED'
}
Write-Output 'UCIE_W30_SECOND_CHANCE_PLUS_ONE_JOURNALED_RETRY_PASS'
""")
        self.assertIn("UCIE_W30_SECOND_CHANCE_PLUS_ONE_JOURNALED_RETRY_PASS", out)

    def test_failed_retry_preserves_both_attempts_no_false_restored(self):
        out = self.native(r"""
$script:failEnable='UCIE-Internal-Minute'
try{[void](InvokeW30JournaledRecovery 'BASE' $w30Intent 'UCIE_W30_SECONDARY_RECOVERY_INTENT')}
catch{if($_.Exception.Message -cne 'UCIE_W30_INJECTED_ENABLE_DENIED'){throw}}
ValidateW30InitialIntent 'BASE'
try{[void](InvokeW30JournaledRecovery 'BASE' $w30Retry 'UCIE_W30_SECONDARY_BOUNDED_RETRY_INTENT')}
catch{if($_.Exception.Message -cne 'UCIE_W30_INJECTED_ENABLE_DENIED'){throw}}
if(-not $script:receipts.ContainsKey($w30Intent) -or
   -not $script:receipts.ContainsKey($w30Retry) -or
   $script:receipts.ContainsKey($w30Restored)){
    throw 'UCIE_W30_INCOMPLETE_RETRY_RECEIPTS_INCORRECT'
}
try{[void](InvokeW30JournaledRecovery 'BASE' $w30Retry 'UCIE_W30_SECONDARY_BOUNDED_RETRY_INTENT')
    throw 'UCIE_W30_UNEXPECTED_THIRD_ATTEMPT'
}catch{
    if($_.Exception.Message -cne 'UCIE_W30_ALREADY_EXISTS_NO_BLIND_RETRY'){throw}
}
Write-Output 'UCIE_W30_TWO_FAILURES_PRESERVE_RECEIPTS_NO_THIRD_RETRY_PASS'
""")
        self.assertIn("UCIE_W30_TWO_FAILURES_PRESERVE_RECEIPTS_NO_THIRD_RETRY_PASS", out)

    def test_completed_but_w29_success_receipt_missing_can_issue_w30_receipt(self):
        out = self.native(r"""
$script:states=@('Ready','Ready','Running')
$script:port='ONE_LOOPBACK_LISTENER';$script:http=$true
[void](InvokeW30JournaledRecovery 'BASE' $w30Intent 'UCIE_W30_SECONDARY_RECOVERY_INTENT')
if(($script:log -join ',') -cne 'SAVE_W30_INTENT,SAVE_W30_RESTORED'){
    throw 'UCIE_W30_UNNECESSARY_TASK_OPERATION'
}
Write-Output 'UCIE_W30_ALREADY_HEALTHY_NO_EXTRA_TASK_MUTATION_PASS'
""")
        self.assertIn("UCIE_W30_ALREADY_HEALTHY_NO_EXTRA_TASK_MUTATION_PASS", out)

    def test_w30_pin_and_no_legacy_calls_in_source(self):
        s = self.source
        self.assertIn("ddcbb9ebc02b6908ab5f7a558f81b01a1e09d831", s)
        self.assertIn("848cb03f50dc455fc61935a484c3d71e82506c90", s)
        self.assertIn("HEAD:scripts/ucie_owner_w29_oldroot_rehearsal_restore_v01.ps1", s)
        self.assertIn("ParseFile(", s)
        self.assertIn(". ([scriptblock]::Create($functionAsts[0].Extent.Text))", s)
        self.assertIn("UCIE_W30_CONTRACT_ONLY_NO_HOST_ACCESS", s)
        self.assertIn("UCIE_W30_SECONDARY_BOUNDED_RETRY_INTENT", s)
        self.assertLess(s.index("SaveW30 $entryPath ([ordered]@{"),
                        s.index("$result=InvokeW29RestoreOld $baseline"))
        self.assertLess(s.index("VerifyOldRestored $baseline"),
                        s.index("SaveW30 $w30Restored ([ordered]@{"))
        for forbidden in (
            "Stop-ScheduledTask", "Stop-Process", "taskkill",
            "Disable-ScheduledTask", "Set-ScheduledTask",
            "Register-ScheduledTask", "Unregister-ScheduledTask",
            "sqlite3.connect", "Copy-Item", "Move-Item -LiteralPath $old",
            "-ApplyLocal", "-RollbackLocal", "& $w29",
            "git reset", "git clean",
        ):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, s)


if __name__ == "__main__":
    unittest.main()
