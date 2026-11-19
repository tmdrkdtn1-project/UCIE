"""W31 native PowerShell exact PID/CLI/SID local listener gate; NO owner host.

Parse actual first-party W31 pure functions, run only on in-memory mock TCP,
CIM and process-owner results. No actual TCP inspection, Scheduler/SQLite/C40,
private archive or process stop on either CI runner platform.
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


def ps() -> str | None:
    return "powershell.exe" if os.name == "nt" else shutil.which("pwsh")


def execute(script: str) -> subprocess.CompletedProcess[str]:
    shell = ps()
    assert shell
    with tempfile.TemporaryDirectory(prefix="ucie_w31_pid_mock_") as td:
        file = Path(td) / "pid_identity.ps1"
        file.write_text(script, encoding="utf-8")
        command = [shell, "-NoProfile", "-NonInteractive"]
        if os.name == "nt":
            command += ["-ExecutionPolicy", "Bypass"]
        return subprocess.run(
            command + ["-File", str(file)],
            capture_output=True, text=True, timeout=30, check=False,
        )


def mock_core() -> str:
    source = str(SOURCE).replace("'", "''")
    return rf"""
Set-StrictMode -Version Latest
$ErrorActionPreference='Stop'
$tokens=$null;$errors=$null
$ast=[Management.Automation.Language.Parser]::ParseFile('{source}',[ref]$tokens,[ref]$errors)
if(@($errors).Count -ne 0){{throw 'UCIE_W31_SOURCE_PARSE_FAILED'}}
foreach($name in @('AssertExactOriginalCommandLine','AssertOwnerLocalListenerPidIdentity')){{
  $fns=@($ast.FindAll({{param($node)
      ($node -is [Management.Automation.Language.FunctionDefinitionAst] -and
       $node.Name -ceq $name)}},$true))
  if($fns.Count -ne 1){{throw 'UCIE_W31_SOURCE_FUNCTION_NOT_UNIQUE'}}
  . ([scriptblock]::Create($fns[0].Extent.Text))
}}
$specs=@(
 [pscustomobject]@{{Exe='D:\UCIE\.venv\Scripts\python.exe';Arguments='collector'}},
 [pscustomobject]@{{Exe='D:\UCIE\.venv\Scripts\python.exe';Arguments='internal'}},
 [pscustomobject]@{{Exe='D:\UCIE\.venv\Scripts\pythonw.exe';Arguments='-B "D:\UCIE\scripts\run_ucie_local_v1_autostart.py" --port 18767'}}
)
$script:ownerSid='S-1-5-21-SYNTHETIC-UCIE'
$script:tcp=@([pscustomobject]@{{LocalAddress='127.0.0.1';LocalPort=18767;OwningProcess=42420}})
$script:cim=@([pscustomobject]@{{
  ProcessId=42420
  ExecutablePath='D:\UCIE\.venv\Scripts\pythonw.exe'
  CommandLine='"D:\UCIE\.venv\Scripts\pythonw.exe" -B "D:\UCIE\scripts\run_ucie_local_v1_autostart.py" --port 18767'
}})
$script:cimOwner=$script:ownerSid
$script:cimReturn=0
$script:log=[System.Collections.Generic.List[string]]::new()
function Get-NetTCPConnection{{
    [CmdletBinding()]
    param([int]$LocalPort,[string]$State)
    if($LocalPort -ne 18767 -or $State -cne 'Listen'){{
        throw 'UCIE_W31_BROADER_LISTENER_SCAN_DENIED'
    }}
    $script:log.Add('GET_EXACT_PORT_18767')
    return $script:tcp
}}
function Get-CimInstance{{
    [CmdletBinding()]
    param([string]$ClassName,[string]$Filter)
    if($ClassName -cne 'Win32_Process' -or $Filter -cne 'ProcessId = 42420'){{
        throw 'UCIE_W31_BROAD_HOST_PROCESS_SCAN_DENIED'
    }}
    $script:log.Add('GET_ONLY_LISTENER_PID')
    return $script:cim
}}
function Invoke-CimMethod{{
    [CmdletBinding()]
    param($InputObject,[string]$MethodName)
    if($MethodName -cne 'GetOwnerSid' -or
       [int]$InputObject.ProcessId -ne 42420){{
        throw 'UCIE_W31_NONREADONLY_CIM_METHOD_DENIED'
    }}
    $script:log.Add('GET_PROCESS_SID_ONLY')
    return [pscustomobject]@{{Sid=$script:cimOwner;ReturnValue=$script:cimReturn}}
}}
"""


class W31ListenerPidIdentityNativeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = SOURCE.read_text(encoding="utf-8")

    def native(self, tail: str) -> str:
        if not ps():
            self.skipTest("Native PowerShell unavailable")
        result = execute(mock_core() + tail)
        self.assertEqual(result.returncode, 0,
                         result.stdout + result.stderr)
        return result.stdout

    def test_no_host_contract_and_missing_owner_approval_denied(self):
        if not ps():
            self.skipTest("Native PowerShell unavailable")
        command = [ps(), "-NoProfile", "-NonInteractive"]
        if os.name == "nt":
            command += ["-ExecutionPolicy", "Bypass"]
        command += ["-File", str(SOURCE)]
        contract = subprocess.run(command, capture_output=True, text=True, timeout=25)
        self.assertEqual(contract.returncode, 0, contract.stdout + contract.stderr)
        self.assertIn("UCIE_W31_CONTRACT_ONLY_NO_HOST_ACCESS", contract.stdout)
        self.assertIn('"host_process_queried":false', contract.stdout)
        denied = subprocess.run(command + ["-CheckLocal"],
                                capture_output=True, text=True, timeout=25)
        self.assertNotEqual(denied.returncode, 0)
        self.assertIn("UCIE_W31_EXPLICIT_OWNER_READONLY_APPROVAL_REQUIRED",
                      denied.stdout + denied.stderr)
        orphan = subprocess.run(command + ["-OwnerApproval", "ORPHAN"],
                                capture_output=True, text=True, timeout=25)
        self.assertNotEqual(orphan.returncode, 0)
        self.assertIn("UCIE_W31_APPROVAL_WITHOUT_CHECK_DENIED",
                      orphan.stdout + orphan.stderr)

    def test_actual_functions_accept_exact_quoted_and_unquoted_exe(self):
        out = self.native(r"""
