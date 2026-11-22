"""Pure synthetic C40 loss-recovery behavior. Never touches a real UCIE task/client.

PowerShell AST extracts only One-C40Check from the pinned repository script.
All process, task, sleep and input functions are substituted with synthetic
stubs. This is behavior evidence, NOT a real outage or logon acceptance.
"""
from pathlib import Path
import shutil
import subprocess
import unittest

SOURCE = Path(__file__).resolve().parents[1] / "scripts" / "ucie_c40_recover.ps1"


class C40LossRecoverySyntheticV1(unittest.TestCase):
    def scenario(self, body):
        shell = shutil.which("powershell.exe") or shutil.which("pwsh")
        if shell is None:
            self.skipTest("PowerShell is unavailable")
        path = str(SOURCE).replace("'", "''")
        setup = r'''
$ErrorActionPreference='Stop'
$tokens=$null; $parseErrors=$null
$ast=[System.Management.Automation.Language.Parser]::ParseFile(
    'SOURCE_PATH',[ref]$tokens,[ref]$parseErrors)
if($parseErrors.Count -ne 0){throw 'UCIE_C40_SYNTHETIC_PARSE_FAILED'}
$defs=@($ast.FindAll({
    param($node)
    $node -is [System.Management.Automation.Language.FunctionDefinitionAst] -and
    $node.Name -eq 'One-C40Check'
},$true))
if($defs.Count -ne 1){throw 'UCIE_C40_SYNTHETIC_FUNCTION_NOT_UNIQUE'}
Invoke-Expression $defs[0].Extent.Text
# Fail-fast stand-ins: no real process/task/input access can escape the trial.
function Get-CimInstance {throw 'UCIE_C40_SYNTHETIC_REAL_CIM_FORBIDDEN'}
function Get-ScheduledTask {throw 'UCIE_C40_SYNTHETIC_REAL_TASK_FORBIDDEN'}
function Start-ScheduledTask {throw 'UCIE_C40_SYNTHETIC_REAL_TASK_START_FORBIDDEN'}
function Register-ScheduledTask {throw 'UCIE_C40_SYNTHETIC_REAL_TASK_REG_FORBIDDEN'}
function Stop-Process {throw 'UCIE_C40_SYNTHETIC_REAL_PROCESS_STOP_FORBIDDEN'}
function Start-Process {throw 'UCIE_C40_SYNTHETIC_REAL_PROCESS_START_FORBIDDEN'}
function Start-Sleep {param([int]$Seconds) if($Seconds -ne 2){throw 'UCIE_C40_SYNTHETIC_SLEEP_UNEXPECTED'}}
$script:clientExe='UCIE_SYNTHETIC_EXECUTABLE'
$script:profile='UCIE_SYNTHETIC_PROFILE'
$script:health='UCIE_SYNTHETIC_HEALTH'
$script:ownerMarker='UCIE_PRIVATE_READONLY_APPROVED'
$script:librarySrc='UCIE_SYNTHETIC_LIB'
$script:adminSrc='UCIE_SYNTHETIC_ADMIN'
$script:libraryApp='UCIE_SYNTHETIC_APP'
$script:EnableAdminTools=$true
$script:censuses=0
$script:starts=0
$script:authorizations=0
$env:UCIE_MCP_OWNER_APPROVAL='BEFORE_APPROVAL'
$env:UCIE_MCP_TUNNEL_ID='BEFORE_ID'
$env:UCIE_ADMIN_TOOLS_ENABLED='BEFORE_ADMIN'
$env:PYTHONPATH='BEFORE_PATH'
function Assert-SyntheticEnvironmentRestored {
    if($env:UCIE_MCP_OWNER_APPROVAL -ne 'BEFORE_APPROVAL' -or
       $env:UCIE_MCP_TUNNEL_ID -ne 'BEFORE_ID' -or
       $env:UCIE_ADMIN_TOOLS_ENABLED -ne 'BEFORE_ADMIN' -or
       $env:PYTHONPATH -ne 'BEFORE_PATH') {
       throw 'UCIE_C40_SYNTHETIC_ENVIRONMENT_NOT_RESTORED'
    }
}
'''
        program = setup.replace("SOURCE_PATH", path) + "\n" + body + "\nexit 0\n"
        out = subprocess.run(
            [shell, "-NoProfile", "-NonInteractive", "-Command", program],
            capture_output=True, text=True, errors="replace",
            timeout=35, check=False,
        )
        self.assertEqual(out.returncode, 0, out.stdout + out.stderr)

    def test_missing_client_restarted_once_after_two_empty_censuses(self):
        self.scenario(r'''
function Assert-C40LaunchAuthority {$script:authorizations++}
function Verify-C40Inputs {return 'SYNTHETIC_ID'}
function Find-C40 {
    $script:censuses++
    if($script:censuses -le 2){return @()}
    return [pscustomobject]@{ProcessId=424242}
}
function Start-Process {
    [CmdletBinding()]
    param([string]$FilePath,[string[]]$ArgumentList,
          [string]$WorkingDirectory,[string]$WindowStyle,[switch]$PassThru)
    if($FilePath -ne 'UCIE_SYNTHETIC_EXECUTABLE' -or
       $WorkingDirectory -ne 'D:\UCIE' -or -not $PassThru -or
       $env:UCIE_MCP_OWNER_APPROVAL -ne 'UCIE_PRIVATE_READONLY_APPROVED' -or
       $env:UCIE_ADMIN_TOOLS_ENABLED -ne '1' -or
       $env:UCIE_MCP_TUNNEL_ID -ne 'SYNTHETIC_ID') {
        throw 'UCIE_C40_SYNTHETIC_BAD_LAUNCH_ARGUMENTS'
    }
    $script:starts++
    return [pscustomobject]@{Id=424242}
}
$result=One-C40Check -StartMissing
if($result.status -ne 'UCIE_C40_CHILD_STARTED' -or -not $result.started -or
   $result.tunnel_clients -ne 1 -or $script:starts -ne 1 -or
   $script:censuses -ne 3 -or $script:authorizations -ne 1){
    throw 'UCIE_C40_SYNTHETIC_RESTART_NOT_PROVEN'
}
Assert-SyntheticEnvironmentRestored
''')

    def test_without_owner_authority_no_synthetic_launch(self):
        self.scenario(r'''
function Find-C40 {$script:censuses++; return @()}
function Assert-C40LaunchAuthority {throw 'UCIE_C40_SYNTHETIC_DENIED'}
function Verify-C40Inputs {throw 'UCIE_C40_SYNTHETIC_INPUTS_MUST_NOT_RUN'}
$denied=$false
try {$null=One-C40Check -StartMissing}
catch {
    if([string]$_.Exception.Message -ne 'UCIE_C40_SYNTHETIC_DENIED'){throw}
    $denied=$true
}
if(-not $denied -or $script:censuses -ne 1 -or $script:starts -ne 0){
    throw 'UCIE_C40_SYNTHETIC_AUTH_BYPASS'
}
Assert-SyntheticEnvironmentRestored
''')

    def test_client_appearing_on_second_census_blocks_launch(self):
        self.scenario(r'''
function Find-C40 {
    $script:censuses++
    if($script:censuses -eq 1){return @()}
    return [pscustomobject]@{ProcessId=424242}
}
function Assert-C40LaunchAuthority {$script:authorizations++}
function Verify-C40Inputs {return 'SYNTHETIC_ID'}
$blocked=$false
try {$null=One-C40Check -StartMissing}
catch {
    if([string]$_.Exception.Message -ne 'UCIE_C40_CLIENT_APPEARED_ABORT_LAUNCH'){throw}
    $blocked=$true
}
if(-not $blocked -or $script:censuses -ne 2 -or
   $script:authorizations -ne 1 -or $script:starts -ne 0){
    throw 'UCIE_C40_SYNTHETIC_RACE_NOT_BLOCKED'
}
Assert-SyntheticEnvironmentRestored
''')

    def test_failed_synthetic_child_start_restores_environment(self):
        self.scenario(r'''
function Find-C40 {$script:censuses++; return @()}
function Assert-C40LaunchAuthority {$script:authorizations++}
function Verify-C40Inputs {return 'SYNTHETIC_ID'}
function Start-Process {
    [CmdletBinding()]
    param([string]$FilePath,[string[]]$ArgumentList,
          [string]$WorkingDirectory,[string]$WindowStyle,[switch]$PassThru)
    $script:starts++
    throw 'UCIE_C40_SYNTHETIC_CHILD_FAILURE'
}
$failed=$false
try {$null=One-C40Check -StartMissing}
catch {
    if([string]$_.Exception.Message -ne 'UCIE_C40_SYNTHETIC_CHILD_FAILURE'){throw}
    $failed=$true
}
if(-not $failed -or $script:censuses -ne 2 -or
   $script:authorizations -ne 1 -or $script:starts -ne 1){
    throw 'UCIE_C40_SYNTHETIC_FAILURE_PATH_BROKEN'
}
Assert-SyntheticEnvironmentRestored
''')

    def test_healthy_client_not_restarted(self):
        self.scenario(r'''
function Find-C40 {
    $script:censuses++
    return [pscustomobject]@{ProcessId=424242}
}
function Assert-C40LaunchAuthority {throw 'UCIE_C40_SYNTHETIC_AUTH_NOT_NEEDED'}
function Verify-C40Inputs {throw 'UCIE_C40_SYNTHETIC_INPUTS_NOT_NEEDED'}
$result=One-C40Check -StartMissing
if($result.status -ne 'UCIE_C40_ALREADY_RUNNING' -or $result.started -or
   $result.tunnel_clients -ne 1 -or $script:censuses -ne 1 -or
   $script:starts -ne 0){
    throw 'UCIE_C40_SYNTHETIC_EXISTING_CLIENT_CHANGED'
}
Assert-SyntheticEnvironmentRestored
''')


if __name__ == "__main__":
    unittest.main()
