"""Offline static safety tests for UCIE-only read-only identity/ACL diagnostic."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
PATH = ROOT / "scripts" / "ucie_unattended_identity_acl_readonly_v2.ps1"
CI = ROOT / ".github" / "workflows" / "stage1-offline-tests.yml"


class ReadonlyIdentityDiagnosticV2Tests(unittest.TestCase):
    def test_scope_is_fixed_ucie_only_and_bridge_is_not_ops_journal(self):
        text = PATH.read_text(encoding="utf-8")
        for name in (
            "D:\\UCIE", "D:\\UCIE\\.ucie_bridge_state",
            "D:\\UCIE_DATA\\ucie_unattended_state",
            "UCIE-PublicMiner-Hourly", "UCIE-C40-Supervisor",
            "Translate(", "SecurityIdentifier", "Get-Acl -LiteralPath",
            "existing_bridge_directory",
            "proposed_independent_operations_directory",
            "miner_task_sid_matches_current_user",
            "operator_install_authorized = $false",
        ):
            with self.subTest(name=name):
                self.assertIn(name, text)
        self.assertIn("DIAGNOSTIC_OBSERVATION_ONLY_NOT_HOST_APPROVAL", text)
        self.assertNotIn("Get-ChildItem -Recurse", text)
        self.assertNotIn("D:\\OFFICE", text)

    def test_never_modifies_schedule_acl_service_or_git(self):
        text = PATH.read_text(encoding="utf-8")
        for forbidden in (
            "Register-ScheduledTask", "Set-ScheduledTask",
            "Unregister-ScheduledTask", "Start-ScheduledTask",
            "Stop-ScheduledTask", "Restart-Service", "Stop-Service",
            "Start-Service", "Start-Process", "Stop-Process",
            "Set-Acl", "icacls ", "takeown ",
            "Remove-Item", "New-Item", "Set-Content", "Out-File",
            "Invoke-Expression", "Invoke-WebRequest", "Invoke-RestMethod",
            "git push", "git reset", "git pull", "git fetch",
            "ConvertTo-SecureString", "Export-Clixml", "Get-Credential",
        ):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, text)
        for value in (
            "windows_acl_modified = $false",
            "scheduled_task_modified = $false",
            "github_push_performed = $false",
            "production_rule_promoted = $false",
        ):
            self.assertIn(value, text)

    def test_ci_parses_ps1_on_windows_without_execution(self):
        workflow = CI.read_text(encoding="utf-8")
        self.assertIn("scripts/ucie_unattended_identity_acl_readonly_v2.ps1", workflow)
        self.assertIn("System.Management.Automation.Language.Parser", workflow)
        self.assertIn("runner.os == 'Windows'", workflow)


if __name__ == "__main__":
    unittest.main()
