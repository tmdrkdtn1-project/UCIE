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

    def test_exact_one_script_body_approval_here_string_and_finally(self):
        source = self.source
        # Guard against previous accidental JS replacement expansion of
        # dollar-apostrophe in regex, which duplicated a suffix into the
        # middle of the PowerShell script and invalidated all following code.
        self.assertEqual(
            source.count("Read-Host 'UCIE one-session authorization: type APPROVE'"), 1)
        self.assertEqual(source.count("$probe = @'"), 1)
        self.assertEqual(source.count("'@"), 1)
        # Initial process census plus just-in-time prelaunch duplicate guard.
        self.assertEqual(source.count("UCIE_TUNNEL_ALREADY_RUNNING_DO_NOT_DUPLICATE"), 2)
        self.assertEqual(source.count("\nfinally {"), 1)
        self.assertLess(len(source.splitlines()), 315)
        self.assertEqual(source.rstrip().splitlines()[-1], "}")

    def test_pr77_library_package_precedes_admin_source(self):
        source = self.source
        self.assertIn(
            "$env:PYTHONPATH = @($librarySource, $adminSource, $libraryApp) -join ';'",
            source)
        self.assertNotIn(
            "$env:PYTHONPATH = @($adminSource, $librarySource, $libraryApp) -join ';'",
            source)
        self.assertIn("ucie_miner\\public_library_mcp_adapter.py", source)
        self.assertIn("ucie_admin\\mcp_registration.py", source)
        self.assertIn("VERIFY_LIBRARY_ADAPTER_ORIGIN", source)
        self.assertIn("UCIE_LIBRARY_ADAPTER_SHADOWED", source)

    def test_local_probe_invokes_legacy_search_before_launch(self):
        source = self.source
        self.assertIn('server.call_tool("search_ucie_evidence"', source)
        self.assertIn("CALL_EXISTING_PUBLIC_SEARCH", source)
        self.assertIn('"legacy_search_call_verified":True', source)
        self.assertIn("UCIE_LEGACY_PUBLIC_SEARCH_CONTRACT_NOT_MET", source)
        self.assertLess(
            source.index('server.call_tool("search_ucie_evidence"'),
            source.index('& $clientExe run --profile-file $profile'))
        self.assertIn('"live_chatgpt_tools_verified":False', source)

    def test_inline_probe_python_grammar(self):
        source = self.source
        self.assertEqual(source.count("$probe = @'"), 1)
        embedded = source.split("$probe = @'\n", 1)[1].split("\n'@", 1)[0]
        compile(embedded, "UCIE_owner_MCP_embedded_probe.py", "exec")

    def test_hidden_background_is_independent_and_remains_approval_gated(self):
        source = self.source
        self.assertIn("[ValidateSet('Probe', 'Launch', 'Background')]", source)
        self.assertIn("if ($Mode -eq 'Background') {", source)
        self.assertIn("Start-Process -FilePath $clientExe", source)
        self.assertIn("-WindowStyle Hidden -PassThru", source)
        self.assertIn("-WorkingDirectory (Get-Location).ProviderPath", source)
        self.assertIn("UCIE_OWNER_BACKGROUND_TUNNEL_PROCESS_OBSERVED", source)
        self.assertIn("UCIE_TUNNEL_ALREADY_RUNNING_DO_NOT_DUPLICATE", source)
        self.assertIn("survives_windows_logoff_or_reboot = $false", source)
        self.assertIn("startup_task_registered = $false", source)
        self.assertNotIn("Register-ScheduledTask", source)
        self.assertNotIn("Stop-Process", source)
        self.assertLess(
            source.index('server.call_tool("search_ucie_evidence"'),
            source.index("Start-Process -FilePath $clientExe"))
        self.assertIn("$env:UCIE_MCP_OWNER_APPROVAL = $oldApproval", source)

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
        self.assertIn("if ($Mode -in @('Launch', 'Background') -and -not $OwnerOnlyConfirmed)", source)
        self.assertIn("$env:UCIE_ADMIN_TOOLS_ENABLED = '1'", source)
        self.assertIn("if ($Mode -eq 'Launch') {", source)
        self.assertNotIn("Register-ScheduledTask", source)
        self.assertNotIn("Stop-Process", source)


if __name__ == "__main__":
    unittest.main()
