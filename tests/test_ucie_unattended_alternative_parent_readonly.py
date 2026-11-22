"""UCIE owner LocalAppData alternative preflight is source-only and read-only."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "ucie_unattended_alternative_owner_parent_readonly_v1.ps1"
CI = ROOT / ".github" / "workflows" / "stage1-offline-tests.yml"


class UCIEAlternativeParentReadOnlyTests(unittest.TestCase):
    def test_only_current_owner_known_folder_and_ucie_leaf(self):
        s = SCRIPT.read_text(encoding="utf-8")
        for fragment in (
            "[Environment+SpecialFolder]::LocalApplicationData",
            "UCIE_Unattended_State",
            "CURRENT_OWNER_LOCALAPPDATA_UCIE_UNATTENDED_STATE",
            "UCIE_LOCALAPPDATA_PARENT_CANDIDATE_REVIEW_ONLY",
            "UCIE_LOCALAPPDATA_PARENT_UNTRUSTED_NO_INSTALL",
            "Get-Acl -LiteralPath $localParent",
            "parent_foreign_delete_child_allow_ace",
            "parent_broad_modifying_allow_ace",
            "parent_unresolved_allow_ace_identity",
            "candidate_host_independently_attested = $false",
            "candidate_install_approved = $false",
        ):
            with self.subTest(fragment=fragment):
                self.assertIn(fragment, s)
        self.assertNotIn("Get-ChildItem", s)
        self.assertNotIn("Get-Content", s)
        self.assertNotIn("user_sid =", s)
        self.assertNotIn("parent_path =", s)
        self.assertNotIn("owner_account =", s)

    def test_no_os_mutation_or_secret_calls(self):
        s = SCRIPT.read_text(encoding="utf-8")
        for fragment in (
            "new_directory_created = $false",
            "existing_acl_changed = $false",
            "scheduled_task_modified = $false",
            "github_token_read = $false",
            "git_pushed = $false",
            "rule_auto_promoted = $false",
        ):
            self.assertIn(fragment, s)
        for forbidden in (
            "Register-ScheduledTask", "Set-ScheduledTask",
            "Unregister-ScheduledTask", "Start-ScheduledTask",
            "Stop-ScheduledTask", "Restart-Service", "Start-Service",
            "Stop-Service", "Start-Process", "Stop-Process",
            "Remove-Item", "New-Item", "Set-Content",
            "Set-Acl", "icacls ", "takeown ", "Invoke-Expression",
            "Invoke-RestMethod", "Invoke-WebRequest", "git push",
            "Get-Credential", "ConvertTo-SecureString",
            "Export-Clixml", "Get-ChildItem -Recurse",
        ):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, s)

    def test_modify_bits_do_not_include_fullcontrol_lookup(self):
        s = SCRIPT.read_text(encoding="utf-8")
        self.assertIn("FileSystemRights]::Write -bor", s)
        self.assertIn("FileSystemRights]::DeleteSubdirectoriesAndFiles -bor", s)
        self.assertIn("FileSystemRights]::TakeOwnership", s)
        self.assertNotIn("FileSystemRights]::FullControl -bor", s)
        self.assertNotIn("FileSystemRights]::Modify -bor", s)

    def test_windows_ci_parses_but_does_not_execute(self):
        workflow = CI.read_text(encoding="utf-8")
        self.assertIn("scripts/ucie_unattended_alternative_owner_parent_readonly_v1.ps1", workflow)
        self.assertIn("System.Management.Automation.Language.Parser", workflow)
        self.assertIn("runner.os == 'Windows'", workflow)


if __name__ == "__main__":
    unittest.main()
