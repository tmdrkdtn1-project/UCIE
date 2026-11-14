"""Static fail-closed contracts for UCIE-only console-free runtime changes.

This test does not launch a tunnel or change a scheduled task.
Windows PowerShell AST parsing happens in GitHub Actions separately.
"""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
LAUNCHER = ROOT / "scripts" / "ucie_owner_admin_mcp_launch.ps1"
MINER = ROOT / "scripts" / "install_hourly_task.ps1"
STATUS = ROOT / "scripts" / "task_status.ps1"


class UCIENoWindowSourceContracts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.launcher = LAUNCHER.read_text("utf-8")
        cls.miner = MINER.read_text("utf-8")
        cls.status = STATUS.read_text("utf-8")

    def test_tunnel_background_keeps_existing_c40_and_operator_gate(self):
        s = self.launcher
        for fragment in (
            "if ($Mode -eq 'Background')",
            "-WindowStyle Hidden -PassThru",
            "UCIE_OWNER_BACKGROUND_TUNNEL_PROCESS_OBSERVED",
            "UCIE_TUNNEL_ALREADY_RUNNING_DO_NOT_DUPLICATE",
            "UCIE_MCP_OWNER_APPROVAL",
            "UCIE_ADMIN_TOOLS_ENABLED",
            "UCIE_OWNER_ONLY_TUNNEL_RUN_STARTED",
            "survives_windows_logoff_or_reboot = $false",
        ):
            self.assertIn(fragment, s)
        self.assertNotIn("Register-ScheduledTask", s)
        self.assertNotIn("Stop-Process", s)

    def test_only_exact_original_ucie_miner_task_may_be_quieted(self):
        s = self.miner
        for fragment in (
            "$taskName = 'UCIE-PublicMiner-Hourly'",
            "D:\\UCIE_PREVIEW\\UCIE_ADMIN",
            "if ($QuietExisting -and [string]::Equals(",
            "[switch]$QuietExisting",
            "UCIE_SCHEDULE_ALREADY_EXISTS_REFUSE_OVERWRITE",
            "UCIE_HOURLY_TASK_PRINCIPAL_OR_POLICY_MISMATCH_NO_CHANGE",
            "UCIE_HOURLY_TASK_ACTION_NOT_EXACT_NO_CHANGE",
            "UCIE_HOURLY_TASK_CADENCE_MISMATCH_NO_CHANGE",
            "UCIE_HOURLY_TASK_ACTIVE_NO_CHANGE_RETRY_AFTER_CYCLE",
            "UCIE_HOURLY_TASK_WINDOWLESS_ACTION_UPDATED",
            "$quietAction = New-ScheduledTaskAction -Execute $pythonw",
        ):
            self.assertIn(fragment, s)
        self.assertEqual(s.count("Set-ScheduledTask -TaskPath $taskPath -TaskName $taskName"), 1)
        for forbidden in (
            "Unregister-ScheduledTask", "Stop-Process", "Get-ScheduledTask -TaskName '*'",
            "Stop-ScheduledTask", "Restart-Service", "Invoke-Expression",
        ):
            self.assertNotIn(forbidden, s)

    def test_readonly_miner_status_recognizes_pythonw_and_legacy(self):
        s = self.status
        self.assertIn("task_uses_pythonw_without_main_console = $windowlessAction", s)
        self.assertIn("$knownLegacyAction", s)
        self.assertIn("$expectedPythonw", s)
        self.assertIn("scheduler_changed = $false", s)


if __name__ == "__main__":
    unittest.main()
