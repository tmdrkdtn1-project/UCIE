"""Read-only UCIE-only pinned C40 process count cross-check.

Only exact UCIE_DATA tunnel executable and profile markers are inspected.
No raw command lines, owner names, environment, tokens or other project data.
"""
from __future__ import annotations
import json
import os
from pathlib import Path
import shutil
import subprocess
import unittest

PROFILE = Path(r"D:\UCIE_DATA\mcp_tunnel_profiles\ucie-private-c40.yaml")


class UCIEC40ProcessConsistency(unittest.TestCase):
    def test_pinned_tunnel_process_consistency_readonly(self):
        if os.name != "nt" or not PROFILE.is_file():
            self.skipTest("not UCIE owner Windows host")
        exe = shutil.which("powershell.exe")
        if not exe:
            self.skipTest("PowerShell unavailable")
        script = r"""
$ErrorActionPreference = 'Stop'
$client = 'D:\UCIE_DATA\tools\tunnel-client-v0.0.16\tunnel-client.exe'
$records = @(
    Get-CimInstance Win32_Process -Filter "Name = 'tunnel-client.exe' AND ExecutablePath LIKE '%UCIE_DATA%'" -ErrorAction Stop |
    Where-Object {
        [string]::Equals([string]$_.ExecutablePath,$client,[StringComparison]::OrdinalIgnoreCase)
    } |
    ForEach-Object {
        [pscustomobject]@{
            pid = [int]$_.ProcessId
            c40_profile = ([string]$_.CommandLine).IndexOf('ucie-private-c40',[StringComparison]::OrdinalIgnoreCase) -ge 0
            profile_file_arg = ([string]$_.CommandLine).Contains('--profile-file')
            client_run_arg = ([string]$_.CommandLine).Contains('run')
            started_utc = if ($_.CreationDate) {$_.CreationDate.ToUniversalTime().ToString('o')} else {'UNKNOWN'}
        }
    }
)
$match = @($records | Where-Object { $_.c40_profile })
[pscustomobject]@{
    schema='UCIE_C40_EXACT_PROCESS_DIAGNOSTIC_V1'
    pinned_executable_count=$records.Count
    c40_marked_count=$match.Count
    processes=@($records | Sort-Object pid)
    process_or_task_changed=$false
    all_raw_arguments_withheld=$true
} | ConvertTo-Json -Depth 5 -Compress
"""
        r = subprocess.run([exe,"-NoProfile","-NonInteractive","-Command",script],
                           capture_output=True,text=True,timeout=30,check=False)
        self.assertEqual(r.returncode,0, "UCIE process diagnostic failed")
        d=json.loads(r.stdout.strip().splitlines()[-1])
        print("UCIE_C40_PROCESS_CROSSCHECK="+json.dumps(d,sort_keys=True))
        self.assertEqual(d["schema"],"UCIE_C40_EXACT_PROCESS_DIAGNOSTIC_V1")
        self.assertTrue(d["all_raw_arguments_withheld"])
        self.assertFalse(d["process_or_task_changed"])
        self.assertEqual(d["pinned_executable_count"],len(d["processes"]))
        self.assertEqual(d["c40_marked_count"],sum(1 for p in d["processes"] if p["c40_profile"]))
        # Do not assert a single client here: this is diagnosing a reported duplicate.


if __name__ == "__main__":
    unittest.main()