$expected=$specs[2]
$argv='"D:\UCIE\.venv\Scripts\pythonw.exe" '+$expected.Arguments
if(-not (AssertExactOriginalCommandLine $argv $expected.Exe $expected.Arguments)){
    throw 'UCIE_W31_VALID_QUOTED_REJECTED'
}
$argv=$expected.Exe+' '+$expected.Arguments
if(-not (AssertExactOriginalCommandLine $argv $expected.Exe $expected.Arguments)){
    throw 'UCIE_W31_VALID_UNQUOTED_REJECTED'
}
if(-not (AssertOwnerLocalListenerPidIdentity)){throw 'UCIE_W31_EXACT_LISTENER_REJECTED'}
if(($script:log -join ',') -cne 'GET_EXACT_PORT_18767,GET_ONLY_LISTENER_PID,GET_PROCESS_SID_ONLY'){
    throw 'UCIE_W31_UNEXPECTED_HOST_DATA_QUERY'
}
Write-Output 'UCIE_W31_REAL_EXACT_PID_CLI_SID_MOCK_PASS'
""")
        self.assertIn("UCIE_W31_REAL_EXACT_PID_CLI_SID_MOCK_PASS", out)

    def test_wrong_argv_or_executable_binary_refused(self):
        out = self.native(r"""
function MustDeny([string]$cmd,[string]$reason){
 try{[void](AssertExactOriginalCommandLine $cmd $specs[2].Exe $specs[2].Arguments)
     throw 'UCIE_W31_BAD_ARGV_ACCEPTED'}
 catch{if($_.Exception.Message -cne $reason){throw}}
}
MustDeny '"D:\UCIE\.venv\Scripts\pythonw.exe" -B "D:\UCIE\scripts\run_ucie_local_v1_autostart.py" --port 18768' 'UCIE_W31_LISTENER_ARGS_COMMANDLINE_MISMATCH_HOLD'
MustDeny '"D:\UCIE\.venv\Scripts\pythonw.exe" -B "D:\UCIE\scripts\run_ucie_local_v1_autostart.py" --port 18767 --other' 'UCIE_W31_LISTENER_ARGS_COMMANDLINE_MISMATCH_HOLD'
MustDeny '"D:\UCIE\.venv\Scripts\pythonw.exe.bak" '+$specs[2].Arguments 'UCIE_W31_LISTENER_EXE_COMMANDLINE_MISMATCH_HOLD'
MustDeny '"D:\OTHER\pythonw.exe" '+$specs[2].Arguments 'UCIE_W31_LISTENER_EXE_COMMANDLINE_MISMATCH_HOLD'
MustDeny ' "D:\UCIE\.venv\Scripts\pythonw.exe"'+$specs[2].Arguments 'UCIE_W31_LISTENER_ARGS_COMMANDLINE_MISMATCH_HOLD'
Write-Output 'UCIE_W31_PRODUCTION_CLI_REJECTION_MATRIX_PASS'
""")
        self.assertIn("UCIE_W31_PRODUCTION_CLI_REJECTION_MATRIX_PASS", out)

    def test_foreign_listener_multiple_missing_pid_wrong_owner_and_exe_hold(self):
        out = self.native(r"""
