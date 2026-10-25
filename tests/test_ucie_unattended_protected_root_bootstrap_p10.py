"""UCIE P10 one-directory owner bootstrap source contract. Never runs the installer."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "ucie_unattended_protected_root_bootstrap_p10.ps1"


class ProtectedRootBootstrapContract(unittest.TestCase):
    def test_disarmed_and_single_known_folder(self):
        text = SCRIPT.read_text(encoding="utf-8")
        self.assertIn("[Environment+SpecialFolder]::ProgramFiles", text)
        self.assertIn("UCIE_UnattendedHost", text)
        self.assertIn("[switch]$Apply", text)
        self.assertIn("APPROVE_UCIE_PROGRAMFILES_ROOT_ONE_DIRECTORY_ONLY", text)
        self.assertIn("UCIE_P10_PARENT_OR_ACL_REVIEW_NO_GO", text)
        self.assertIn("UCIE_P10_TARGET_ALREADY_EXISTS_NO_OVERWRITE", text)

    def test_acl_creation_and_no_activation(self):
        text = SCRIPT.read_text(encoding="utf-8")
        self.assertIn("SetAccessRuleProtection($true, $false)", text)
        self.assertIn("Test-UcieExactNewDacl $target", text)
        self.assertIn("external_antireplay_anchor_provisioned = $false", text)
        self.assertIn("scheduled_task_registered = $false", text)
        self.assertIn("unattended_worker_activated = $false", text)
        self.assertIn("rule_auto_promotion_enabled = $false", text)

    def test_windows_ci_ast_only(self):
        workflow = (ROOT / ".github" / "workflows" / "stage1-offline-tests.yml").read_text(encoding="utf-8")
        self.assertIn("ucie_unattended_protected_root_bootstrap_p10.ps1", workflow)
        self.assertIn("System.Management.Automation.Language.Parser", workflow)


if __name__ == "__main__":
    unittest.main()
