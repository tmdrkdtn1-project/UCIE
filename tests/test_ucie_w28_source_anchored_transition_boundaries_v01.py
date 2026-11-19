"""Source-anchored W28 simulation contract against existing W19/W21/W22.

Only reads first-party repository code inside disposable CI checkout.
NEVER invokes W19/W21/W22 apply/rollback or any owner Windows host API.
"""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
W19 = ROOT / "scripts" / "ucie_owner_w19_data_task_stage_v01.ps1"
W21 = ROOT / "scripts" / "ucie_owner_w21_single_local_maintenance_v01.ps1"
W22 = ROOT / "scripts" / "ucie_owner_w22_quiesce_resume_local_v01.ps1"
W28 = ROOT / "scripts" / "ucie_owner_w28_transaction_state_model_v01.py"


class W28SourceAnchoredMigrationBoundaryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.w19 = W19.read_text("utf-8")
        cls.w21 = W21.read_text("utf-8")
        cls.w22 = W22.read_text("utf-8")
        cls.w28 = W28.read_text("utf-8")

    def test_w19_starts_private_journal_before_touching_operating_sqlite(self):
        src = self.w19
        first_save = src.index("PrivateJson $journal ([ordered]@{")
        handoff = src.index("& $python -I -B $handoff --prepare")
        w13 = src.index("& powershell.exe -NoProfile -NonInteractive -File $rebinder -Apply")
        self.assertLess(first_save, handoff)
        self.assertLess(handoff, w13)
        self.assertIn("UCIE_W19_FINAL_HANDOFF_FAILED_PRESERVE_PARTIAL_NO_RETRY", src)
        self.assertIn("ConfirmThree $false", src)

    def test_w21_actual_recovery_does_not_promote_partial_w19_to_no_stage(self):
        src = self.w21
        self.assertIn("function AssertPreRebindNoStage {", src)
        for guard in (
            "$w19Journal", "$w13Journal", "$w20Journal",
            "$w19Rollback", "$w20Rollback", "$marker",
            "$privateData", "$targetRuntime", "OriginalDisabled",
            "UCIE_W27_PRE_REBIND_C40_ACTION_DRIFT_HOLD",
        ):
            self.assertIn(guard, src)
        self.assertIn("pre_rebind_no_w19_stage=", src)
        self.assertIn("W27_PRE_REBIND_ORIGINAL_DISABLED_NO_DATA_STAGE", src)
        self.assertNotIn("Enable-ScheduledTask", src)
        self.assertNotIn("Start-ScheduledTask", src)
        self.assertNotIn("Stop-Process", src)

    def test_w22_legacy_records_already_one_shot_no_repeat(self):
        src = self.w22
        self.assertIn("UCIE_W22_OWNER_MAINTENANCE_INTENT_V01.json", src)
        self.assertIn("UCIE_W24_OWNER_RECOVERED_RETRY_INTENT_V01.json", src)
        self.assertIn("UCIE_W21_LOCAL_MAINTENANCE_INTENT_V01.json", src)
        self.assertLess(src.index("SavePrivate $intent ([ordered]@{"),
                        src.index("Disable-ScheduledTask -TaskPath"))
        self.assertIn("UCIE_W22_LISTENER_NOT_RELEASED_BY_OLD_TASK_EXPLICIT_RESUME", src)
        self.assertIn("UCIE_W22_PARTIAL_STAGE_WITHOUT_W21_JOURNAL_MANUAL_HOLD", src)
        self.assertIn("UCIE_W22_C40_ACTION_DRIFT_AFTER_W21", src)

    def test_w28_does_not_reuse_any_old_intents_or_call_real_maintenance(self):
        src = self.w28
        self.assertIn("NEW_INTENT = \"UCIE_W28_", src)
        self.assertIn("NEW_RECOVERY = \"UCIE_W28_", src)
        self.assertIn("NEW_RESTORED = \"UCIE_W28_", src)
        self.assertIn("HISTORICAL_INTENTS", src)
        self.assertIn("W28_OLD_TASKS_QUIESCED_PRE_REBIND_RECOVERY_CANDIDATE", src)
        self.assertIn("HOLD_W19_STAGE_REQUIRES_SEPARATE_ROLLBACK_REVIEW", src)
        self.assertIn("HOLD_INCOMPLETE_RECOVERY_ATTEMPT", src)
        self.assertIn("automatic_old_task_restart_allowed: bool = False", src)
        self.assertIn("full_cutover_authorized: bool = False", src)


if __name__ == "__main__":
    unittest.main()