function MustHold([string]$expect){
 try{[void](AssertOwnerLocalListenerPidIdentity);throw 'UCIE_W31_UNEXPECTED_LISTENER_ACCEPT'}
 catch{if($_.Exception.Message -cne $expect){throw}}
}
$baseline=$script:tcp
$script:tcp=@();MustHold 'UCIE_W31_ONE_LISTENER_REQUIRED_HOLD'
$script:tcp=@($baseline[0],$baseline[0]);MustHold 'UCIE_W31_ONE_LISTENER_REQUIRED_HOLD'
$script:tcp=@([pscustomobject]@{LocalAddress='0.0.0.0';LocalPort=18767;OwningProcess=42420})
MustHold 'UCIE_W31_EXACT_LOOPBACK_BINDING_REQUIRED_HOLD'
$script:tcp=@([pscustomobject]@{LocalAddress='127.0.0.1';LocalPort=18767;OwningProcess=0})
MustHold 'UCIE_W31_LISTENER_PROCESS_ID_MISSING_HOLD'
$script:tcp=$baseline
$script:cim=@();MustHold 'UCIE_W31_LISTENER_PID_PROCESS_LOOKUP_HOLD'
$script:cim=@([pscustomobject]@{ProcessId=42420;ExecutablePath='D:\OTHER\pythonw.exe';CommandLine='NOPE'})
MustHold 'UCIE_W31_LISTENER_EXE_PATH_MISMATCH_HOLD'
$script:cim=@([pscustomobject]@{ProcessId=42420;ExecutablePath=$specs[2].Exe;CommandLine='"D:\UCIE\.venv\Scripts\pythonw.exe" '+$specs[2].Arguments})
$script:cimOwner='S-1-5-21-FOREIGN';MustHold 'UCIE_W31_LISTENER_PROCESS_OWNER_SID_HOLD'
$script:cimOwner=$script:ownerSid;$script:cimReturn=5;MustHold 'UCIE_W31_LISTENER_PROCESS_OWNER_SID_HOLD'
Write-Output 'UCIE_W31_FOREIGN_PORT_PID_OWNER_BINARY_FAIL_CLOSED_PASS'
""")
        self.assertIn("UCIE_W31_FOREIGN_PORT_PID_OWNER_BINARY_FAIL_CLOSED_PASS", out)

    def test_source_readonly_constraints_and_no_false_task_pid_claim(self):
        source = self.source
        self.assertIn("Get-NetTCPConnection -LocalPort 18767 -State Listen", source)
        self.assertIn("Get-CimInstance -ClassName Win32_Process -Filter", source)
        self.assertIn("-MethodName GetOwnerSid", source)
        self.assertIn("listener_pid_launched_by_task_scheduler_verified=$false", source)
        self.assertIn("listener_task_pid_identity_verified=$false", source)
        self.assertIn("c40_mcp_round_trip_verified=$false", source)
        self.assertIn("UCIE_W31_EXACT_LOOPBACK_PID_BINARY_CLI_OWNER_VERIFIED__TASK_LAUNCH_LINK_HOLD", source)
        self.assertIn("OWNER_NEWROOT_DIRTY_HOLD", source)
        self.assertIn("UCIE_W31_PROTECTED_ARCHIVE_SAME_OWNER_REQUIRED", source)
        self.assertIn("848cb03f50dc455fc61935a484c3d71e82506c90", source)
        self.assertIn("5a0251f8c8b22efbb7cb3876ef66409486b053dd", source)
        self.assertNotIn("Get-CimInstance -ClassName Win32_Process |", source)
        self.assertNotIn("Stop-Process", source)
        self.assertNotIn("taskkill", source)
        self.assertNotIn("Disable-ScheduledTask", source)
        self.assertNotIn("Enable-ScheduledTask", source)
        self.assertNotIn("Start-ScheduledTask", source)
        self.assertNotIn("Stop-ScheduledTask", source)
        self.assertNotIn("Register-ScheduledTask", source)
        self.assertNotIn("Set-ScheduledTask", source)
        self.assertNotIn("sqlite3.connect", source)
        self.assertNotIn("SavePrivate $", source)
        self.assertNotIn("SaveW30 $", source)
        self.assertNotIn("$pid=", source.lower())
        self.assertNotIn("$matches=", source.lower())


if __name__ == "__main__":
    unittest.main()
