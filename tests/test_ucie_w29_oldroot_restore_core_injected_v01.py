"""W29 actual production PowerShell core on disposable, in-memory Task mocks.

No owner Windows Task Scheduler, private archive, C40, localhost or SQLite
access. Native PowerShell AST extracts production-only InvokeW29RestoreOld,
InvokeW29RehearsalQuiesce and InvokeW29JournaledRestore and supplies mocks.
The real owner -RehearseOld / -RecoverOld modes are NEVER invoked by CI.
"""
from __future__ import annotations

import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "scripts" / "ucie_owner_w29_oldroot_rehearsal_restore_v01.ps1"


def shell() -> str | None:
    return "powershell.exe" if os.name == "nt" else shutil.which("pwsh")


def run_ps(code: str) -> subprocess.CompletedProcess[str]:
    ps = shell()
    if not ps:
        raise RuntimeError("PowerShell unavailable")
    with tempfile.TemporaryDirectory(prefix="ucie_w29_offline_") as tmp:
        path = Path(tmp) / "isolated.ps1"
        path.write_text(code, encoding="utf-8")
        cmd = [ps, "-NoProfile", "-NonInteractive"]
        if os.name == "nt":
            cmd += ["-ExecutionPolicy", "Bypass"]
        return subprocess.run(cmd + ["-File", str(path)], capture_output=True,
                              text=True, timeout=45, check=False)


