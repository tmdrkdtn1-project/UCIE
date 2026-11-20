"""W36 TaskScheduler event 129 and Python redirector parent PID read-only tests.

The actual W36 PowerShell pure event matcher is AST-extracted. All events
are synthetic first-party data; CI NEVER reads native Windows event logs,
runs a scheduled task, opens owner SQLite, or calls C40.
"""
from __future__ import annotations

import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "scripts" / "ucie_owner_w36_task129_parent_event_readonly_v01.ps1"


def ps() -> str | None:
    return "powershell.exe" if os.name == "nt" else shutil.which("pwsh")


def invoke_ps(source: str) -> subprocess.CompletedProcess[str]:
    if not ps():
        raise RuntimeError("Native PowerShell not available")
    with tempfile.TemporaryDirectory(prefix="ucie_w36_event_mock_") as td:
        script = Path(td) / "bounded.ps1"
        script.write_text(source, encoding="utf-8")
        args = [ps(), "-NoProfile", "-NonInteractive"]
        if os.name == "nt":
            args += ["-ExecutionPolicy", "Bypass"]
        return subprocess.run(args + ["-File", str(script)], text=True,
                              capture_output=True, timeout=35)


def fixture() -> str:
    path = str(SOURCE).replace("'", "''")
    return rf"""
Set-StrictMode -Version Latest
$ErrorActionPreference='Stop'
$tok=$null;$err=$null
$ast=[Management.Automation.Language.Parser]::ParseFile('{path}',[ref]$tok,[ref]$err)
if(@($err).Count -ne 0){{throw 'UCIE_W36_NATIVE_SOURCE_PARSE_HOLD'}}
$matched=@($ast.FindAll({{param($node)
    ($node -is [Management.Automation.Language.FunctionDefinitionAst] -and
     $node.Name -ceq 'TestExactTask129ParentEvent')}},$true))
if($matched.Count -ne 1){{throw 'UCIE_W36_EXACT_FUNCTION_UNIQUE_HOLD'}}
. ([scriptblock]::Create($matched[0].Extent.Text))
$boundedFn=@($ast.FindAll({{param($node)
    ($node -is [Management.Automation.Language.FunctionDefinitionAst] -and
     $node.Name -ceq 'NewBoundedUcIeTask129FilterXml')}},$true))
if($boundedFn.Count -ne 1){{throw 'UCIE_W36_FILTERXML_BUILDER_NOT_UNIQUE'}}
. ([scriptblock]::Create($boundedFn[0].Extent.Text))
$xml=@'
<Event xmlns="http://schemas.microsoft.com/win/2004/08/events/event">
 <System><Provider Name="Microsoft-Windows-TaskScheduler"/>
 <EventID>129</EventID>
 <Channel>Microsoft-Windows-TaskScheduler/Operational</Channel></System>
 <EventData>
 <Data Name="TaskName">\UCIE-LocalV1-Web</Data>
 <Data Name="Path">D:\UCIE\.venv\Scripts\pythonw.exe</Data>
 <Data Name="ProcessID">42420</Data>
 </EventData>
</Event>
'@
$launch=[datetime]'2026-11-20T05:00:00Z'
$created=[datetime]'2026-11-20T05:00:03Z'
function Exact([string]$value,[datetime]$at,[datetime]$child,[int]$parent){{
    return TestExactTask129ParentEvent $value $at $child $parent '\UCIE-LocalV1-Web' 'D:\UCIE\.venv\Scripts\pythonw.exe'
}}
"""


