"""UCIE-only Windows migration read-only task/MCP preflight safety contracts.

Windows CI executes ONLY -ContractOnly. It never invokes real ScheduledTasks,
does not inspect D: or query existing user plugins, and cannot migrate anything.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import unittest


REPO = Path(__file__).resolve().parents[1]
SCRIPT = REPO / "scripts" / "ucie_owner_cutover_bindings_readonly_v01.ps1"


class UCIEOwnerCutoverBindingReadonlyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = SCRIPT.read_text("utf-8")

    def test_01_exact_ucie_checkout_guard_is_mandatory(self):
        self.assertIn("$oldRoot = 'D:\\UCIE'", self.text)
        self.assertIn("Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')", self.text)
        self.assertIn("UCIE_ORIGINAL_ROOT_PATH_MISMATCH_NO_GO", self.text)
        self.assertIn("ReparsePoint", self.text)

    def test_02_future_parent_is_target_only_never_auto_created(self):
        self.assertIn("$newRoot = 'D:\\UCIE_PROJECT\\UCIE'", self.text)
        self.assertIn("'proposed_ucie_parent'", self.text)
        self.assertIn("safe_to_move_or_delete = $false", self.text)
        self.assertIn("owner_files_moved = $false", self.text)
        self.assertIn("owner_files_deleted = $false", self.text)

    def test_03_four_specific_first_party_task_names_only(self):
        task_section = self.text.split("$knownTasks = @(", 1)[1].split(")", 1)[0]
        names = re.findall(r"'(UCIE-[^']+)'", task_section)
        self.assertEqual(names, [
            "UCIE-PublicMiner-Hourly",
            "UCIE-Internal-Minute",
            "UCIE-C40-Recover",
            "UCIE-LocalV1-Web",
        ])
        self.assertIn("all_ucie_tasks_enumerated = $false", self.text)
        self.assertIn("Get-ScheduledTask -TaskPath '\\' -TaskName $name", self.text)

    def test_04_mcp_tunnel_health_explicitly_unverified(self):
        for token in (
            "mcp_live_tunnel_binding_verified = $false",
            "mcp_client_process_count_verified = $false",
            "owner_profile_and_acl_migration_verified = $false",
            "original_operating_db_backup_verified = $false",
            "owner_approved_live_migration = $false",
        ):
            with self.subTest(flag=token):
                self.assertIn(token, self.text)

    def test_05_no_powershell_mutations_or_network_calls(self):
        forbidden = [
            "New-Item", "Copy-Item", "Move-Item", "Rename-Item",
            "Remove-Item", "Set-Item", "Start-ScheduledTask",
            "Stop-ScheduledTask", "Register-ScheduledTask",
            "Unregister-ScheduledTask", "Disable-ScheduledTask",
            "Enable-ScheduledTask", "Set-ScheduledTask",
            "Restart-Service", "Start-Service", "Stop-Service",
            "Invoke-RestMethod", "Invoke-WebRequest", "Invoke-Expression",
            "Get-ChildItem", "Get-CimInstance", "Start-Process",
            "Set-Content", "Out-File", "Add-Content",
        ]
        for verb in forbidden:
            with self.subTest(verb=verb):
                self.assertNotRegex(self.text, r"(?im)^\s*&?\s*" + re.escape(verb) + r"\b")
        self.assertNotIn("git clean", self.text)
        self.assertNotIn("git reset", self.text)
        self.assertNotIn("git gc", self.text)

    def test_06_no_secret_profiles_or_databases_read(self):
        self.assertIn("private_profile_contents_read = $false", self.text)
        self.assertIn("operating_database_opened_or_modified = $false", self.text)
        self.assertIn("Get-Item -LiteralPath $entry.Path", self.text)
        self.assertNotRegex(self.text, r"(?i)(Get-Content|Import-Clixml|ConvertFrom-Yaml|SqliteConnection|ReadAllText)")
        self.assertIn("network_requests = 0", self.text)

    def test_07_paths_are_ucie_only_no_drive_root_enumeration(self):
        all_roots = re.findall(r"D:\\[A-Za-z_]+", self.text)
        self.assertGreater(len(all_roots), 8)
        self.assertTrue(all(r.casefold() in (
            "d:\\ucie", "d:\\ucie_data", "d:\\ucie_preview",
            "d:\\ucie_project") for r in all_roots))
        self.assertNotIn("Get-PSDrive", self.text)
        self.assertIn("source_root = $oldRoot", self.text)

    def test_08_task_query_never_reports_private_executable_arguments(self):
        self.assertIn("action_count = $actions", self.text)
        self.assertIn("action_arguments_reference_old_root = $oldArguments", self.text)
        self.assertNotIn("action_arguments = $arguments", self.text)
        self.assertNotIn("task_user_id =", self.text)
        self.assertNotIn("principal_user =", self.text)

    def test_09_contract_only_exits_before_owner_query(self):
        part = self.text.split("if ($ContractOnly) {", 1)
        self.assertEqual(len(part), 2)
        before_guard, after_guard = part
        early = after_guard.split("\n}", 1)[0]
        self.assertIn("task_binding_checks_executed = $false", early)
        self.assertIn("return", early)
        self.assertNotIn("Get-ScheduledTask", before_guard)
        self.assertNotIn("Get-Item", before_guard)

    def test_10_actual_existing_schedulers_not_changed_by_new_file(self):
        baseline = (REPO / "scripts" / "install_hourly_task.ps1").read_text("utf-8")
        local = (REPO / "scripts" / "status_ucie_local_v1_autostart.ps1").read_text("utf-8")
        self.assertIn("Register-ScheduledTask", baseline)
        self.assertIn("'D:\\UCIE'", baseline)
        self.assertIn("'UCIE-LocalV1-Web'", local)
        self.assertIn("Get-ScheduledTask", local)
        self.assertNotIn("Register-ScheduledTask", self.text)

    @unittest.skipUnless(os.name == "nt", "native Windows PowerShell acceptance only")
    def test_11_windows_contract_only_does_not_query_live_tasks(self):
        powershell = shutil.which("powershell.exe")
        if not powershell:
            self.skipTest("powershell.exe unavailable on Windows runner")
        p = subprocess.run(
            [powershell, "-NoProfile", "-NonInteractive",
             "-File", str(SCRIPT), "-ContractOnly"],
            cwd=REPO, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=25,
        )
        self.assertEqual(
            p.returncode, 0, p.stderr.decode("utf-8", errors="replace")[-600:])
        report = json.loads(p.stdout.decode("utf-8-sig"))
        self.assertEqual(report["schema"], "UCIE_OWNER_CUTOVER_BINDINGS_READONLY_V01")
        self.assertEqual(
            report["status"], "UCIE_READONLY_SCRIPT_CONTRACT_ONLY_NOT_HOST_TESTED")
        self.assertTrue(report["contract_only"])
        self.assertFalse(report["task_binding_checks_executed"])
        self.assertFalse(report["safe_to_move_or_delete"])
        self.assertFalse(report["mcp_live_tunnel_binding_verified"])
        self.assertEqual(report["task_bindings"], [])
        self.assertEqual(report["exact_paths_checked"], [])
        self.assertEqual(report["network_requests"], 0)

    @unittest.skipUnless(os.name == "nt", "native Windows PowerShell acceptance only")
    def test_12_windows_script_parses_without_executing_host_queries(self):
        powershell = shutil.which("powershell.exe")
        if not powershell:
            self.skipTest("powershell.exe unavailable on Windows runner")
        command = (
            "$t=$null;$e=$null;"
            "[System.Management.Automation.Language.Parser]::ParseFile("
            f"'{str(SCRIPT).replace(chr(39), chr(39)+chr(39))}',"
            "[ref]$t,[ref]$e)|Out-Null;"
            "if($e.Count -gt 0){exit 2};exit 0"
        )
        p = subprocess.run(
            [powershell, "-NoProfile", "-NonInteractive", "-Command", command],
            cwd=REPO, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=25,
        )
        self.assertEqual(
            p.returncode, 0,
            p.stderr.decode("utf-8", errors="replace")[-650:])


if __name__ == "__main__":
    unittest.main()
