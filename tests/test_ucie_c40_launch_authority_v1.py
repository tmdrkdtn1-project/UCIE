"""UCIE C40 missing-client launch gate: isolated synthetic PowerShell evidence.

Real process listing, task registration, client starting and DB writes are forbidden.
Only the already-reviewed UCIE PowerShell function definitions are evaluated
against synthetic no-client, access-denied and census-race observations.
"""
from pathlib import Path
import shutil
import subprocess
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "ucie_c40_recover.ps1"


class UCIEC40LaunchGateV1(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = SCRIPT.read_text(encoding="utf-8")

    def test_launch_authority_defined_and_default_status_inert(self):
        self.assertIn("function Assert-C40LaunchAuthority", self.source)
        self.assertIn("UCIE_C40_LAUNCH_REQUIRES_RUNNING_HIGHEST_TASK", self.source)
        self.assertIn("UCIE_C40_ELEVATED_OWNER_REQUIRED_FOR_LAUNCH", self.source)
        self.assertIn("UCIE_C40_CLIENT_APPEARED_ABORT_LAUNCH", self.source)
        self.assertIn("[string]$Mode = 'Status'", self.source)
        self.assertIn("-LogonType Interactive -RunLevel Highest", self.source)

    def _run_scenario(self, script):
        shell = shutil.which("pwsh") or shutil.which("powershell.exe")
        if shell is None:
            self.skipTest("PowerShell unavailable")
        path = str(SCRIPT).replace("'", "''")
        setup = r'''
$ErrorActionPreference = 'Stop'
$t = $null; $errors = $null
$ast = [System.Management.Automation.Language.Parser]::ParseFile(
    'SCRIPT_PATH', [ref]$t, [ref]$errors)
if ($errors.Count -ne 0) { throw 'UCIE_C40_SOURCE_PARSER_FAILED' }
foreach ($name in @('One-C40Check', 'Assert-C40LaunchAuthority')) {
    $matches = @($ast.FindAll({
        param($a)
        $a -is [System.Management.Automation.Language.FunctionDefinitionAst] -and
        $a.Name -eq $name
    }, $true))
    if ($matches.Count -ne 1) { throw 'UCIE_C40_SOURCE_FUNCTION_MISSING' }
    Invoke-Expression $matches[0].Extent.Text
}
function Start-Process { throw 'UCIE_C40_TEST_REAL_PROCESS_START_FORBIDDEN' }
function Get-CimInstance { throw 'UCIE_C40_TEST_REAL_CIM_FORBIDDEN' }
function Start-Sleep { throw 'UCIE_C40_TEST_REAL_SLEEP_FORBIDDEN' }
function Verify-C40Inputs { throw 'UCIE_C40_TEST_REAL_INPUT_ACCESS_FORBIDDEN' }
'''
        ps = setup.replace("SCRIPT_PATH", path) + "\n" + script
        result = subprocess.run(
            [shell, "-NoProfile", "-NonInteractive", "-Command", ps],
            capture_output=True, text=True, timeout=25, check=False
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_missing_c40_is_readonly_if_start_not_requested(self):
        self._run_scenario(r'''
function Find-C40 { return @() }
function Assert-C40LaunchAuthority { throw 'UCIE_C40_TEST_AUTHORITY_NOT_ALLOWED' }
$r=One-C40Check -StartMissing:$false
if ($r.status -ne 'UCIE_C40_NOT_RUNNING' -or $r.started) {
    throw 'UCIE_C40_READONLY_ABSENCE_BEHAVIOR_FAILED'
}
''')

    def test_missing_client_with_no_authority_never_starts(self):
        self._run_scenario(r'''
function Find-C40 { return @() }
function Assert-C40LaunchAuthority { throw 'UCIE_C40_TEST_AUTHORITY_DENIED' }
try {
    One-C40Check -StartMissing | Out-Null
    throw 'UCIE_C40_TEST_LAUNCH_WAS_NOT_BLOCKED'
}
catch {
    if ([string]$_.Exception.Message -ne 'UCIE_C40_TEST_AUTHORITY_DENIED') {
        throw
    }
}
''')

    def test_client_appearing_during_census_aborts_before_start(self):
        self._run_scenario(r'''
$script:queries=0
function Find-C40 {
    $script:queries++
    if ($script:queries -eq 1) { return @() }
    return [pscustomobject]@{ ProcessId=111 }
}
function Assert-C40LaunchAuthority { }
function Verify-C40Inputs { return 'SYNTHETIC_UCIE_PROFILE' }
try {
    One-C40Check -StartMissing | Out-Null
    throw 'UCIE_C40_TEST_RACE_DID_NOT_ABORT'
}
catch {
    if ([string]$_.Exception.Message -ne 'UCIE_C40_CLIENT_APPEARED_ABORT_LAUNCH') {
        throw
    }
}
if ($script:queries -ne 2) { throw 'UCIE_C40_TEST_DOUBLE_CENSUS_MISSING' }
''')

    def test_healthy_existing_client_remains_untouched(self):
        self._run_scenario(r'''
function Find-C40 { return [pscustomobject]@{ ProcessId=111 } }
function Assert-C40LaunchAuthority { throw 'UCIE_C40_TEST_SHOULD_NOT_RECHECK_AUTH' }
$r=One-C40Check -StartMissing
if ($r.status -ne 'UCIE_C40_ALREADY_RUNNING' -or
    $r.started -or $r.tunnel_clients -ne 1) {
    throw 'UCIE_C40_TEST_EXISTING_CLIENT_CHANGED'
}
''')

    def test_disabled_task_cannot_gain_launch_authority(self):
        self._run_scenario(r'''
function Assert-ApprovedRecoveryTask {
    return [pscustomobject]@{
        State='Disabled'
        Principal=[pscustomobject]@{ RunLevel='Highest';LogonType='Interactive' }
    }
}
try {
    Assert-C40LaunchAuthority
    throw 'UCIE_C40_TEST_DISABLED_TASK_LAUNCH_ALLOWED'
}
catch {
    if ([string]$_.Exception.Message -ne 'UCIE_C40_LAUNCH_REQUIRES_RUNNING_HIGHEST_TASK') {
        throw
    }
}
''')


if __name__ == "__main__":
    unittest.main()