class W36Task129ParentPidNativeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = SOURCE.read_text(encoding="utf-8")

    def native(self, tail: str) -> str:
        if not ps():
            self.skipTest("Native PowerShell unavailable")
        result = invoke_ps(fixture() + tail)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        return result.stdout

    def test_nohost_contract_and_no_orphan_approval(self):
        if not ps():
            self.skipTest("Native PowerShell unavailable")
        args = [ps(), "-NoProfile", "-NonInteractive"]
        if os.name == "nt":
            args += ["-ExecutionPolicy", "Bypass"]
        plain = subprocess.run(args + ["-File", str(SOURCE)],
                               capture_output=True, text=True, timeout=25)
        self.assertEqual(plain.returncode, 0, plain.stdout + plain.stderr)
        self.assertIn("UCIE_W36_CONTRACT_ONLY_NO_HOST_ACCESS", plain.stdout)
        self.assertIn('"event_log_queried_or_modified":false', plain.stdout)
        self.assertIn('"task_scheduler_queried_or_modified":false', plain.stdout)
        denied = subprocess.run(args + ["-File", str(SOURCE), "-InspectLocal"],
                                capture_output=True, text=True, timeout=25)
        self.assertNotEqual(denied.returncode, 0)
        self.assertIn("UCIE_W36_EXPLICIT_OWNER_READONLY_APPROVAL_REQUIRED",
                      denied.stdout + denied.stderr)

    def test_only_exact_microsoft_event129_task_pid_path_and_time_accepted(self):
        out = self.native(r"""
if(-not (Exact $xml $launch $created 42420)){
    throw 'UCIE_W36_EXPECTED_EXACT_EVENT_REJECTED'
}
if(Exact $xml $launch $created 42421){
    throw 'UCIE_W36_WRONG_PARENT_PID_ACCEPTED'
}
if(Exact $xml $launch ($created.AddSeconds(70)) 42420){
    throw 'UCIE_W36_OLD_EVENT_ACCEPTED'
}
if(Exact $xml ($launch.AddSeconds(8)) $created 42420){
    throw 'UCIE_W36_FUTURE_EVENT_ACCEPTED'
}
Write-Output 'UCIE_W36_EXACT_EVENT_AND_TEMPORAL_NEGATIVES_PASS'
""")
        self.assertIn("UCIE_W36_EXACT_EVENT_AND_TEMPORAL_NEGATIVES_PASS", out)

    def test_forged_event_fields_or_provider_denied(self):
        out = self.native(r"""
foreach($bad in @(
  $xml.Replace('Microsoft-Windows-TaskScheduler','Foreign-Provider'),
  $xml.Replace('<EventID>129</EventID>','<EventID>200</EventID>'),
  $xml.Replace('Operational</Channel>','Other</Channel>'),
  $xml.Replace('\UCIE-LocalV1-Web','\DIFFERENT-TASK'),
  $xml.Replace('D:\UCIE\.venv\Scripts\pythonw.exe','D:\OTHER\pythonw.exe'),
  $xml.Replace('<Data Name="ProcessID">42420</Data>','<Data Name="ProcessID">123</Data>'),
  $xml.Replace('<Data Name="ProcessID">42420</Data>','<Data Name="ProcessID">42420</Data><Data Name="ProcessID">42420</Data>'),
  $xml.Replace('<Data Name="ProcessID">42420</Data>','<Data Name="ProcessID">0xA5B4</Data>'),
  '<Event><unclosed',
  ('x' * 17000)
)){
    if(Exact $bad $launch $created 42420){
        throw 'UCIE_W36_ACCEPTED_FORGED_EVENT_FIELD'
    }
}
Write-Output 'UCIE_W36_PROVIDER_SCHEMA_PID_NEGATIVES_PASS'
""")
        self.assertIn("UCIE_W36_PROVIDER_SCHEMA_PID_NEGATIVES_PASS", out)

    def test_server_side_filter_scopes_to_ucie_task_only(self):
        out = self.native(r"""
$q=NewBoundedUcIeTask129FilterXml $created
$node=$q.SelectSingleNode('/QueryList/Query/Select')
if($null -eq $node){throw 'UCIE_W36_FILTERXML_NO_SELECT'}
$xpath=$node.InnerText
if(-not $xpath.Contains('EventID=129') -or
   -not $xpath.Contains("Data[@Name='TaskName']='\UCIE-LocalV1-Web'") -or
   -not $xpath.Contains("Data[@Name='Path']='D:\UCIE\.venv\Scripts\pythonw.exe'") -or
   -not $xpath.Contains('@SystemTime >=') -or
   -not $xpath.Contains('@SystemTime <=') -or
   -not $xpath.Contains('04:58:03') -or
   -not $xpath.Contains('05:02:03')){
    throw 'UCIE_W36_UNBOUNDED_OR_UNSCOPED_EVENT_QUERY'
}
Write-Output 'UCIE_W36_TASK_ONLY_FILTER_XML_PASS'
""")
        self.assertIn("UCIE_W36_TASK_ONLY_FILTER_XML_PASS", out)

    def test_source_is_bounded_readonly_and_does_not_claim_launch(self):
        s = self.source
        self.assertIn("Get-WinEvent -FilterXml $onlyUcIeEvents", s)
        self.assertIn("NewBoundedUcIeTask129FilterXml", s)
        self.assertNotIn("Get-WinEvent -FilterHashtable", s)
        self.assertIn("-MaxEvents 128 -ErrorAction Stop", s)
        self.assertIn("Get-NetTCPConnection -LocalPort 18767 -State Listen", s)
        self.assertIn("Get-CimInstance -ClassName Win32_Process -Filter", s)
        self.assertIn("listener_pid_launched_by_task_scheduler_verified=$false", s)
        self.assertIn("security4688_creation_event_verified=$false", s)
        self.assertIn("full_cutover_authorized=$false", s)
        self.assertIn("b6420a1b00336d62907440078947a50ffbc3af51", s)
        self.assertNotIn("Start-ScheduledTask", s)
        self.assertNotIn("Stop-ScheduledTask", s)
        self.assertNotIn("Set-ScheduledTask", s)
        self.assertNotIn("Enable-ScheduledTask", s)
        self.assertNotIn("Stop-Process", s)
        self.assertNotIn("Start-Process", s)
        self.assertNotIn("Get-WinEvent -LogName", s)
        self.assertNotIn("sqlite3.connect", s)
        self.assertNotIn("Get-ChildItem D:", s)


if __name__ == "__main__":
    unittest.main()
