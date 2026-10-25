"""UCIE P5 host bootstrap source assertions; never create Windows folder in CI."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
BOOTSTRAP = ROOT / "scripts" / "ucie_unattended_owner_journal_bootstrap.ps1"
WORKFLOW = ROOT / ".github" / "workflows" / "stage1-offline-tests.yml"


class UCIEOwnerJournalBootstrapTests(unittest.TestCase):
    def test_exact_ucie_separate_path_and_no_touch_existing_bridge(self):
        src = BOOTSTRAP.read_text(encoding="utf-8")
        self.assertIn(r"D:\UCIE_DATA\ucie_unattended_state", src)
        self.assertIn(r"D:\UCIE_DATA", src)
        self.assertIn("APPROVE_UCIE_NEW_OPERATIONS_DIRECTORY_ONLY", src)
        self.assertIn("UCIE_OWNER_OPERATIONS_DIRECTORY_INSPECTION_ONLY", src)
        self.assertIn("UCIE_PARENT_OWNER_OR_ACL_UNSAFE_NO_INSTALL", src)
        self.assertIn("UCIE_OPERATIONS_DIRECTORY_ALREADY_EXISTS_NO_OVERWRITE", src)
        self.assertIn("UCIE_OPERATIONS_DIRECTORY_CREATED_BUT_ACL_NOT_VERIFIED_HOLD", src)
        self.assertIn("existing_bridge_state_modified = $false", src)
        self.assertIn("external_antirollback_anchor_configured = $false", src)
        self.assertIn("unattended_automation_activated = $false", src)
        self.assertNotIn("D:\\UCIE\\.ucie_bridge_state'", src)

    def test_dacl_is_applied_during_creation_not_after(self):
        src = BOOTSTRAP.read_text(encoding="utf-8")
        self.assertIn("[switch]$Apply", src)
        self.assertIn("if ($Apply -and $Approval -cne $approvalPhrase)", src)
        self.assertIn("SetAccessRuleProtection($true, $false)", src)
        self.assertIn("[IO.Directory]::CreateDirectory($target, $security)", src)
        self.assertIn("[IO.FileSystemAclExtensions]::CreateDirectory($security, $target)", src)
        self.assertIn("S-1-5-18", src)
        self.assertIn("$targetOwner -eq $currentSid", src)
        self.assertIn("trustedSids", src)
        self.assertIn("target_acl_exact_owner_and_system_only", src)
        for forbidden in (
            "Set-Acl ", "icacls ", "takeown ", "Remove-Item ",
            "Register-ScheduledTask", "New-ScheduledTask",
            "Stop-Process", "Start-Process", "Restart-Service",
            "Stop-Service", "Start-Service", "git push",
            "Invoke-RestMethod", "Invoke-WebRequest",
            "Get-Credential", "ConvertTo-SecureString",
            "Export-Clixml", "Start-ScheduledTask",
        ):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, src)

    def test_windows_ci_only_parses_install_script(self):
        workflow = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("scripts/ucie_unattended_owner_journal_bootstrap.ps1", workflow)
        self.assertIn("System.Management.Automation.Language.Parser", workflow)
        self.assertIn("runner.os == 'Windows'", workflow)


if __name__ == "__main__":
    unittest.main()
