"""W28 synthetic first-party new owner transaction failure-state matrix.

Pure in-memory states only. No Windows host access, SQLite, Task Scheduler,
C40, Git mutation, owner credentials, private files or external fetches.
"""
from __future__ import annotations

import importlib.util
import json
from dataclasses import replace
from pathlib import Path
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "scripts" / "ucie_owner_w28_transaction_state_model_v01.py"

spec = importlib.util.spec_from_file_location("ucie_w28_state_fixture", SOURCE)
assert spec and spec.loader
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)


class W28SyntheticOwnerTransactionSafetyTests(unittest.TestCase):
    def check_hold(self, owner, starts: str = "HOLD_"):
        decision = module.classify(owner)
        self.assertTrue(decision.status.startswith(starts), decision)
        self.assertFalse(decision.full_cutover_authorized)
        self.assertFalse(decision.automatic_old_task_restart_allowed)
        self.assertFalse(decision.task_scheduler_changed)
        self.assertFalse(decision.database_opened)
        self.assertFalse(decision.c40_queried_or_modified)
        self.assertFalse(decision.journal_written)
        self.assertTrue(decision.simulated_only)
        return decision

    def test_no_host_contract_without_scenario(self):
        proc = subprocess.run(
            [sys.executable, "-I", "-B", str(SOURCE)],
            capture_output=True, text=True, timeout=25)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        data = json.loads(proc.stdout)
        self.assertEqual(data["status"], "UCIE_W28_CONTRACT_ONLY_NO_HOST_ACCESS")
        self.assertEqual(data["expected_w27_main"],
                         "dd503ef37c908dccd7216fe8ecf1bcf061cc97ed")
        self.assertFalse(data["legacy_receipts_reused"])
        self.assertFalse(data["real_owner_host_accessed"])
        self.assertFalse(data["task_or_c40_modified"])
        self.assertFalse(data["journal_written"])
        self.assertFalse(data["sqlite_opened"])
        self.assertFalse(data["full_cutover_authorized"])

    def test_fresh_new_intent_names_distinct_and_historical_immutable(self):
        new = (module.NEW_INTENT, module.NEW_RECOVERY, module.NEW_RESTORED)
        self.assertEqual(len(set(new)), 3)
        self.assertTrue(all(name.startswith("UCIE_W28_") for name in new))
        self.assertFalse(set(new) & set(module.HISTORICAL_INTENTS))
        self.assertEqual(len(module.OLD_TASK_NAMES), 3)
        self.assertIn("UCIE-LocalV1-Web", module.OLD_TASK_NAMES)

    def test_baseline_running_never_authorizes_outage(self):
        state = module.OwnerSnapshot()
        decision = module.classify(state)
        self.assertEqual(
            decision.status, "W28_FRESH_PLAN_ELIGIBLE_NOT_AUTHORIZED")
        self.assertEqual(decision.recommended_workflow,
                         "SOURCE_DESIGN_ONLY__FRESH_OWNER_APPROVAL_REQUIRED")
        self.assertFalse(decision.full_cutover_authorized)
        self.assertFalse(decision.task_scheduler_changed)

    def test_exact_prejournal_recovery_is_candidate_only(self):
        state = module.fixtures()["prejournal-recovery"]
        decision = module.classify(state)
        self.assertEqual(
            decision.status,
            "W28_OLD_TASKS_QUIESCED_PRE_REBIND_RECOVERY_CANDIDATE")
        self.assertIn("LOCALV1_THEN_WRITERS", decision.recommended_workflow)
        self.assertFalse(decision.automatic_old_task_restart_allowed)
        self.assertFalse(decision.journal_written)
        self.assertFalse(decision.full_cutover_authorized)

    def test_every_staged_file_refuses_premature_recovery(self):
        initial = module.fixtures()["prejournal-recovery"]
        for name in module.STAGE_ITEMS:
            with self.subTest(residual=name):
                changed = replace(initial, **{name: True})
                self.check_hold(changed)

    def test_any_task_action_or_state_drift_refuses_auto_restore(self):
        initial = module.fixtures()["prejournal-recovery"]
        for pos in range(3):
            for action in ("NEW_EXACT", "UNKNOWN"):
                actions = list(initial.actions)
                actions[pos] = action
                with self.subTest(index=pos, action=action):
                    self.check_hold(replace(initial, actions=tuple(actions)))
            for state in ("Ready", "Running", "Missing"):
                states = list(initial.states)
                states[pos] = state
                with self.subTest(index=pos, state=state):
                    self.check_hold(replace(initial, states=tuple(states)))

    def test_any_owner_c40_acl_or_source_drift_blocks(self):
        initial = module.fixtures()["prejournal-recovery"]
        for attr in (
            "same_owner_sid", "owner_uac_elevated",
            "archive_acl_protected", "c40_task_running",
            "c40_action_hash_unchanged",
            "history_preserved_and_recovered",
            "pinned_first_party_source",
        ):
            with self.subTest(attr=attr):
                self.check_hold(replace(initial, **{attr: False}))

    def test_foreign_listener_and_healthy_http_in_quiesced_state_block(self):
        initial = module.fixtures()["prejournal-recovery"]
        self.check_hold(replace(initial, port_state="OTHER_OR_MULTIPLE"))
        self.check_hold(replace(initial,
                                port_state="ONE_LOOPBACK_HEALTHY_OLD"))
        self.check_hold(replace(initial, old_http_healthy=True))

    def test_existing_restoration_or_recovery_intent_prevents_retry(self):
        initial = module.fixtures()["prejournal-recovery"]
        dec = self.check_hold(replace(
            initial, w28_restored_receipt_exists=True))
        self.assertEqual(dec.status, "HOLD_RESTORATION_ALREADY_RECORDED")
        dec = self.check_hold(replace(
            initial, w28_recovery_intent_exists=True))
        self.assertEqual(dec.status, "HOLD_INCOMPLETE_RECOVERY_ATTEMPT")

    def test_new_intent_with_tasks_still_running_is_not_recovery_candidate(self):
        initial = module.OwnerSnapshot(w28_intent_exists=True)
        self.check_hold(initial)

    def test_partial_rebind_never_triggers_prejournal_route(self):
        initial = module.fixtures()["prejournal-recovery"]
        bad = replace(initial, w13_rebind_journal=True,
                      actions=("NEW_EXACT",) * 3)
        self.check_hold(bad)
        bad = replace(initial, w20_pilot_journal=True)
        self.check_hold(bad)

    def test_fixed_scenarios_are_synthetic_without_output_secret_data(self):
        for name, item in module.fixtures().items():
            with self.subTest(name=name):
                expected = module.classify(item).as_dict()
                self.assertTrue(expected["simulated_only"])
                self.assertFalse(expected["journal_written"])
                self.assertFalse(expected["database_opened"])
                self.assertFalse(expected["task_scheduler_changed"])
                self.assertFalse(expected["c40_queried_or_modified"])
                self.assertFalse(expected["full_cutover_authorized"])
                self.assertFalse(expected["automatic_old_task_restart_allowed"])
                proc = subprocess.run(
                    [sys.executable, "-I", "-B", str(SOURCE),
                     "--scenario", name],
                    capture_output=True, text=True, timeout=25)
                self.assertEqual(proc.returncode, 0, proc.stderr)
                got = json.loads(proc.stdout)
                self.assertEqual(got["status"], expected["status"])
                self.assertEqual(got["scenario"], name)

    def test_arbitrary_fixture_file_or_external_code_denied(self):
        proc = subprocess.run(
            [sys.executable, "-I", "-B", str(SOURCE),
             "--scenario", "../../other_project"],
            capture_output=True, text=True, timeout=25)
        self.assertNotEqual(proc.returncode, 0)
        self.assertNotIn("D:\\", proc.stdout)

    def test_no_live_host_or_mutating_api_imports(self):
        code = SOURCE.read_text("utf-8")
        for forbidden in (
            "import os", "import pathlib", "from pathlib",
            "subprocess", "sqlite3", "winreg", "ctypes",
            "Get-ScheduledTask", "Stop-ScheduledTask",
            "Start-ScheduledTask", "Disable-ScheduledTask",
            "Enable-ScheduledTask", "Stop-Process", "taskkill",
            "GitHub", "requests", "httpx", "urllib", "socket",
            "open(", "Path(", "read_text(", "write_text(",
        ):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, code)


if __name__ == "__main__":
    unittest.main()
