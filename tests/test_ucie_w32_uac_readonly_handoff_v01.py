"""W32 exact W31 read-only UAC helper with native PowerShell mocked RunAs.

Tests AST-extract ACTUAL production UAC command builder and handoff core,
replace Start-Process with a disposable in-memory fake, and NEVER trigger
Windows UAC or any Task Scheduler/SQLite/C40/owner private access.
"""
from __future__ import annotations

import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "scripts" / "ucie_owner_w31_local_listener_pid_readonly_v01.ps1"


def shell() -> str | None:
    return "powershell.exe" if os.name == "nt" else shutil.which("pwsh")


def run_mock(script: str) -> subprocess.CompletedProcess[str]:
    program = shell()
    if not program:
        raise RuntimeError("Native PowerShell unavailable")
    with tempfile.TemporaryDirectory(prefix="ucie_w32_readonly_uac_mock_") as td:
        path = Path(td) / "in_memory_uac.ps1"
        path.write_text(script, encoding="utf-8")
        args = [program, "-NoProfile", "-NonInteractive"]
        if os.name == "nt":
            args.extend(["-ExecutionPolicy", "Bypass"])
        return subprocess.run(args + ["-File", str(path)],
                              capture_output=True, text=True, timeout=35)


def setup() -> str:
    source = str(SOURCE).replace("'", "''")
    return rf"""
Set-StrictMode -Version Latest
$ErrorActionPreference='Stop'
$tok=$null;$err=$null
$ast=[Management.Automation.Language.Parser]::ParseFile('{source}',[ref]$tok,[ref]$err)
if(@($err).Count -gt 0){{throw 'UCIE_W32_PRODUCTION_PS_PARSE_HOLD'}}
foreach($fn in @('NewReadOnlyUacArguments','InvokeReadOnlyUacHandoff','GetTrustedWindowsPowerShellPath')){{
  $found=@($ast.FindAll({{param($node)
      ($node -is [Management.Automation.Language.FunctionDefinitionAst] -and
       $node.Name -ceq $fn)}},$true))
  if($found.Count -ne 1){{throw 'UCIE_W32_PRODUCTION_UAC_FN_NOT_UNIQUE'}}
  . ([scriptblock]::Create($found[0].Extent.Text))
}}
$script:spawnCount=0
$script:denied=$false
$script:spawnedArguments=''
$script:spawnedExe=''
$schema='UCIE_W31_OLD_LOCAL_LISTENER_PID_IDENTITY_READONLY_V01'
function Start-Process {{
    [CmdletBinding()]
    param(
      [string]$FilePath,[string]$ArgumentList,[string]$Verb,
      [switch]$PassThru
    )
    $script:spawnCount++
    $script:spawnedArguments=$ArgumentList
    $script:spawnedExe=$FilePath
    if($Verb -cne 'RunAs' -or -not $PassThru){{
      throw 'UCIE_W32_NOT_EXPLICIT_UAC'
    }}
    if($FilePath -cne 'C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe'){{
      throw 'UCIE_W32_NOT_PINNED_SYSTEM_POWERSHELL'
    }}
    if($script:denied){{throw 'UCIE_W32_SYNTHETIC_UAC_CANCEL'}}
    return [pscustomobject]@{{Id=42420}}
}}
"""


class W32OwnerReadOnlyUacNativeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = SOURCE.read_text("utf-8")

    def native(self, tail: str) -> str:
        if not shell():
            self.skipTest("Native PowerShell unavailable")
        proc = run_mock(setup() + tail)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        return proc.stdout

    def test_no_host_contract_and_missing_approval_preserved(self):
        if not shell():
            self.skipTest("Native PowerShell unavailable")
        command = [shell(), "-NoProfile", "-NonInteractive"]
        if os.name == "nt":
            command.extend(["-ExecutionPolicy", "Bypass"])
        command.extend(["-File", str(SOURCE)])
        default = subprocess.run(command, capture_output=True, text=True, timeout=25)
        self.assertEqual(default.returncode, 0, default.stdout + default.stderr)
        self.assertIn("UCIE_W31_CONTRACT_ONLY_NO_HOST_ACCESS", default.stdout)
        self.assertIn('"task_scheduler_queried_or_modified":false', default.stdout)
        denied = subprocess.run(command + ["-CheckLocal"],
                                capture_output=True, text=True, timeout=25)
        self.assertNotEqual(denied.returncode, 0)
        self.assertIn("UCIE_W31_EXPLICIT_OWNER_READONLY_APPROVAL_REQUIRED",
                      denied.stdout + denied.stderr)

    def test_pure_encoded_command_proves_same_sid_and_only_readonly_action(self):
        out = self.native(r"""
$callerSid='S-1-5-21-111-222-333-444'
$arg=NewReadOnlyUacArguments $callerSid
$parts=$arg.Split(' ')
if($parts.Count -ne 4 -or $parts[0] -cne '-NoProfile' -or
   $parts[1] -cne '-NoExit' -or $parts[2] -cne '-EncodedCommand'){
    throw 'UCIE_W32_LAUNCH_ARGS_NOT_FIXED'
}
$decoded=[Text.Encoding]::Unicode.GetString([Convert]::FromBase64String($parts[3]))
if(-not $decoded.Contains($callerSid) -or
   -not $decoded.Contains("UCIE_W32_UAC_ACCOUNT_CHANGED__READONLY_HOLD") -or
   -not $decoded.Contains("D:\UCIE_PROJECT\UCIE\scripts\ucie_owner_w31_local_listener_pid_readonly_v01.ps1") -or
   -not $decoded.Contains("-CheckLocal -OwnerApproval 'AUTHORIZE_UCIE_W31_READONLY_OLD_LOCAL_LISTENER_PID_INSPECTION'")){
    throw 'UCIE_W32_CHILD_OWNER_SID_OR_FIXED_READONLY_COMMAND_MISSING'
}
foreach($forbidden in @(
  '-RehearseOld','-RecoverOld','-RecoverPartial','-ResumePartial',
  '-ApplyLocal','-RollbackLocal','Stop-ScheduledTask','git reset',
  'UCIE_W31_EXACT_LOOPBACK_PID_BINARY_CLI_OWNER_VERIFIED__TASK_LAUNCH_LINK_HOLD'
)){
    if($decoded.Contains($forbidden)){
        throw 'UCIE_W32_MUTATION_OR_FALSE_PASS_EMBEDDED_IN_CHILD'
    }
}
Write-Output 'UCIE_W32_EXACT_OWNER_SID_ENCODED_READONLY_COMMAND_PASS'
""")
        self.assertIn("UCIE_W32_EXACT_OWNER_SID_ENCODED_READONLY_COMMAND_PASS", out)

    def test_pure_helper_rejects_non_sid_and_injection_values(self):
        out = self.native(r"""
foreach($invalid in @(
    '', 'ABC', "S-1-5-21'; Stop-ScheduledTask -TaskName other",
    'S-1-5-21-111-222 | Out-File C:\TEMP\victim', 'S-1-'
)){
    try{
        [void](NewReadOnlyUacArguments $invalid)
        throw 'UCIE_W32_ACCEPTED_MALICIOUS_SID'
    }catch{
        if($_.Exception.Message -cne 'UCIE_W32_INVALID_OR_UNTRUSTED_OWNER_SID'){throw}
    }
}
Write-Output 'UCIE_W32_INVALID_SID_INPUT_DENIED_PASS'
""")
        self.assertIn("UCIE_W32_INVALID_SID_INPUT_DENIED_PASS", out)

    def test_actual_uac_handoff_mocked_and_truthfully_pending(self):
        out = self.native(r"""
$callerSid='S-1-5-21-111-222-333-444'
$powershell='C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe'
$receipt=InvokeReadOnlyUacHandoff $powershell $callerSid
if($script:spawnCount -ne 1){
    throw 'UCIE_W32_SPAWN_COUNT_NOT_ONE'
}
if($receipt.status -cne 'UCIE_W32_ELEVATED_READONLY_WINDOW_STARTED__RESULT_PENDING' -or
   $receipt.full_cutover_authorized -ne $false -or
   $receipt.task_scheduler_or_c40_modified -ne $false -or
   $receipt.host_service_examined_in_parent -ne $false -or
   $receipt.journal_written -ne $false){
    throw 'UCIE_W32_UAC_LAUNCH_WRONGLY_CLAIMED_OWNER_PASS'
}
if(-not $script:spawnedArguments.Contains('-EncodedCommand')){
    throw 'UCIE_W32_NON_ENCODED_ARGUMENTS'
}
Write-Output 'UCIE_W32_MOCK_UAC_RUNAS_PENDING_NOT_PASS'
""")
        self.assertIn("UCIE_W32_MOCK_UAC_RUNAS_PENDING_NOT_PASS", out)

    def test_uac_cancel_returns_stable_hold_without_fallback(self):
        out = self.native(r"""
$script:denied=$true
try{
    [void](InvokeReadOnlyUacHandoff 'C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe' 'S-1-5-21-111-222-333-444')
    throw 'UCIE_W32_UAC_DENIAL_WRONGLY_ACCEPTED'
}catch{
    if($_.Exception.Message -cne 'UCIE_W32_OWNER_UAC_CANCELLED_OR_LAUNCH_FAILED__NO_HOST_CHECK'){throw}
}
if($script:spawnCount -ne 1){throw 'UCIE_W32_FALLBACK_UAC_RETRY_DETECTED'}
Write-Output 'UCIE_W32_UAC_CANCEL_NO_FALLBACK_PASS'
""")
        self.assertIn("UCIE_W32_UAC_CANCEL_NO_FALLBACK_PASS", out)

    def test_windows_os_system_directory_ignores_forged_process_systemroot(self):
        if os.name != "nt":
            self.skipTest("requires native Windows")
        out = self.native(r"""
$expected=Join-Path -Path ([Environment]::SystemDirectory) -ChildPath 'WindowsPowerShell\v1.0\powershell.exe'
$original=$env:SystemRoot
try {
    $env:SystemRoot='Q:\UCIE_W33_UNTRUSTED_WINDOWS_ROOT'
    $actual=GetTrustedWindowsPowerShellPath
    if(-not [string]::Equals($expected,$actual,[StringComparison]::OrdinalIgnoreCase)){
        throw 'UCIE_W33_ENVIRONMENT_REDIRECTED_TRUSTED_PATH'
    }
    if(-not [IO.File]::Exists($actual)){throw 'UCIE_W33_TRUSTED_BINARY_MISSING'}
    if($script:spawnCount -ne 0){throw 'UCIE_W33_UNEXPECTED_UAC_LAUNCH'}
} finally {
    $env:SystemRoot=$original
}
Write-Output 'UCIE_W33_NATIVE_OS_DIRECTORY_PASS'
""")
        self.assertIn("UCIE_W33_NATIVE_OS_DIRECTORY_PASS", out)

    def test_first_party_source_does_not_bypass_safety_gate(self):
        s = self.source
        self.assertIn("NewReadOnlyUacArguments", s)
        self.assertIn("InvokeReadOnlyUacHandoff", s)
        self.assertIn("Start-Process -FilePath $powershellPath -ArgumentList $arguments", s)
        self.assertIn("-Verb RunAs -ErrorAction Stop -PassThru", s)
        self.assertIn("[Environment]::SystemDirectory", s)
        self.assertIn("Join-Path -Path $systemDirectory -ChildPath 'WindowsPowerShell", s)
        self.assertIn("GetTrustedWindowsPowerShellPath", s)
        self.assertNotIn("GetEnvironmentVariable('SystemRoot','Machine')", s)
        self.assertIn("UAC_ACCOUNT_CHANGED__READONLY_HOLD", s)
        self.assertIn("ELEVATED_READONLY_WINDOW_STARTED__RESULT_PENDING", s)
        self.assertIn("UCIE_W31_EXPLICIT_OWNER_READONLY_APPROVAL_REQUIRED", s)
        self.assertIn("UCIE_W31_CONTRACT_ONLY_NO_HOST_ACCESS", s)
        self.assertNotIn("-ExecutionPolicy Bypass", s)
        for bad in ("Stop-ScheduledTask", "Start-ScheduledTask",
                    "Enable-ScheduledTask", "Disable-ScheduledTask",
                    "Set-ScheduledTask", "Register-ScheduledTask",
                    "Stop-Process", "taskkill", "sqlite3.connect",
                    "SavePrivate $", "SaveW30 $", "-ApplyLocal", "-RollbackLocal"):
            with self.subTest(bad=bad):
                self.assertNotIn(bad, s)


if __name__ == "__main__":
    unittest.main()
