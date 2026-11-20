"""W39: first-party source-only and synthetic native PowerShell tests.

No test invokes the actual UCIE task, tunnel executable, WMI host, URL,
private profile or operating SQLite. Native tests AST-extract only pure
first-party functions and supply disposable in-memory records.
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
SOURCE = ROOT / "scripts" / "ucie_owner_w39_c40_client_readonly_v01.ps1"


def ps_command() -> str | None:
    return "powershell.exe" if os.name == "nt" else shutil.which("pwsh")


def run_script(script: str) -> subprocess.CompletedProcess[str]:
    if ps_command() is None:
        raise RuntimeError("Native PowerShell not available")
    with tempfile.TemporaryDirectory(prefix="ucie_w39_synth_") as tmp:
        path = Path(tmp) / "w39_synthetic.ps1"
        path.write_text(script, encoding="utf-8")
        args = [ps_command(), "-NoProfile", "-NonInteractive"]
        if os.name == "nt":
            args += ["-ExecutionPolicy", "Bypass"]
        return subprocess.run(args + ["-File", str(path)], capture_output=True,
                              text=True, timeout=30)


def first_party_functions() -> str:
    path = str(SOURCE).replace("'", "''")
    return rf"""
Set-StrictMode -Version Latest
$ErrorActionPreference='Stop'
$tokens=$null;$err=$null
$ast=[Management.Automation.Language.Parser]::ParseFile('{path}',[ref]$tokens,[ref]$err)
if(@($err).Count -ne 0){{throw 'UCIE_W39_SOURCE_PARSE_HOLD'}}
foreach($name in @('NewW39ExactClientWql','AssertW39OneExactClient','WriteW39Receipt')){{
    $functions=@($ast.FindAll({{param($node)
        ($node -is [Management.Automation.Language.FunctionDefinitionAst] -and
         $node.Name -ceq $name)}},$true))
    if($functions.Count -ne 1){{throw 'UCIE_W39_UNIQUE_PURE_FUNCTION_HOLD'}}
    . ([scriptblock]::Create($functions[0].Extent.Text))
}}
$schema='UCIE_W39_C40_CLIENT_IMAGE_OWNER_READONLY_V01'
$expectedExe='D:\UCIE_DATA\tools\tunnel-client-v0.0.16\tunnel-client.exe'
"""


class TestW39BoundedC40ClientMetadata(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = SOURCE.read_text(encoding="utf-8")

    def native(self, tail: str) -> str:
        if ps_command() is None:
            self.skipTest("PowerShell native unavailable")
        result = run_script(first_party_functions() + tail)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        return result.stdout

    def test_contract_only_has_no_host_access(self):
        if ps_command() is None:
            self.skipTest("PowerShell native unavailable")
        args = [ps_command(), "-NoProfile", "-NonInteractive"]
        if os.name == "nt":
            args += ["-ExecutionPolicy", "Bypass"]
        result = subprocess.run(args + ["-File", str(SOURCE)],
                                capture_output=True, text=True, timeout=25)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        data = json.loads(result.stdout)
        self.assertEqual(data["status"], "UCIE_W39_CONTRACT_ONLY_NO_HOST_ACCESS")
        self.assertFalse(data["c40_client_metadata_queried"])
        self.assertFalse(data["c40_mcp_round_trip_verified"])
        self.assertFalse(data["connector_route_binding_verified"])
        self.assertFalse(data["full_cutover_authorized"])
        self.assertFalse(data["c40_profile_contents_read"])

    def test_owner_approval_is_required_before_any_host_queries(self):
        if ps_command() is None:
            self.skipTest("PowerShell native unavailable")
        args = [ps_command(), "-NoProfile", "-NonInteractive"]
        if os.name == "nt":
            args += ["-ExecutionPolicy", "Bypass"]
        proc = subprocess.run(args + ["-File", str(SOURCE), "-InspectLocal"],
                              capture_output=True, text=True, timeout=25)
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("UCIE_W39_EXPLICIT_OWNER_APPROVAL_REQUIRED_HOLD",
                      proc.stdout + proc.stderr)

    def test_wql_query_scoped_to_exact_first_party_client(self):
        out = self.native(r"""
$query=NewW39ExactClientWql $expectedExe
if(-not $query.Contains("WHERE ExecutablePath = 'D:\\UCIE_DATA\\tools\\tunnel-client-v0.0.16\\tunnel-client.exe'") -or
   $query.Contains('CommandLine') -or
   $query.Contains('SELECT *')){
    throw 'UCIE_W39_QUERY_WOULD_EXPOSE_OTHER_PROCESSES'
}
$pidScoped=NewW39ExactClientWql $expectedExe 1234
if(-not $pidScoped.EndsWith(' AND ProcessId = 1234')){
    throw 'UCIE_W39_SCOPED_PID_QUERY_INVALID'
}
try {
    [void](NewW39ExactClientWql 'D:\OTHER\tunnel-client.exe')
    throw 'UCIE_W39_FOREIGN_CLIENT_PATH_ACCEPTED'
} catch {
    if($_.Exception.Message -cne 'UCIE_W39_UNKNOWN_CLIENT_PATH_OR_PID_HOLD'){throw}
}
Write-Output 'UCIE_W39_WQL_EXACT_PATH_ONLY_PASS'
""")
        self.assertIn("UCIE_W39_WQL_EXACT_PATH_ONLY_PASS", out)

    @unittest.skipUnless(os.name == "nt", "Windows path semantics only")
    def test_exact_one_client_and_all_negative_cases(self):
        out = self.native(r"""
