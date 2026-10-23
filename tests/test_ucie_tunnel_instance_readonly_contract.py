"""UCIE tunnel-instance diagnostic: source-only safety contract.

CI parses the real .ps1 with Windows PowerShell 5.1 separately.
This test must never execute local tunnel clients or inspect host processes.
"""
from pathlib import Path
import unittest

SCRIPT = (Path(__file__).resolve().parents[1]
          / "scripts" / "inspect_ucie_tunnel_runtime_instances.ps1")


class UCIEInstanceReadOnlySourceContract(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.script = SCRIPT.read_text(encoding="utf-8")

    def test_ucie_only_process_and_profile_scope(self):
        script = self.script
        self.assertIn("D:\\UCIE_DATA\\tools\\tunnel-client-v0.0.16\\tunnel-client.exe", script)
        self.assertIn("D:\\UCIE_DATA\\.venv_mcp\\Scripts\\python.exe", script)
        self.assertIn("D:\\UCIE_DATA\\mcp_tunnel_profiles\\ucie-private-c40.yaml", script)
        self.assertIn("ExecutablePath LIKE '%UCIE_DATA%'", script)
        self.assertIn("StartsWith(", script)

    def test_does_not_change_or_disclose_runtime(self):
        script = self.script
        for forbidden in ("Stop-Process", "Start-Process", "Restart-Service",
                          "Stop-Service", "Start-Service", "Set-ScheduledTask",
                          "Set-Content", "Out-File", "Remove-Item",
                          "Invoke-Expression", "Set-ItemProperty"):
            self.assertNotIn(forbidden, script)
        self.assertNotIn("Write-Host $cmd", script)
        self.assertNotIn("Write-Output $cmd", script)
        self.assertIn("command_lines_or_tunnel_ids_printed = $false", script)
        self.assertIn("files_modified = $false", script)

    def test_unknown_is_not_reported_as_single_instance_pass(self):
        script = self.script
        self.assertIn("UCIE_INSTANCE_OBSERVATION_INCOMPLETE", script)
        self.assertIn("local_ucie_tunnel_client_count = $clients.Count", script)
        self.assertIn("possible_local_duplicate = ($clients.Count -gt 1)", script)
        self.assertIn("other_hosts_or_platform_instances_visible = $false", script)


if __name__ == "__main__":
    unittest.main()
