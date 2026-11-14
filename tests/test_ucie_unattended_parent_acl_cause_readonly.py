"""UCIE dedicated-parent ACL diagnostics: static offline/no-OS-effects QA."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "scripts" / "ucie_unattended_parent_acl_cause_readonly_v1.ps1"
CI = ROOT / ".github" / "workflows" / "stage1-offline-tests.yml"


class UCIEParentAclCauseReadonlyTests(unittest.TestCase):
    def test_fixed_ucie_parent_no_identity_or_ace_export(self):
        src = SOURCE.read_text(encoding="utf-8")
        self.assertIn("$parent = 'D:\\UCIE_DATA'", src)
        self.assertIn("$expectedTarget = 'D:\\UCIE_DATA\\ucie_unattended_state'", src)
        self.assertIn("READONLY_PARENT_CAUSE_OBSERVED_NOT_INSTALL_APPROVAL", src)
        for name in (
            "parent_owned_by_current_user",
            "parent_owned_by_builtin_administrators",
            "parent_owned_by_local_system",
            "parent_owned_by_other",
            "broad_account_mutating_allow_ace",
            "foreign_account_mutating_allow_ace",
            "unresolved_allow_ace_identity",
            "parent_and_ancestors_unlinked",
            "guarded_parent_criteria_met",
        ):
            with self.subTest(name=name):
                self.assertIn(name, src)
        self.assertNotIn("Get-ChildItem -Recurse", src)
        self.assertNotIn("owner_sid =", src)
        self.assertNotIn("raw_acl =", src)
        self.assertNotIn("acl_entries =", src)

    def test_readonly_cannot_claim_install_or_escalate(self):
        src = SOURCE.read_text(encoding="utf-8")
        for term in (
            "directory_created = $false",
            "existing_acl_changed = $false",
            "c40_restarted = $false",
            "github_push_performed = $false",
            "rule_promoted = $false",
            "owner_install_approved = $false",
            "host_security_attested = $false",
        ):
            self.assertIn(term, src)
        for forbidden in (
            "Register-ScheduledTask", "Set-ScheduledTask",
            "Start-ScheduledTask", "Stop-ScheduledTask",
            "Unregister-ScheduledTask", "Start-Process", "Stop-Process",
            "Restart-Service", "Start-Service", "Stop-Service",
            "Remove-Item", "New-Item", "Set-Content", "Set-Acl",
            "icacls ", "takeown ", "git push", "git checkout",
            "git reset", "Invoke-Expression", "Invoke-RestMethod",
            "Invoke-WebRequest", "Set-ExecutionPolicy",
            "Get-Credential", "ConvertTo-SecureString",
        ):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, src)

    def test_mutation_mask_excludes_read_rights(self):
        src = SOURCE.read_text(encoding="utf-8")
        self.assertIn("[Security.AccessControl.FileSystemRights]::Write -bor", src)
        self.assertIn("[Security.AccessControl.FileSystemRights]::Delete -bor", src)
        self.assertIn("[Security.AccessControl.FileSystemRights]::ChangePermissions -bor", src)
        self.assertNotIn("[Security.AccessControl.FileSystemRights]::FullControl -bor", src)
        self.assertNotIn("[Security.AccessControl.FileSystemRights]::Modify -bor", src)
        self.assertIn("if (($ace.FileSystemRights -band $writeMask) -eq 0)", src)
        self.assertIn("if ($ace.IsInherited)", src)

    def test_windows_ci_syntax_only(self):
        workflow = CI.read_text(encoding="utf-8")
        self.assertIn("scripts/ucie_unattended_parent_acl_cause_readonly_v1.ps1", workflow)
        self.assertIn("System.Management.Automation.Language.Parser", workflow)
        self.assertIn("runner.os == 'Windows'", workflow)


if __name__ == "__main__":
    unittest.main()
