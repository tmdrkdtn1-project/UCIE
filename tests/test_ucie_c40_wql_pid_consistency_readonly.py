"""UCIE-only pinned C40 process census comparison (READ ONLY).

Investigates intermittent WQL omission seen for already verified UCIE C40 PIDs.
Never lists arbitrary process command lines, modifies tasks, starts clients,
reads secrets, or touches any other project. Historical PIDs here are temporary
diagnostic anchors, not durable process identity for production.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess
import unittest


PROFILE = Path(r"D:\UCIE_DATA\mcp_tunnel_profiles\ucie-private-c40.yaml")


class UCIEC40WqlVsExactPidReadOnly(unittest.TestCase):
    def test_known_ucie_pid_wql_consistency(self):
        if os.name != "nt" or not PROFILE.is_file():
            self.skipTest("Not the pinned UCIE Windows host")
        shell = shutil.which("powershell.exe")
        if shell is None:
            self.skipTest("Windows PowerShell unavailable")
        script = r"""
$ErrorActionPreference = 'Stop'
$expectedExe = 'D:\UCIE_DATA\tools\tunnel-client-v0.0.16\tunnel-client.exe'
# PIDs were previously verified using exact UCIE executable/profile metadata.
# If either PID has exited, record that fact; do not treat it as a new client.
$knownUCIEPids = @(53556,57016)
$samples = @()
for ($sample=0; $sample -lt 10; $sample++) {
    $byPid = @()
    foreach ($targetPid in $knownUCIEPids) {
        $items = @(Get-CimInstance Win32_Process -Filter "ProcessId = $targetPid" -ErrorAction Stop)
        $byPid += @($items | Where-Object {
            [string]::Equals([string]$_.ExecutablePath,$expectedExe,[StringComparison]::OrdinalIgnoreCase) -and
            ([string]$_.CommandLine).Contains('ucie-private-c40')
        } | ForEach-Object { [int]$_.ProcessId })
    }
    $byWql = @(
        Get-CimInstance Win32_Process -Filter "Name = 'tunnel-client.exe' AND ExecutablePath LIKE '%UCIE_DATA%'" -ErrorAction Stop |
        Where-Object {
            [string]::Equals([string]$_.ExecutablePath,$expectedExe,[StringComparison]::OrdinalIgnoreCase) -and
            ([string]$_.CommandLine).Contains('ucie-private-c40') -and
            ($knownUCIEPids -contains [int]$_.ProcessId)
        } | ForEach-Object { [int]$_.ProcessId }
    )
    $byNative = @()
    foreach ($targetPid in $knownUCIEPids) {
        $process = Get-Process -Id $targetPid -ErrorAction SilentlyContinue
        if ($null -ne $process) {
            try {
                if ([string]::Equals([string]$process.Path,$expectedExe,[StringComparison]::OrdinalIgnoreCase)) {
                    $byNative += [int]$targetPid
                }
            }
            catch { }
        }
    }
    $samples += [pscustomobject]@{
        sequence=($sample+1)
        by_exact_pid=@($byPid | Sort-Object -Unique)
        by_wql_filter=@($byWql | Sort-Object -Unique)
        by_native_exact_pid=@($byNative | Sort-Object -Unique)
    }
    if ($sample -lt 9) { Start-Sleep -Milliseconds 100 }
}
$missed = @($samples | Where-Object {
    $s=$_
    @($s.by_exact_pid | Where-Object { $s.by_wql_filter -notcontains $_ }).Count -gt 0
}).Count
[pscustomobject]@{
    schema='UCIE_C40_WQL_PID_CONSISTENCY_READONLY_V1'
    samples=$samples
    samples_where_wql_missed_exact_pid=$missed
    no_process_started_or_stopped=$true
    no_task_modified=$true
    no_external_project_enumeration=$true
    original_executable_and_profile_only=$true
    raw_command_lines_withheld=$true
} | ConvertTo-Json -Depth 7 -Compress
"""
        result = subprocess.run(
            [shell, "-NoProfile", "-NonInteractive", "-Command", script],
            capture_output=True, text=True, timeout=40, check=False
        )
        self.assertEqual(result.returncode, 0, "UCIE-only diagnostic invocation failed")
        try:
            output = json.loads(result.stdout.strip().splitlines()[-1])
        except (ValueError, IndexError) as exc:
            raise AssertionError("No structured UCIE process diagnostic") from exc
        print("UCIE_C40_WQL_PID_CONSISTENCY=" + json.dumps(output, sort_keys=True))
        self.assertEqual(output["schema"], "UCIE_C40_WQL_PID_CONSISTENCY_READONLY_V1")
        self.assertEqual(len(output["samples"]), 10)
        self.assertTrue(output["no_process_started_or_stopped"])
        self.assertTrue(output["no_task_modified"])
        self.assertTrue(output["no_external_project_enumeration"])
        self.assertTrue(output["original_executable_and_profile_only"])
        self.assertTrue(output["raw_command_lines_withheld"])
        for sample in output["samples"]:
            for key in ("by_exact_pid", "by_wql_filter", "by_native_exact_pid"):
                self.assertTrue(
                    all(pid in (53556, 57016) for pid in sample[key]), (sample["sequence"], key)
                )


if __name__ == "__main__":
    unittest.main()