def core_setup() -> str:
    p = str(SOURCE).replace("'", "''")
    return rf"""
Set-StrictMode -Version Latest
$ErrorActionPreference='Stop'
$tokens=$null;$errors=$null
$ast=[Management.Automation.Language.Parser]::ParseFile('{p}',[ref]$tokens,[ref]$errors)
if(@($errors).Count -ne 0){{throw 'UCIE_W29_NATIVE_SOURCE_PARSE_HOLD'}}
foreach($fnName in @('InvokeW29RestoreOld','InvokeW29RehearsalQuiesce','InvokeW29JournaledRestore')){{
  $found=@($ast.FindAll({{param($node)
      ($node -is [Management.Automation.Language.FunctionDefinitionAst] -and
       $node.Name -ceq $fnName)}},$true))
  if($found.Count -ne 1){{throw 'UCIE_W29_FUNCTION_NAME_UNIQUE_HOLD'}}
  . ([scriptblock]::Create($found[0].Extent.Text))
}}
$names=@('UCIE-PublicMiner-Hourly','UCIE-Internal-Minute','UCIE-LocalV1-Web')
$script:states=@('Disabled','Disabled','Disabled')
$script:port='FREE'
$script:http=$false
$script:c40='BASE'
$script:stagePresent=$false
$script:failEnableTask=''
$script:failStop=$false
$script:failStart=$false
$script:log=[System.Collections.Generic.List[string]]::new()
$script:receipts=@{{}}
$schema='UCIE_W29_OWNER_OLDROOT_REHEARSAL_AND_RESTORE_V01'
$recoveryIntent='W29_RECOVERY_INTENT'
$restored='W29_RESTORED'
$script:ownerSid='S-1-5-21-SYNTHETIC-OWNER'
function ShaText([string]$value){{return 'SYNTHETIC_HASH'}}
function AssertNoStagedData{{if($script:stagePresent){{throw 'UCIE_W29_SIMULATED_STAGE_RESIDUE'}}}}
function CheckOld([int]$idx){{
    if($idx -lt 0 -or $idx -gt 2){{throw 'UCIE_W29_UNKNOWN_MOCK_TASK'}}
    return [pscustomobject]@{{State=$script:states[$idx]}}
}}
function C40Hash {{return $script:c40}}
function PortState {{return $script:port}}
function HealthyOld {{return $script:http}}
function WaitHealthyOld{{
    return ($script:states[2] -eq 'Running' -and
            $script:port -eq 'ONE_LOOPBACK_LISTENER' -and $script:http)
}}
function WaitFreePort {{return ($script:port -eq 'FREE')}}
function ReadW29Intent([string]$baseline){{
    if($baseline -ne 'BASE'){{throw 'UCIE_W29_BAD_INTENT_BASELINE'}}
    $script:log.Add('INTENT_VERIFIED')
}}
function Absent([string]$path){{
    if($script:receipts.ContainsKey($path)){{throw 'UCIE_W29_EXISTING_RECEIPT_NO_RETRY'}}
}}
function SavePrivate([string]$path,$value){{
    Absent $path
    $script:receipts[$path]=$value
    $script:log.Add('RECEIPT_'+$path)
}}
function Enable-ScheduledTask {{
    [CmdletBinding()]
    param([string]$TaskPath,[string]$TaskName)
    if($script:failEnableTask -ceq $TaskName){{
        throw 'UCIE_W29_SIMULATED_ENABLE_DENIED'
    }}
    $idx=[array]::IndexOf($names,$TaskName)
    if($idx -lt 0){{throw 'UCIE_W29_OTHER_PROJECT_TASK_DENIED'}}
    $script:states[$idx]='Ready'
    $script:log.Add('ENABLE_'+$TaskName)
}}
function Start-ScheduledTask {{
    [CmdletBinding()]
    param([string]$TaskPath,[string]$TaskName)
    if($TaskName -cne $names[2]){{
        throw 'UCIE_W29_SIMULATED_WRITER_FORCE_START_DENIED'
    }}
    if($script:failStart){{
        throw 'UCIE_W29_SIMULATED_START_FAILURE'
    }}
    $script:states[2]='Running'
    $script:port='ONE_LOOPBACK_LISTENER'
    $script:http=$true
    $script:log.Add('START_OLD_LOCAL')
}}
function Disable-ScheduledTask {{
    [CmdletBinding()]
    param([string]$TaskPath,[string]$TaskName)
    $idx=[array]::IndexOf($names,$TaskName)
    if($idx -lt 0){{throw 'UCIE_W29_UNKNOWN_QUIESCE_TASK'}}
    if($script:failEnableTask -ceq $TaskName){{
        throw 'UCIE_W29_SIMULATED_DISABLE_DENIED'
    }}
    $script:states[$idx]='Disabled'
    $script:log.Add('DISABLE_'+$TaskName)
}}
function Stop-ScheduledTask {{
    [CmdletBinding()]
    param([string]$TaskPath,[string]$TaskName)
    if($TaskName -cne $names[2]){{
        throw 'UCIE_W29_SIMULATED_OTHER_PROCESS_STOP_DENIED'
    }}
    if($script:failStop){{throw 'UCIE_W29_SIMULATED_STOP_DENIED'}}
    $script:port='FREE';$script:http=$false
    $script:log.Add('STOP_OLD_LOCAL_ONLY')
}}
"""


class W29NoHostRecoveryCoreNativeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = SOURCE.read_text(encoding="utf-8")

    def native(self, extra: str, *, success: bool = True) -> str:
        if not shell():
            self.skipTest("Native PowerShell unavailable")
        result = run_ps(core_setup() + extra)
        if success:
            self.assertEqual(result.returncode, 0,
                             result.stdout + result.stderr)
        else:
            self.assertNotEqual(result.returncode, 0)
        return result.stdout + result.stderr

    def test_native_powershell_parser_contract_only_and_unauthorized_denial(self):
        if not shell():
            self.skipTest("Native PowerShell unavailable")
        ps = shell()
        cmd = [ps, "-NoProfile", "-NonInteractive"]
        if os.name == "nt":
            cmd += ["-ExecutionPolicy", "Bypass"]
        cmd += ["-File", str(SOURCE)]
        contract = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        self.assertEqual(contract.returncode, 0,
                         contract.stdout + contract.stderr)
        self.assertIn("UCIE_W29_CONTRACT_ONLY_NO_HOST_ACCESS", contract.stdout)
        self.assertIn('"task_scheduler_changed":false', contract.stdout)
        self.assertIn('"private_archive_read":false', contract.stdout)
        denied = subprocess.run(cmd + ["-RehearseOld"], capture_output=True,
                                text=True, timeout=30)
        self.assertNotEqual(denied.returncode, 0)
        self.assertIn("UCIE_W29_EXPLICIT_MODE_SPECIFIC_OWNER_APPROVAL_REQUIRED",
                      denied.stdout + denied.stderr)

    def test_restore_from_three_disabled_tasks_starts_local_before_writers(self):
        out = self.native(r"""
$result=InvokeW29RestoreOld 'BASE'
if($result -cne 'STARTED_OLD_LOCAL_AND_HTTP_HEALTHY'){throw 'UCIE_W29_BAD_LOCAL_RESULT'}
if(($script:states -join ',') -cne 'Ready,Ready,Running'){throw 'UCIE_W29_NOT_FULLY_RESTORED'}
$expect=@(
 'ENABLE_UCIE-LocalV1-Web','START_OLD_LOCAL',
 'ENABLE_UCIE-PublicMiner-Hourly','ENABLE_UCIE-Internal-Minute'
)
if(($script:log -join ',') -cne ($expect -join ',')){
    throw 'UCIE_W29_RECOVERY_ORDER_INCORRECT'
}
Write-Output 'UCIE_W29_REAL_CORE_MOCK_RESTORE_ORDER_PASS'
""")
        self.assertIn("UCIE_W29_REAL_CORE_MOCK_RESTORE_ORDER_PASS", out)

    def test_restore_from_partial_disabled_writers_old_local_already_healthy(self):
        out = self.native(r"""
$script:states=@('Disabled','Ready','Running')
$script:port='ONE_LOOPBACK_LISTENER';$script:http=$true
$result=InvokeW29RestoreOld 'BASE'
if($result -cne 'ALREADY_RUNNING_OLD_HTTP_HEALTHY'){throw 'UCIE_W29_BAD_EXISTING_HEALTH'}
if(($script:log -join ',') -cne 'ENABLE_UCIE-PublicMiner-Hourly'){
    throw 'UCIE_W29_REDUNDANT_LOCAL_RESTART_OR_WRITER_MUTATION'
}
Write-Output 'UCIE_W29_REAL_CORE_MOCK_PARTIAL_RESTORE_PASS'
""")
        self.assertIn("UCIE_W29_REAL_CORE_MOCK_PARTIAL_RESTORE_PASS", out)

    def test_foreign_port_refuses_restore_without_mutation(self):
        out = self.native(r"""
$script:port='FOREIGN_OR_MULTIPLE_HOLD'
try{
  [void](InvokeW29RestoreOld 'BASE')
  throw 'UCIE_W29_SIMULATION_EXPECTED_HOLD_MISSING'
}catch{
  if($_.Exception.Message -cne 'UCIE_W29_FOREIGN_LISTENER_NO_UNKNOWN_PID_KILL'){throw}
}
if($script:log.Count -ne 0){throw 'UCIE_W29_FOREIGN_PORT_TASK_MUTATION'}
Write-Output 'UCIE_W29_REAL_CORE_MOCK_FOREIGN_PORT_FAIL_CLOSED_PASS'
""")
        self.assertIn("UCIE_W29_REAL_CORE_MOCK_FOREIGN_PORT_FAIL_CLOSED_PASS", out)

    def test_staged_data_or_c40_drift_refuses_restore_without_mutation(self):
        out = self.native(r"""
$script:stagePresent=$true
try{[void](InvokeW29RestoreOld 'BASE');throw 'UCIE_W29_BAD_STAGE_ACCEPTED'}
catch{if($_.Exception.Message -cne 'UCIE_W29_SIMULATED_STAGE_RESIDUE'){throw}}
$script:stagePresent=$false;$script:c40='CHANGED'
try{[void](InvokeW29RestoreOld 'BASE');throw 'UCIE_W29_BAD_C40_ACCEPTED'}
catch{if($_.Exception.Message -cne 'UCIE_W29_C40_ACTION_CHANGED_BEFORE_RESTORE'){throw}}
if($script:log.Count -ne 0){throw 'UCIE_W29_STAGE_OR_C40_TASK_MUTATION'}
Write-Output 'UCIE_W29_REAL_CORE_MOCK_STAGE_AND_C40_FAIL_CLOSED_PASS'
""")
        self.assertIn("UCIE_W29_REAL_CORE_MOCK_STAGE_AND_C40_FAIL_CLOSED_PASS", out)

    def test_journal_persists_before_any_restore_mutation_and_never_overwrites(self):
        out = self.native(r"""
$result=InvokeW29JournaledRestore 'BASE'
if(-not $script:receipts.ContainsKey('W29_RECOVERY_INTENT') -or
   -not $script:receipts.ContainsKey('W29_RESTORED')){
    throw 'UCIE_W29_JOURNAL_MISSING_AFTER_RESTORE'
}
$seq=$script:log -join ','
if($seq.IndexOf('RECEIPT_W29_RECOVERY_INTENT') -gt $seq.IndexOf('ENABLE_UCIE-LocalV1-Web')){
    throw 'UCIE_W29_FIRST_MUTATION_BEFORE_JOURNAL'
}
if($seq.IndexOf('RECEIPT_W29_RESTORED') -lt $seq.IndexOf('ENABLE_UCIE-Internal-Minute')){
    throw 'UCIE_W29_RESTORED_RECEIPT_TOO_EARLY'
}
try{[void](InvokeW29JournaledRestore 'BASE');throw 'UCIE_W29_REPLAY_SHOULD_FAIL'}
catch{if($_.Exception.Message -cne 'UCIE_W29_EXISTING_RECEIPT_NO_RETRY'){throw}}
Write-Output 'UCIE_W29_REAL_CORE_MOCK_JOURNAL_BEFORE_MUTATION_AND_REPLAY_HOLD_PASS'
""")
        self.assertIn("UCIE_W29_REAL_CORE_MOCK_JOURNAL_BEFORE_MUTATION_AND_REPLAY_HOLD_PASS", out)

    def test_restore_failure_mid_writer_preserves_recovery_intent_no_false_receipt(self):
        out = self.native(r"""
$script:failEnableTask='UCIE-Internal-Minute'
try{[void](InvokeW29JournaledRestore 'BASE');throw 'UCIE_W29_UNEXPECTED_COMPLETION'}
catch{if($_.Exception.Message -cne 'UCIE_W29_SIMULATED_ENABLE_DENIED'){throw}}
if(-not $script:receipts.ContainsKey('W29_RECOVERY_INTENT')){
    throw 'UCIE_W29_MISSING_DURABLE_RECOVERY_INTENT'
}
if($script:receipts.ContainsKey('W29_RESTORED')){
    throw 'UCIE_W29_FALSE_RESTORED_RECEIPT'
}
try{[void](InvokeW29JournaledRestore 'BASE');throw 'UCIE_W29_BAD_RETRY'}
catch{if($_.Exception.Message -cne 'UCIE_W29_EXISTING_RECEIPT_NO_RETRY'){throw}}
Write-Output 'UCIE_W29_REAL_CORE_MOCK_RECOVERY_FAILURE_NO_REPLAY_PASS'
""")
        self.assertIn("UCIE_W29_REAL_CORE_MOCK_RECOVERY_FAILURE_NO_REPLAY_PASS", out)

    def test_quiesce_stops_only_old_local_after_three_disabled(self):
        out = self.native(r"""
$script:states=@('Ready','Ready','Running')
$script:port='ONE_LOOPBACK_LISTENER';$script:http=$true
InvokeW29RehearsalQuiesce 'BASE'
if(($script:states -join ',') -cne 'Disabled,Disabled,Disabled'){
    throw 'UCIE_W29_QUIESCE_DID_NOT_DISABLE_THREE'
}
if($script:port -cne 'FREE'){throw 'UCIE_W29_OLD_PORT_NOT_RELEASED'}
$expected=@(
 'DISABLE_UCIE-PublicMiner-Hourly','DISABLE_UCIE-Internal-Minute',
 'DISABLE_UCIE-LocalV1-Web','STOP_OLD_LOCAL_ONLY'
)
if(($script:log -join ',') -cne ($expected -join ',')){
    throw 'UCIE_W29_UNEXPECTED_STOP_ACTIONS'
}
Write-Output 'UCIE_W29_REAL_CORE_MOCK_QUIESCE_EXACT_THREE_PASS'
""")
        self.assertIn("UCIE_W29_REAL_CORE_MOCK_QUIESCE_EXACT_THREE_PASS", out)

    def test_partially_quiesced_state_can_restore_without_killing_process(self):
        out = self.native(r"""
$script:states=@('Ready','Ready','Running')
$script:port='ONE_LOOPBACK_LISTENER';$script:http=$true
$script:failEnableTask='UCIE-Internal-Minute'
try{InvokeW29RehearsalQuiesce 'BASE';throw 'UCIE_W29_EXPECTED_QUIESCE_FAIL'}
catch{if($_.Exception.Message -cne 'UCIE_W29_SIMULATED_DISABLE_DENIED'){throw}}
$script:failEnableTask=''
$result=InvokeW29RestoreOld 'BASE'
if($result -cne 'ALREADY_RUNNING_OLD_HTTP_HEALTHY'){throw 'UCIE_W29_LOCAL_SHOULD_BE_HEALTHY'}
if(($script:states -join ',') -cne 'Ready,Ready,Running'){
    throw 'UCIE_W29_FAILED_RESTORE_AFTER_FIRST_DISABLE'
}
Write-Output 'UCIE_W29_REAL_CORE_MOCK_QUIESCE_FAIL_RECOVER_PASS'
""")
        self.assertIn("UCIE_W29_REAL_CORE_MOCK_QUIESCE_FAIL_RECOVER_PASS", out)

    def test_code_does_not_copy_sqlite_or_mutate_c40_or_run_legacy_owner_apply(self):
        s = self.source
        for forbidden in (
            "Stop-Process", "taskkill", "sqlite3.connect", "VACUUM",
            "Copy-Item", "Move-Item -LiteralPath $old",
            "Set-ScheduledTask", "Register-ScheduledTask",
            "Unregister-ScheduledTask", "-ApplyLocal", "-RollbackLocal",
            "& $w19", "& $w21", "& $w22", "& $w24",
        ):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, s)
        self.assertIn("UCIE_W29_OWNER_REHEARSAL_INTENT", s)
        self.assertIn("UCIE_W29_OWNER_OLD_RESTORE_INTENT", s)
        self.assertIn("UCIE_W29_OLD_ROOT_LOCAL_HTTP_AND_TWO_WRITERS_RESTORED", s)
        self.assertIn("UCIE_W29_REHEARSAL_RECOVERY_HOLD_KEEP_ALL_RECEIPTS_NO_BLIND_RETRY", s)
        self.assertIn("$needed=if($OwnerPreflightReadOnly)", s)
        self.assertIn("UCIE_W29_OWNER_ELEVATED_TOKEN_REQUIRED_BEFORE_HOST_ACCESS", s)
        self.assertIn("UCIE_W29_PRIVATE_ARCHIVE_SAME_OWNER_ACL_HOLD", s)
        self.assertIn("AssertNoStagedData", s)
        self.assertIn("full_cutover_authorized=$false", s)
        self.assertIn("c40_mcp_round_trip_verified=$false", s)


if __name__ == "__main__":
    unittest.main()
