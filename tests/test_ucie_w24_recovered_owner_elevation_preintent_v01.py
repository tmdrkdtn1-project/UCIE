"""W24 owner recovery history isolation and UAC pre-intent guard contracts.

No tests exercise owner Task Scheduler mutation, DB handoff, tunnel, live HTTP,
or protected Windows journal creation. Source contract and native PowerShell
no-host/negative-approval tests only; real owner host still unverified.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "ucie_owner_w22_quiesce_resume_local_v01.ps1"


class W24RecoveredRetryOwnerElevatedContract(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.src = SCRIPT.read_text(encoding="utf-8")

    def test_elevated_admin_gate_precedes_every_private_intent_and_mutation(self):
        text = self.src
        permit = text.index("UCIE_W22_EXPLICIT_OWNER_APPROVAL_REQUIRED")
        uac = text.index("UCIE_W24_ELEVATED_TOKEN_REQUIRED_BEFORE_INTENT_NO_TASK_CHANGE")
        archive = text.index("Get-Acl -LiteralPath $archive")
        tasks = text.index("Import-Module ScheduledTasks -ErrorAction Stop")
        intent = text.index("SavePrivate $intent (")
        disable = text.index("Disable-ScheduledTask -TaskPath '\\' -TaskName $names[$i]")
        stop = text.index("Stop-ScheduledTask -TaskPath '\\' -TaskName $names[2]")
        stage = text.index("& $w21 -ApplyLocal -OwnerApproval $w21Apply")
        self.assertLess(permit, uac)
        self.assertLess(uac, archive)
        self.assertLess(uac, tasks)
        self.assertLess(uac, intent)
        self.assertLess(intent, disable)
        self.assertLess(disable, stop)
        self.assertLess(stop, stage)
        self.assertIn("WindowsBuiltInRole]::Administrator", text)
        self.assertIn("$script:ownerSid=$caller.User.Value", text)
        self.assertIn("UCIE_W22_PRIVATE_OWNER_ACL_REQUIRED", text)
        self.assertIn("UCIE_W22_TASK_OWNER_MISMATCH", text)

    def test_previous_w22_receipts_immutable_and_current_attempt_distinct(self):
        text = self.src
        old_intent = "UCIE_W22_OWNER_MAINTENANCE_INTENT_V01.json"
        old_restore = "UCIE_W22_ORIGINAL_AVAILABILITY_RESTORED_V01.json"
        new_intent = "UCIE_W24_OWNER_RECOVERED_RETRY_INTENT_V01.json"
        new_restore = "UCIE_W24_OWNER_RECOVERED_RETRY_RESTORED_V01.json"
        for path in (old_intent, old_restore, new_intent, new_restore):
            self.assertIn(path, text)
        self.assertIn("UCIE_W24_OWNER_RECOVERED_RETRY_V01", text)
        self.assertIn("if ($RecoveredAttempt) {", text)
        self.assertIn("RequireRecoveredW22History", text)
        self.assertIn("Direct $priorW22Intent $false", text)
        self.assertIn("Direct $priorW22Restore $false", text)
        self.assertIn("$before.owner_sid_sha256 -ne (ShaText $script:ownerSid)", text)
        self.assertIn("$before.c40_action_sha256 -ne $baseline", text)
        self.assertIn("$after.original_writer_schedules_enabled -ne 2", text)
        self.assertIn("$after.original_sqlite_restored_or_overwritten -ne $false", text)
        self.assertIn("UCIE_W24_PRIOR_W22_RECOVERY_NOT_PROVEN_NO_RETRY", text)
        self.assertIn("UCIE_W24_PRIOR_W22_ORIGINAL_STATES_MISMATCH", text)
        self.assertIn("Absent $intent", text)
        self.assertIn("Absent $resumeReceipt", text)
        self.assertIn("$record.status -ne $intentStatus", text)
        self.assertIn("schema=$schema;status=$resumeStatus", text)
        self.assertNotIn("Remove-Item -LiteralPath $priorW22Intent", text)
        self.assertNotIn("Remove-Item -LiteralPath $priorW22Restore", text)
        self.assertNotIn("Move-Item -LiteralPath $priorW22Intent", text)
        self.assertNotIn("Move-Item -LiteralPath $priorW22Restore", text)
        self.assertNotIn("Stop-Process", text)
        self.assertNotIn("taskkill", text)
        self.assertNotIn("Set-ScheduledTask", text)
        self.assertNotIn("Unregister-ScheduledTask", text)

    def test_retry_is_fail_closed_after_prior_full_recovery_and_new_journal_only(self):
        code = self.src
        prior = code.index("RequireRecoveredW22History\n}")
        apply = code.index("if($ApplyLocal) {")
        w23 = code.index("& $python -I -B $w23Lineage --check-owner --owner-approval $w23Approval")
        write = code.index("SavePrivate $intent (")
        disable = code.index("Disable-ScheduledTask -TaskPath '\\' -TaskName $names[$i]")
        self.assertLess(prior, apply)
        self.assertLess(apply, w23)
        self.assertLess(w23, write)
        self.assertLess(write, disable)
        self.assertIn("UCIE_W24_OWNER_RECOVERED_RETRY_LOCAL_ONLY", code)
        self.assertIn("UCIE_W24_OWNER_RECOVERED_RETRY_RESUME_OLD", code)
        self.assertIn("UCIE_W24_ORIGINAL_TASK_SCHEDULES_RESTORED", code)
        self.assertIn("UCIE_W24_LOCAL_ONLY_PILOT_STAGED__WRITERS_C40_HOLD", code)
        self.assertIn("UCIE_W22_LISTENER_NOT_RELEASED_BY_OLD_TASK_EXPLICIT_RESUME", code)

    def test_native_powershell_no_host_contract_and_no_approval_denials(self):
        exe = "powershell.exe" if os.name == "nt" else shutil.which("pwsh")
        if not exe:
            self.skipTest("Native PowerShell unavailable")
        safe = str(SCRIPT).replace("'", "''")
        parser = (
            "$tokens=$null;$errors=$null;"
            f"[Management.Automation.Language.Parser]::ParseFile('{safe}',"
            "[ref]$tokens,[ref]$errors)|Out-Null;"
            "if(@($errors).Count -gt 0){$errors|ForEach-Object{$_.Message};exit 2};exit 0"
        )
        syntax = subprocess.run([exe, "-NoProfile", "-NonInteractive",
                                 "-Command", parser], capture_output=True,
                                text=True, timeout=30)
        self.assertEqual(syntax.returncode, 0, syntax.stdout + syntax.stderr)

        base = [exe, "-NoProfile", "-NonInteractive"]
        if os.name == "nt":
            base.extend(["-ExecutionPolicy", "Bypass"])
        base.extend(["-File", str(SCRIPT), "-RecoveredAttempt"])
        contract = subprocess.run(base, capture_output=True, text=True, timeout=30)
        self.assertEqual(contract.returncode, 0, contract.stdout + contract.stderr)
        data = json.loads(contract.stdout)
        self.assertEqual(data["schema"], "UCIE_W24_OWNER_RECOVERED_RETRY_V01")
        self.assertEqual(data["status"], "UCIE_W22_CONTRACT_ONLY_NO_HOST_ACCESS")
        self.assertFalse(data["owner_tasks_queried"])
        self.assertFalse(data["intent_written"])
        for flag in ("-ApplyLocal", "-ResumeOld"):
            with self.subTest(flag=flag):
                denied = subprocess.run(base + [flag],
                                        capture_output=True, text=True,
                                        timeout=30)
                self.assertNotEqual(denied.returncode, 0)
                self.assertIn("UCIE_W22_EXPLICIT_OWNER_APPROVAL_REQUIRED",
                              denied.stdout + denied.stderr)


if __name__ == "__main__":
    unittest.main()
