"""UCIE C40 supervisor exact-function read-only preflight, no task start.

Runs *only* pre-existing UCIE recovery script in its default read-only
Status mode, then calls its exact task identity and C40 observation functions.
Never executes Supervise, Once, Install, Start-Process or task mutations.
"""
import json
import os
from pathlib import Path
import shutil
import subprocess
import unittest

P = Path(r"D:\UCIE\scripts\ucie_c40_recover.ps1")
PROFILE = Path(r"D:\UCIE_DATA\mcp_tunnel_profiles\ucie-private-c40.yaml")


class UCIEC40SupervisorReadOnlyPreflight(unittest.TestCase):
    def test_exact_script_supervisor_gates(self):
        if os.name != "nt" or not P.is_file() or not PROFILE.is_file():
            self.skipTest("not approved UCIE Windows host")
        shell = shutil.which("powershell.exe")
        if not shell:
            self.skipTest("no Windows PowerShell")
        ps = r"""
$ErrorActionPreference='Stop'
$stage='SOURCED_STATUS'
$failed='NONE'
$taskOk=$false
$clientOk=$false
$clientCount=-1
try {
    . 'D:\UCIE\scripts\ucie_c40_recover.ps1' -Mode Status -EnableAdminTools | Out-Null
    $stage='TASK_IDENTITY'
    $task = Assert-ApprovedRecoveryTask
    $taskOk = $null -ne $task
    $stage='CLIENT_OBSERVATION_NO_START'
    $client = One-C40Check -StartMissing:$false
    $clientOk = $client.status -eq 'UCIE_C40_ALREADY_RUNNING'
    $clientCount = [int]$client.tunnel_clients
    $stage='FINISHED'
}
catch {
    $v = [string]$_.Exception.Message
    if ($v -match 'UCIE_C40_[A-Z0-9_]+') { $failed = $Matches[0] }
    else { $failed = 'OTHER_EXCEPTION' }
}
[pscustomobject]@{
 schema='UCIE_C40_EXACT_GATES_READONLY_V1'
 stage=$stage
 fault=$failed
 task_identity_pass=[bool]$taskOk
 original_client_present=[bool]$clientOk
 client_count=$clientCount
 started_client=$false
 started_task=$false
 changed_task=$false
} | ConvertTo-Json -Compress
"""
        r=subprocess.run([shell,"-NoProfile","-NonInteractive","-Command",ps],
                         capture_output=True,text=True,timeout=30,check=False)
        self.assertEqual(r.returncode,0,"UCIE read-only preflight command error")
        try:
            row=json.loads(r.stdout.strip().splitlines()[-1])
        except (ValueError,IndexError) as exc:
            raise AssertionError("missing UCIE diagnostic JSON") from exc
        print("UCIE_C40_EXACT_GATES_READONLY="+json.dumps(row,sort_keys=True))
        self.assertEqual(row["schema"],"UCIE_C40_EXACT_GATES_READONLY_V1")
        self.assertEqual(row["stage"],"FINISHED",row["fault"])
        self.assertTrue(row["task_identity_pass"])
        self.assertTrue(row["original_client_present"])
        self.assertEqual(row["client_count"],1)
        self.assertFalse(row["started_client"])
        self.assertFalse(row["started_task"])
        self.assertFalse(row["changed_task"])


if __name__=="__main__":
    unittest.main()
