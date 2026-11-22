"""UCIE-only exact historical C40 PID visibility and access diagnostic.

Read-only and restricted to two preverified UCIE C40 process IDs. Outputs no
owner name, SID, credentials, raw process command lines or other project data.
The process IDs are ephemeral observations; never use them as static authority.
"""
import json
import os
from pathlib import Path
import shutil
import subprocess
import unittest

UCIE_PROFILE = Path(r"D:\UCIE_DATA\mcp_tunnel_profiles\ucie-private-c40.yaml")


class C40ExactPidVisibility(unittest.TestCase):
    def test_known_ucie_pids_accessible_properties(self):
        if os.name != "nt" or not UCIE_PROFILE.is_file():
            self.skipTest("not the exact UCIE owner host")
        shell = shutil.which("powershell.exe")
        if shell is None:
            self.skipTest("Windows PowerShell absent")
        command = r"""
$ErrorActionPreference = 'Stop'
$path = 'D:\UCIE_DATA\tools\tunnel-client-v0.0.16\tunnel-client.exe'
$identity = [Security.Principal.WindowsIdentity]::GetCurrent()
$principal = New-Object Security.Principal.WindowsPrincipal($identity)
$elevated = $principal.IsInRole(
    [Security.Principal.WindowsBuiltInRole]::Administrator
)
$session = (Get-Process -Id $PID -ErrorAction Stop).SessionId
$items = @()
foreach ($knownPid in @(53556,57016)) {
    $native = Get-Process -Id $knownPid -ErrorAction SilentlyContinue
    $nativePath = ''
    if ($null -ne $native) {
        try { $nativePath = [string]$native.Path } catch {}
    }
    $cim = @(Get-CimInstance Win32_Process -Filter "ProcessId = $knownPid" -ErrorAction Stop)
    $exact = @($cim | Where-Object { [int]$_.ProcessId -eq $knownPid })
    $cimPath = if ($exact.Count -eq 1) { [string]$exact[0].ExecutablePath } else { '' }
    $line = if ($exact.Count -eq 1) { [string]$exact[0].CommandLine } else { '' }
    $items += [pscustomobject]@{
        pid = $knownPid
        native_process_exists = ($null -ne $native)
        native_path_available = -not [string]::IsNullOrEmpty($nativePath)
        native_path_ucie_exact = [string]::Equals($nativePath,$path,[StringComparison]::OrdinalIgnoreCase)
        cim_process_exists = ($exact.Count -eq 1)
        cim_path_available = -not [string]::IsNullOrEmpty($cimPath)
        cim_path_ucie_exact = [string]::Equals($cimPath,$path,[StringComparison]::OrdinalIgnoreCase)
        cim_profile_marker_readable = $line.Contains('ucie-private-c40')
    }
}
[pscustomobject]@{
    schema = 'UCIE_C40_EXACT_PID_VISIBILITY_READONLY_V1'
    caller_elevated = [bool]$elevated
    caller_session_id = [int]$session
    pids = $items
    raw_identity_and_command_line_withheld = $true
    processes_started_or_stopped = $false
    tasks_modified = $false
} | ConvertTo-Json -Depth 5 -Compress
"""
        run = subprocess.run(
            [shell, "-NoProfile", "-NonInteractive", "-Command", command],
            capture_output=True, text=True, timeout=30, check=False
        )
        self.assertEqual(run.returncode, 0, "UCIE-only PID introspection failed")
        row = json.loads(run.stdout.strip().splitlines()[-1])
        print("UCIE_C40_PID_VISIBILITY=" + json.dumps(row, sort_keys=True))
        self.assertEqual(row["schema"], "UCIE_C40_EXACT_PID_VISIBILITY_READONLY_V1")
        self.assertTrue(row["raw_identity_and_command_line_withheld"])
        self.assertFalse(row["processes_started_or_stopped"])
        self.assertFalse(row["tasks_modified"])
        self.assertEqual([x["pid"] for x in row["pids"]], [53556, 57016])


if __name__ == "__main__":
    unittest.main()
