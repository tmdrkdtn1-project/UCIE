"""W35: native PowerShell runs REAL W31 venv resolver against disposable files.

No owner Windows host, Task Scheduler, C40, operating SQLite, network access,
or UAC is touched. The only CIM/TCP calls are first-party in-memory fakes.
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


def powershell():
    return "powershell.exe" if os.name == "nt" else shutil.which("pwsh")


def ps_quote(value):
    return str(value).replace("'", "''")


PS_TEMPLATE = r"""
Set-StrictMode -Version Latest
$ErrorActionPreference='Stop'
$tok=$null;$err=$null
$ast=[Management.Automation.Language.Parser]::ParseFile('__SOURCE__',[ref]$tok,[ref]$err)
if(@($err).Count -ne 0){throw 'UCIE_W35_SOURCE_PARSE_HOLD'}
foreach($name in @('AssertExactOriginalCommandLine',
                   'GetVenvRedirectorBasePythonw',
                   'AssertOwnerLocalListenerPidIdentity')){
    $matched=@($ast.FindAll({param($node)
        ($node -is [Management.Automation.Language.FunctionDefinitionAst] -and
         $node.Name -ceq $name)},$true))
    if($matched.Count -ne 1){throw 'UCIE_W35_UNIQUE_REAL_FUNCTION_REQUIRED'}
    . ([scriptblock]::Create($matched[0].Extent.Text))
}
$script:ownerSid='S-1-5-21-UCIE-SYNTHETIC'
$script:fakeOwner=$script:ownerSid
$script:fakeRebind=$false
$script:tcpCount=0
$specs=@(
  [pscustomobject]@{Exe='ignored1';Arguments='ignored1'},
  [pscustomobject]@{Exe='ignored2';Arguments='ignored2'},
  [pscustomobject]@{Exe='__LAUNCHER__';Arguments='-B "D:\UCIE\scripts\run_ucie_local_v1_autostart.py" --port 18767'}
)
$script:mockImage='__IMAGE__'
$script:mockArgs='"__LAUNCHER__" '+$specs[2].Arguments
function Get-NetTCPConnection {
    [CmdletBinding()]
    param([int]$LocalPort,[string]$State)
    if($LocalPort -ne 18767 -or $State -cne 'Listen'){
        throw 'UCIE_W35_OTHER_PORT_QUERY_DENIED'
    }
    $script:tcpCount++
    if($script:fakeRebind -and $script:tcpCount -gt 1){
        return [pscustomobject]@{LocalAddress='127.0.0.1';LocalPort=18767;OwningProcess=42421}
    }
    return [pscustomobject]@{LocalAddress='127.0.0.1';LocalPort=18767;OwningProcess=42420}
}
function Get-CimInstance {
    [CmdletBinding()]
    param([string]$ClassName,[string]$Filter)
    if($ClassName -cne 'Win32_Process' -or $Filter -cne 'ProcessId = 42420'){
        throw 'UCIE_W35_OTHER_PROCESS_QUERY_DENIED'
    }
    return [pscustomobject]@{ProcessId=42420;ExecutablePath=$script:mockImage;CommandLine=$script:mockArgs}
}
function Invoke-CimMethod {
    [CmdletBinding()]
    param($InputObject,[string]$MethodName)
    if($MethodName -cne 'GetOwnerSid' -or [int]$InputObject.ProcessId -ne 42420){
        throw 'UCIE_W35_OTHER_CIM_METHOD_DENIED'
    }
    return [pscustomobject]@{ReturnValue=0;Sid=$script:fakeOwner}
}
__TAIL__
"""


class W35VenvBaseImageReadOnlyNativeTests(unittest.TestCase):
    def run_fixture(
        self, tail, *, config="valid", image="base", owner="same",
        change_args=False, rebind=False
    ):
        if not powershell():
            self.skipTest("Native PowerShell not installed")
        with tempfile.TemporaryDirectory(prefix="ucie_w35_synthetic_") as td:
            root = Path(td)
            scripts = root / "old_venv" / "Scripts"
            scripts.mkdir(parents=True)
            launcher = scripts / "pythonw.exe"
            launcher.write_bytes(b"UCIE SYNTHETIC ONLY")
            base = root / "base_python"
            base.mkdir()
            base_image = base / "pythonw.exe"
            base_image.write_bytes(b"UCIE SYNTHETIC ONLY")
            foreign = root / "different_python"
            foreign.mkdir()
            foreign_image = foreign / "pythonw.exe"
            foreign_image.write_bytes(b"UCIE SYNTHETIC ONLY")
            cfg = scripts.parent / "pyvenv.cfg"
            if config == "valid":
                cfg.write_text("home = " + str(base) + "\ninclude-system-site-packages = false\n",
                               encoding="utf-8")
            elif config == "duplicate":
                cfg.write_text("home = " + str(base) + "\nhome = " + str(foreign),
                               encoding="utf-8")
            elif config == "relative":
                cfg.write_text("home = relative_path", encoding="utf-8")
            elif config == "oversized":
                cfg.write_text("home = " + str(base) + "\n" + ("x" * 8192),
                               encoding="utf-8")
            elif config == "absent":
                pass
            else:
                raise AssertionError("unknown fixture config")

            target = {"base": base_image, "different": foreign_image,
                      "direct": launcher}[image]
            test_script = (PS_TEMPLATE.replace("__SOURCE__", ps_quote(SOURCE))
                           .replace("__LAUNCHER__", ps_quote(launcher))
                           .replace("__IMAGE__", ps_quote(target))
                           .replace("__TAIL__", tail))
            if owner != "same":
                test_script += "\n"  # owner switch set by tail in the target run
            with tempfile.TemporaryDirectory(prefix="ucie_w35_runner_") as runner:
                ps_path = Path(runner) / "test_w35.ps1"
                ps_path.write_text(test_script, encoding="utf-8")
                command = [powershell(), "-NoProfile", "-NonInteractive"]
                if os.name == "nt":
                    command += ["-ExecutionPolicy", "Bypass"]
                result = subprocess.run(command + ["-File", str(ps_path)],
                                        capture_output=True, text=True, timeout=35)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            return result.stdout

    def test_actual_real_functions_accept_only_matching_venv_base_pythonw(self):
        out = self.run_fixture(r"""