$one=[pscustomobject]@{
    ProcessId=1234;ExecutablePath=$expectedExe
    CreationDate=(Get-Date).AddMinutes(-3);ParentProcessId=99
}
$p=AssertW39OneExactClient @($one) $expectedExe
if([int]$p.ProcessId -ne 1234){throw 'UCIE_W39_VALID_FAKE_REJECTED'}
$bad=@(
    [pscustomobject]@{ProcessId=1234;ExecutablePath='D:\OTHER\tunnel-client.exe';CreationDate=(Get-Date).AddMinutes(-3)},
    [pscustomobject]@{ProcessId=0;ExecutablePath=$expectedExe;CreationDate=(Get-Date).AddMinutes(-3)},
    [pscustomobject]@{ProcessId=1234;ExecutablePath=$expectedExe;CreationDate=(Get-Date).AddMinutes(9)}
)
foreach($case in $bad){
    try {
        [void](AssertW39OneExactClient @($case) $expectedExe)
        throw 'UCIE_W39_INVALID_IMAGE_PID_OR_TIME_ACCEPTED'
    } catch {
        if($_.Exception.Message -notmatch '^UCIE_W39_(CLIENT_EXE_IDENTITY_MISMATCH|CLIENT_CREATION_DATE)_HOLD$'){throw}
    }
}
foreach($case in @(
    [pscustomobject]@{ Rows=@() },
    [pscustomobject]@{ Rows=@($one,$one) }
)){
    try {
        [void](AssertW39OneExactClient $case.Rows $expectedExe)
        throw 'UCIE_W39_ZERO_OR_DUPLICATE_CLIENT_ACCEPTED'
    } catch {
        if($_.Exception.Message -cne 'UCIE_W39_EXACT_CLIENT_COUNT_NOT_ONE_HOLD'){throw}
    }
}
Write-Output 'UCIE_W39_EXACT_ONE_CLIENT_NEGATIVE_CASES_PASS'
""")
        self.assertIn("UCIE_W39_EXACT_ONE_CLIENT_NEGATIVE_CASES_PASS", out)

    def test_success_receipt_still_forbids_route_and_cutover(self):
        out = self.native(r"""
$receipt=WriteW39Receipt 'UCIE_W39_ONE_EXACT_C40_CLIENT_IMAGE_OWNER_STABLE__MCP_ROUTE_HOLD' $true
$j=$receipt | ConvertFrom-Json
if(-not $j.c40_client_metadata_queried -or
   -not $j.c40_client_image_owner_and_stability_observed -or
   $j.c40_mcp_round_trip_verified -or $j.connector_route_binding_verified -or
   $j.c40_task_launch_origin_verified -or $j.full_cutover_authorized -or
   $j.c40_profile_contents_read -or $j.task_or_tunnel_modified){
    throw 'UCIE_W39_FALSE_C40_ROUTE_PASS'
}
Write-Output 'UCIE_W39_READONLY_STABLE_BUT_ROUTE_HOLD_PASS'
""")
        self.assertIn("UCIE_W39_READONLY_STABLE_BUT_ROUTE_HOLD_PASS", out)

    def test_static_source_never_reads_secret_profile_or_other_projects(self):
        src = self.source
        self.assertIn("Get-CimInstance -Query $query -ErrorAction Stop", src)
        self.assertIn("Get-CimInstance -Query (", src)
        self.assertIn("UCIE-C40-Recover", src)
        self.assertIn("ucie-private-c40.yaml", src)
        for forbidden in (
            "Get-ChildItem", "Get-CimInstance -ClassName Win32_Process",
            "CommandLine", "Get-Content", "ReadAllText", "ReadAllBytes",
            "Start-Process", "Stop-Process", "Restart-Service",
            "Start-ScheduledTask", "Stop-ScheduledTask", "Set-ScheduledTask",
            "Set-Content", "Invoke-RestMethod", "Invoke-WebRequest",
            "Get-WinEvent", "sqlite3.connect", "c40_mcp_round_trip_verified=$true",
            "full_cutover_authorized=$true",
        ):
            # Forbidden code may appear only in an explanatory source comment
            # for 'CommandLine'; remove that comment exception via exact check.
            if forbidden == "CommandLine":
                self.assertNotIn("CommandLine", src)
            else:
                self.assertNotIn(forbidden, src)


if __name__ == "__main__":
    unittest.main()
