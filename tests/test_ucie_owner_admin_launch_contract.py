"""Source-only regression checks for the restored UCIE one-session operator contract.

Never executes PowerShell, tunnel-client, MCP host code, or admin tools.
"""
from pathlib import Path
import unittest


SCRIPT = (Path(__file__).resolve().parents[1]
          / "scripts" / "ucie_owner_admin_mcp_launch.ps1")


class UCIEOwnerMcpSessionContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = SCRIPT.read_text(encoding="utf-8")

    def test_existing_one_session_approval_not_unknown_password(self):
        source = self.source
        self.assertIn("Read-Host 'UCIE one-session authorization: type APPROVE'", source)
        self.assertIn("if ($ownerDecision -cne 'APPROVE')", source)
        self.assertIn("$expectedOwnerMarker = 'UCIE_PRIVATE_READONLY_APPROVED'", source)
        self.assertIn("$env:UCIE_MCP_OWNER_APPROVAL = $expectedOwnerMarker", source)
        self.assertNotIn("Read-Host -AsSecureString", source)
        self.assertNotIn("$secret", source)

    def test_existing_c40_client_flags_and_no_profile_alias(self):
        source = self.source
        self.assertIn("tunnel-client-v0.0.16\\tunnel-client.exe", source)
        self.assertIn("--profile-file $profile", source)
        self.assertIn("--control-plane.tunnel-id $tunnelId", source)
        self.assertIn("--health.url-file $healthFile", source)
        self.assertNotIn("run --profile $profile", source)

    def test_process_only_and_owner_only_access_gates(self):
        source = self.source
        self.assertIn("$env:UCIE_MCP_OWNER_APPROVAL = $oldApproval", source)
        self.assertIn("$env:UCIE_MCP_TUNNEL_ID = $oldTunnelId", source)
        self.assertIn("$env:UCIE_ADMIN_TOOLS_ENABLED = $oldAdminGate", source)
        self.assertIn("$env:PYTHONPATH = $oldPythonPath", source)
        self.assertIn("if ($Mode -eq 'Launch' -and -not $OwnerOnlyConfirmed)", source)
        self.assertIn("$env:UCIE_ADMIN_TOOLS_ENABLED = '1'", source)
        self.assertIn("if ($Mode -eq 'Launch') {", source)
        self.assertNotIn("Register-ScheduledTask", source)
        self.assertNotIn("Stop-Process", source)


if __name__ == "__main__":
    unittest.main()
