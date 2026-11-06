"""Offline contracts for UCIE-only read-only Windows host inspector.

Static assertions only. The inspector is syntax-parsed, never executed, by
the Windows GitHub Actions matrix. Owner's actual Windows host remains
untouched until one-time approval.
"""
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "ucie_unattended_host_readonly_preflight.ps1"
WORKFLOW = ROOT / ".github" / "workflows" / "stage1-offline-tests.yml"


class UCIEHostInspectorContracts(unittest.TestCase):
    def test_only_exact_ucie_host_paths_and_named_tasks(self):
        text = SCRIPT.read_text(encoding="utf-8")
        for expected in (
            r"D:\UCIE", r"D:\UCIE_DATA\mcp_tunnel_profiles\ucie-private-c40.yaml",
            r"D:\UCIE_DATA\tools\tunnel-client-v0.0.16\tunnel-client.exe",
            "UCIE-PublicMiner-Hourly", "UCIE-C40-Supervisor",
            "tmdrkdtn1-project/UCIE.git",
        ):
            with self.subTest(expected=expected):
                self.assertIn(expected, text)
        self.assertIn("READONLY_OBSERVATION_HOST_ACTIVATION_NOT_AUTHORIZED", text)
        self.assertIn("external_anchor_verified", text.replace("monotonic_external_anchor_verified", "external_anchor_verified"))

    def test_no_service_mutation_or_untrusted_execution(self):
        text = SCRIPT.read_text(encoding="utf-8")
        # Reject executable operations outside strictly scoped read-only calls.
        for forbidden in (
            "Register-ScheduledTask", "Unregister-ScheduledTask",
            "Start-ScheduledTask", "Stop-ScheduledTask", "Start-Service",
            "Stop-Service", "Restart-Service", "Start-Process",
            "Stop-Process", "Invoke-Expression", "Invoke-RestMethod",
            "Invoke-WebRequest", "Set-Content", "Out-File", "Remove-Item",
            "New-Item", "icacls ", "schtasks ", "git push", "git reset",
            "git checkout", "git pull", "git fetch",
        ):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, text)
        self.assertIn("Get-Acl -LiteralPath $journalDir", text)
        self.assertIn("[System.Security.AccessControl.FileSystemRights]::DeleteSubdirectoriesAndFiles", text)
        self.assertNotIn("[System.Security.AccessControl.FileSystemRights]::Modify -bor", text)
        self.assertIn(".ucie_bridge_state", text)
        self.assertIn("ucie_journal_acl_inheritance_disabled", text)
        self.assertIn("ucie_journal_broad_write_ace_denied", text)
        self.assertIn("owner_acl_independently_verified = $false", text)
        self.assertIn("Get-ScheduledTask", text)
        self.assertIn("git -C $repo status --porcelain", text)
        self.assertNotIn("Get-ChildItem -Recurse", text)
        self.assertNotIn("Get-CimInstance", text)

    def test_ci_windows_parser_includes_new_script(self):
        script = "scripts/ucie_unattended_host_readonly_preflight.ps1"
        workflow = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn(script, workflow)
        self.assertIn("System.Management.Automation.Language.Parser", workflow)
        self.assertIn("runner.os == 'Windows'", workflow)


if __name__ == "__main__":
    unittest.main()