$r=AssertOwnerLocalListenerPidIdentity
if($r.direct_original_task_binary -ne $false -or
   $r.venv_base_pythonw_redirector_consistent -ne $true -or
   $script:tcpCount -ne 2){
    throw 'UCIE_W35_VALID_BASE_NOT_CLASSIFIED_CORRECTLY'
}
Write-Output 'UCIE_W35_BASE_IMAGE_EXACT_CONFIG_MATCH_PASS'
""")
        self.assertIn("UCIE_W35_BASE_IMAGE_EXACT_CONFIG_MATCH_PASS", out)

    def test_unrelated_python_executable_denied(self):
        out = self.run_fixture(r"""
try {
    [void](AssertOwnerLocalListenerPidIdentity)
    throw 'UCIE_W35_WRONG_IMAGE_ACCEPTED'
} catch {
    if($_.Exception.Message -cne 'UCIE_W35_LISTENER_BASE_PYTHONW_IMAGE_MISMATCH_HOLD'){throw}
}
Write-Output 'UCIE_W35_WRONG_BASE_IMAGE_HOLD_PASS'
""", image="different")
        self.assertIn("UCIE_W35_WRONG_BASE_IMAGE_HOLD_PASS", out)

    def test_missing_duplicate_relative_or_oversized_venv_config_denied(self):
        for config, expected in (
            ("absent", "UCIE_W35_VENV_REDIRECTOR_FILE_UNAVAILABLE_HOLD"),
            ("duplicate", "UCIE_W35_VENV_HOME_NOT_UNIQUE_HOLD"),
            ("relative", "UCIE_W35_VENV_HOME_NOT_CANONICAL_LOCAL_HOLD"),
            ("oversized", "UCIE_W35_VENV_CONFIG_SIZE_HOLD"),
        ):
            with self.subTest(config=config):
                out = self.run_fixture(r"""
