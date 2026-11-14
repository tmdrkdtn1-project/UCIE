"""UCIE owner-only LocalAppData ACL scope diagnostic: offline static safety tests."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "ucie_unattended_localappdata_ace_scope_readonly_v2.ps1"
CI = ROOT / ".github" / "workflows" / "stage1-offline-tests.yml"


class UCIELocalAppDataAceScopeTests(unittest.TestCase):
    def test_exact_owner_known_folder_and_bounded_nonidentifying_result(self):
        source = SCRIPT.read_text(encoding="utf-8")
        for expected in (
            "[Environment+SpecialFolder]::LocalApplicationData",
            "UCIE_Unattended_State",
            "UCIE_OWNER_LOCALAPPDATA_ACE_SCOPE_READONLY_V2",
            "CURRENT_OWNER_LOCALAPPDATA_UCIE_UNATTENDED_STATE",
            "PropagationFlags]::InheritOnly",
            "foreign_mutating_inherit_only_count",
            "foreign_mutating_effective_on_parent_count",
            "foreign_effective_parent_delete_child",
            "foreign_effective_parent_delete",
            "foreign_effective_parent_change_dacl_or_owner",
            "UCIE_FOREIGN_EFFECTIVE_DESTRUCTIVE_PARENT_RIGHTS_NO_GO",
            "UCIE_FOREIGN_ACE_INHERIT_ONLY_CHILD_DACL_REVIEW_REQUIRED",
            "UCIE_FOREIGN_NONDESTRUCTIVE_PARENT_RIGHTS_REVIEW_REQUIRED",
            "os_accesscheck_executed = $false",
        ):
            with self.subTest(expected=expected):
                self.assertIn(expected, source)
        for forbidden in (
            "Get-ChildItem", "Get-Content", "ReadAllText", "ReadAllBytes",
            "username =", "owner_sid =", "source_path =", "parent_path =",
            "user_profile =", "acl_entries =", "account_name =",
        ):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, source)

    def test_no_live_mutation_or_auto_permission(self):
        source = SCRIPT.read_text(encoding="utf-8")
        for no_side_effect in (
            "security_grant_authorized = $false",
            "new_directory_created = $false",
            "existing_acl_changed = $false",
            "service_restarted = $false",
            "git_pushed = $false",
            "automatic_rule_promotion = $false",
        ):
            self.assertIn(no_side_effect, source)
        for forbidden in (
            "Register-ScheduledTask", "Start-ScheduledTask",
            "Stop-ScheduledTask", "Set-ScheduledTask",
            "Unregister-ScheduledTask", "Restart-Service",
            "Start-Service", "Stop-Service", "Start-Process",
            "Stop-Process", "Remove-Item", "New-Item",
            "Set-Content", "Set-Acl", "icacls ", "takeown ",
            "Invoke-Expression", "Invoke-RestMethod", "Invoke-WebRequest",
            "git push", "Get-Credential", "Get-ChildItem -Recurse",
        ):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, source)

    def test_specific_mutating_rights_without_fullcontrol_lookup(self):
        source = SCRIPT.read_text(encoding="utf-8")
        for required in (
            "FileSystemRights]::Write -bor",
            "FileSystemRights]::Delete -bor",
            "FileSystemRights]::DeleteSubdirectoriesAndFiles -bor",
            "FileSystemRights]::ChangePermissions -bor",
            "FileSystemRights]::TakeOwnership",
        ):
            self.assertIn(required, source)
        self.assertNotIn("FileSystemRights]::FullControl -bor", source)
        self.assertNotIn("FileSystemRights]::Modify -bor", source)
        self.assertIn("foreign_effective_parent_create_child", source)

    def test_windows_workflow_ast_parse_only(self):
        workflow = CI.read_text(encoding="utf-8")
        self.assertIn("scripts/ucie_unattended_localappdata_ace_scope_readonly_v2.ps1", workflow)
        self.assertIn("System.Management.Automation.Language.Parser", workflow)
        self.assertIn("runner.os == 'Windows'", workflow)


if __name__ == "__main__":
    unittest.main()
