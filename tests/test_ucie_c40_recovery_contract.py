"""UCIE C40-only logon recovery installer static guardrails and PS parser.

No scheduled tasks created in CI or local tests. No tunnel process started.
"""
import os
from pathlib import Path
import re
import shutil
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "ucie_c40_recover.ps1"


class C40RecoveryContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = SCRIPT.read_text(encoding="utf-8")

    def test_one_exact_recovery_task(self):
        self.assertIn("$taskName = 'UCIE-C40-Recover'", self.source)
        self.assertIn("Get-ScheduledTask -TaskName $taskName", self.source)
        self.assertIn("Register-ScheduledTask -TaskName $taskName", self.source)
        self.assertIn("Unregister-ScheduledTask -TaskName $taskName", self.source)

    def test_existing_c40_only(self):
        self.assertIn("ucie-private-c40.yaml", self.source)
        self.assertIn("tunnel-client-v0.0.16", self.source)
        self.assertIn("UCIE_C40_PROFILE_ID_NOT_UNIQUE_STOP", self.source)
        self.assertIn("UCIE_C40_SERVER_SHA_CHANGED_STOP", self.source)
        self.assertNotIn("tunnel create", self.source.lower())

    def test_no_unbounded_process_access(self):
        self.assertIn("ExecutablePath LIKE '%UCIE_DATA%'", self.source)
        self.assertIn("UCIE_C40_DUPLICATE_CLIENT_STOP", self.source)
        self.assertIn("UCIE_C40_UNRECOGNIZED_CLIENT_STOP", self.source)
        self.assertIn("if ($items.Count -eq 1)", self.source)

    def test_existing_other_ucie_tasks_never_targeted(self):
        for phrase in ("UCIE-PublicMiner-Hourly", "UCIE-Internal-Minute",
                       "Remove-ScheduledTask", "Stop-Process", "taskkill",
                       "Stop-Service", "New-Service", "Set-ScheduledTask"):
            with self.subTest(phrase=phrase):
                self.assertNotIn(phrase, self.source)

    def test_inert_default_and_no_autoenrollment(self):
        self.assertIn("[string]$Mode = 'Status'", self.source)
        self.assertIn("UCIE_C40_RECOVERY_STATUS_READONLY", self.source)
        self.assertNotIn("owner_scoped_batch_v1", self.source)
        self.assertNotIn("grant.json", self.source)

    def test_one_time_owner_approval_for_install(self):
        self.assertIn("if ($Mode -eq 'Install')", self.source)
        self.assertIn("if (-not $OwnerOnlyConfirmed)", self.source)
        self.assertIn("$decision = Read-Host", self.source)
        self.assertIn("if ($decision -cne 'APPROVE')", self.source)
        self.assertIn("UCIE_C40_TASK_EXISTS_NO_OVERWRITE", self.source)

    def test_task_is_owner_logon_only_with_no_password_storage(self):
        self.assertIn("New-ScheduledTaskPrincipal -UserId", self.source)
        self.assertIn("-LogonType Interactive -RunLevel Highest", self.source)
        self.assertIn("New-ScheduledTaskTrigger -AtLogOn", self.source)
        self.assertNotIn("-Password", self.source)
        self.assertNotIn("-AtStartup", self.source)
        self.assertNotIn("-UserId 'SYSTEM'", self.source)

    def test_5min_supervision_and_no_replacement_of_live_client(self):
        self.assertIn("if ($Mode -eq 'Supervise')", self.source)
        self.assertIn("Start-Sleep -Seconds 300", self.source)
        self.assertIn("One-C40Check -StartMissing", self.source)
        self.assertIn("UCIE_C40_ALREADY_RUNNING", self.source)

    def test_once_supervisor_require_registered_owner_task(self):
        self.assertIn("function Assert-ApprovedRecoveryTask", self.source)
        self.assertIn("UCIE_C40_TASK_OWNER_OR_ACTION_MISMATCH", self.source)
        self.assertIn("UCIE_C40_ADMIN_MODE_MISMATCH", self.source)
        self.assertRegex(self.source, r"if \(\$Mode -eq 'Once'\) \{\s+\$task = Assert-ApprovedRecoveryTask")
        self.assertIn("if ($Mode -eq 'Supervise') {", self.source)
        self.assertIn("Save-C40SupervisorReceipt -Stage 'PROCESS_STARTED'", self.source)
        self.assertIn("$task = Assert-ApprovedRecoveryTask", self.source)
        self.assertIn("Save-C40SupervisorReceipt -Stage 'TASK_IDENTITY_OK'", self.source)

    def test_task_owner_is_resolved_via_sid_not_account_name(self):
        self.assertIn("GetCurrent().User.Value", self.source)
        self.assertIn("Security.Principal.NTAccount", self.source)
        self.assertIn("Security.Principal.SecurityIdentifier", self.source)
        self.assertIn("UCIE_C40_TASK_PRINCIPAL_UNRESOLVED", self.source)
        self.assertNotIn("$identity = [Security.Principal.WindowsIdentity]::GetCurrent().Name", self.source)

    def test_supervisor_emits_only_bounded_ucie_health_codes(self):
        self.assertIn("c40_supervisor_health_v1.json", self.source)
        self.assertIn("Save-C40SupervisorReceipt -Stage 'PROCESS_STARTED'", self.source)
        self.assertIn("Save-C40SupervisorReceipt -Stage 'TASK_IDENTITY_FAILED'", self.source)
        self.assertIn("Save-C40SupervisorReceipt -Stage 'CYCLE_OK'", self.source)
        self.assertIn("Save-C40SupervisorReceipt -Stage 'CYCLE_FAILED'", self.source)
        self.assertIn("NON_UCIE_EXCEPTION", self.source)
        self.assertNotIn("$_.ScriptStackTrace", self.source)
        self.assertNotIn("Write-EventLog", self.source)

    def test_startmissing_requires_switch_parameter(self):
        self.assertIn("param([switch]$StartMissing)", self.source)
        self.assertNotIn("param([bool]$StartMissing", self.source)
        self.assertEqual(self.source.count("One-C40Check -StartMissing"), 2)

    def test_supervisor_one_cycle_switch_runtime_no_tunnel(self):
        shell = shutil.which("pwsh") or shutil.which("powershell.exe")
        if not shell:
            self.skipTest("PowerShell unavailable")
        scriptpath = str(SCRIPT).replace("'", "''")
        ps = r'''
$ErrorActionPreference = 'Stop'
$tok = $null; $errors = $null
$ast = [System.Management.Automation.Language.Parser]::ParseFile(
    'SCRIPT_PATH', [ref]$tok, [ref]$errors)
if ($errors.Count -gt 0) { throw 'UCIE_C40_SCRIPT_PARSE_FAILURE' }
$fun = @($ast.FindAll({
    param($a) $a -is [System.Management.Automation.Language.FunctionDefinitionAst] -and
        $a.Name -eq 'One-C40Check'
}, $true))
if ($fun.Count -ne 1) { throw 'UCIE_C40_EXACT_FUNCTION_NOT_FOUND' }
Invoke-Expression $fun[0].Extent.Text
# Synthetic UCIE process only: no real CIM calls, tunnel starts, tasks or DB.
function Find-C40 {
    return @([pscustomobject]@{ ProcessId=111; CommandLine='ucie-private-c40' })
}
$present = One-C40Check -StartMissing
$inactive = One-C40Check -StartMissing:$false
if ($present.status -ne 'UCIE_C40_ALREADY_RUNNING' -or
    $present.tunnel_clients -ne 1 -or
    $inactive.status -ne 'UCIE_C40_ALREADY_RUNNING' -or
    $inactive.tunnel_clients -ne 1) {
    throw 'UCIE_C40_SWITCH_BEHAVIOR_FAILED'
}
'''
        ps = ps.replace("SCRIPT_PATH", scriptpath)
        result = subprocess.run(
            [shell, "-NoProfile", "-NonInteractive", "-Command", ps],
            capture_output=True, text=True, timeout=25, check=False)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_missing_c40_launch_requires_highest_running_owner(self):
        self.assertIn("function Assert-C40LaunchAuthority", self.source)
        self.assertIn("UCIE_C40_LAUNCH_REQUIRES_RUNNING_HIGHEST_TASK", self.source)
        self.assertIn("UCIE_C40_ELEVATED_OWNER_REQUIRED_FOR_LAUNCH", self.source)
        self.assertIn("UCIE_C40_CLIENT_APPEARED_ABORT_LAUNCH", self.source)
        self.assertIn("Assert-C40LaunchAuthority", self.source)
        self.assertIn("UCIE_C40_ELEVATED_OWNER_REQUIRED_FOR_INSTALL", self.source)
        self.assertIn("-LogonType Interactive -RunLevel Highest", self.source)

    def test_only_child_process_receives_legacy_guard(self):
        self.assertIn("$oldApproval = $env:UCIE_MCP_OWNER_APPROVAL", self.source)
        self.assertIn("$env:UCIE_MCP_OWNER_APPROVAL = $oldApproval", self.source)
        self.assertIn("$env:UCIE_ADMIN_TOOLS_ENABLED = if ($EnableAdminTools)", self.source)
        self.assertIn("$env:UCIE_ADMIN_TOOLS_ENABLED = $oldFlag", self.source)
        self.assertIn("finally {", self.source)

    def test_remove_targets_this_task_only(self):
        self.assertIn("if ($Mode -eq 'Remove')", self.source)
        self.assertIn("Unregister-ScheduledTask -TaskName $taskName -Confirm:$false", self.source)
        self.assertIn("running_c40_not_terminated=$true", self.source)

    def test_windows_or_pwsh_parser_accepts_script(self):
        shell = shutil.which("pwsh") or shutil.which("powershell.exe")
        if not shell:
            self.skipTest("PowerShell parser unavailable")
        escaped = str(SCRIPT).replace("'", "''")
        command = (
            "$t=$null;$e=$null;"
            f"[void][System.Management.Automation.Language.Parser]::ParseFile('{escaped}',[ref]$t,[ref]$e);"
            "if($e.Count -gt 0){$e | ForEach-Object {$_.Message}; exit 2}"
        )
        p = subprocess.run([shell, "-NoProfile", "-NonInteractive", "-Command", command],
                           capture_output=True, text=True, timeout=25, check=False)
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)


    def test_real_ucie_host_status_readonly_when_available(self):
        if os.name != "nt" or not Path(
            r"D:\UCIE_DATA\mcp_tunnel_profiles\ucie-private-c40.yaml"
        ).is_file():
            self.skipTest("Owner UCIE host not present; no non-UCIE probing")
        shell = shutil.which("powershell.exe")
        if not shell:
            self.skipTest("Windows PowerShell not found")
        p = subprocess.run(
            [shell, "-NoProfile", "-NonInteractive", "-File", str(SCRIPT),
             "-Mode", "Status"],
            capture_output=True, text=True, timeout=25, check=False)
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        import json
        obj = json.loads(p.stdout)
        self.assertEqual(obj["status"], "UCIE_C40_RECOVERY_STATUS_READONLY")
        self.assertIs(obj["db_changed"], False)
        self.assertGreaterEqual(obj["c40_client_count"], 0)


if __name__ == "__main__":
    unittest.main()