try {
    [void](AssertOwnerLocalListenerPidIdentity)
    throw 'UCIE_W35_BAD_CONFIG_ACCEPTED'
} catch {
    if($_.Exception.Message -cne '__EXPECTED__'){throw}
}
Write-Output 'UCIE_W35_BAD_CONFIG_HOLD_PASS'
""".replace("__EXPECTED__", expected), config=config)
                self.assertIn("UCIE_W35_BAD_CONFIG_HOLD_PASS", out)

    def test_wrong_cli_and_owner_denied_before_redirector_config_read(self):
        out = self.run_fixture(r"""
$script:mockArgs='"__LAUNCHER__" --extra'
try {
    [void](AssertOwnerLocalListenerPidIdentity)
    throw 'UCIE_W35_BAD_CLI_ACCEPTED'
} catch {
    if($_.Exception.Message -cne 'UCIE_W31_LISTENER_ARGS_COMMANDLINE_MISMATCH_HOLD'){throw}
}
Write-Output 'UCIE_W35_BAD_ARGV_HOLD_PASS'
""", config="absent")
        self.assertIn("UCIE_W35_BAD_ARGV_HOLD_PASS", out)
        out = self.run_fixture(r"""
$script:fakeOwner='S-1-5-21-NOT-OWNER'
try {
    [void](AssertOwnerLocalListenerPidIdentity)
    throw 'UCIE_W35_DIFFERENT_OWNER_ACCEPTED'
} catch {
    if($_.Exception.Message -cne 'UCIE_W31_LISTENER_PROCESS_OWNER_SID_HOLD'){throw}
}
Write-Output 'UCIE_W35_FOREIGN_OWNER_HOLD_PASS'
""", config="absent")
        self.assertIn("UCIE_W35_FOREIGN_OWNER_HOLD_PASS", out)

    def test_changed_listener_pid_rejected_after_base_image_check(self):
        out = self.run_fixture(r"""
$script:fakeRebind=$true
try {
    [void](AssertOwnerLocalListenerPidIdentity)
    throw 'UCIE_W35_REBOUND_PID_ACCEPTED'
} catch {
    if($_.Exception.Message -cne 'UCIE_W31_LISTENER_PID_CHANGED_DURING_READONLY_HOLD'){throw}
}
Write-Output 'UCIE_W35_PID_RACE_HOLD_PASS'
""")
        self.assertIn("UCIE_W35_PID_RACE_HOLD_PASS", out)

    def test_direct_binary_remains_valid_without_venv_config(self):
        out = self.run_fixture(r"""
$r=AssertOwnerLocalListenerPidIdentity
if($r.direct_original_task_binary -ne $true -or
   $r.venv_base_pythonw_redirector_consistent -ne $false){
    throw 'UCIE_W35_DIRECT_BINARY_REGRESSION'
}
Write-Output 'UCIE_W35_DIRECT_IMAGE_NO_CONFIG_PASS'
""", config="absent", image="direct")
        self.assertIn("UCIE_W35_DIRECT_IMAGE_NO_CONFIG_PASS", out)

    def test_source_holds_provenance_and_privacy():
        source = SOURCE.read_text(encoding="utf-8")
        self.assertIn("GetVenvRedirectorBasePythonw $expected.Exe", source)
        self.assertIn("UCIE_W35_VENV_BASE_PYTHONW_CLI_OWNER_CONFIG_CONSISTENT__TASK_LAUNCH_LINK_HOLD", source)
        self.assertIn("listener_binary_matches_original_task=[bool]$listenerIdentity.direct_original_task_binary", source)
        self.assertIn("listener_pid_launched_by_task_scheduler_verified=$false", source)
        self.assertIn("c40_mcp_round_trip_verified=$false", source)
        self.assertIn("full_cutover_authorized=$false", source)
        self.assertNotIn("Stop-ScheduledTask", source)
        self.assertNotIn("Start-ScheduledTask", source)
        self.assertNotIn("Stop-Process", source)


if __name__ == "__main__":
    unittest.main()
