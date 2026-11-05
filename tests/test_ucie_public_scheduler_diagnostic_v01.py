"""UCIE exact public miner task read-only diagnostics, isolated fixtures."""
from __future__ import annotations

import copy
import json
from unittest import TestCase

from ucie_miner import public_scheduler_diagnostic_v01 as d


def fixture(*, code=0, state="Ready", event_count=2,
            original_status="TWO_CYCLE_BASE_COLLECTOR_OBSERVED"):
    return {
        "schema": d.SOURCE_SCHEMA,
        "task_found": True,
        "task_state": state,
        "last_task_result": code,
        "evidence": {
            "schema": d.PROOF_SCHEMA,
            "status": original_status,
            "scheduled_task_registered": True,
            "action_matches_ucie_only": True,
            "owner_least_privilege_verified": True,
            "hourly_no_overlap_configured": True,
            "last_task_result_zero": code == 0,
            "scheduler_event_log_readable": True,
            "scheduler_event_instance_receipts_verified": event_count,
            "last_scheduled_run_matches_receipt": event_count == 2,
            "two_recent_hourly_successes": event_count == 2,
            "scheduler_changed": False,
            "database_modified": False,
        },
    }


class ExactUcIePublicTaskEvidenceTests(TestCase):
    def test_only_exact_zero_and_two_task_bound_events_is_success(self):
        report = d.analyze_scheduler_observation(fixture())
        self.assertEqual(report["status"], d.GO)
        self.assertEqual(report["last_task_result_hex"], "0x00000000")
        self.assertEqual(report["blocker_codes"], [])
        self.assertFalse(report["remediation_executed"])
        self.assertFalse(report["actual_task_mutation"])

    def test_user_report_lasttask_no_go_and_only_one_event_stays_blocked(self):
        observed = fixture(code=0x00041306, event_count=1,
                           original_status="LAST_TASK_RESULT_NO_GO")
        r = d.analyze_scheduler_observation(observed)
        self.assertEqual(r["status"], d.NO_GO)
        self.assertEqual(r["last_task_result_interpretation"],
                         "SCHED_S_TASK_TERMINATED")
        self.assertIn("TWO_EXACT_INSTANCE_EVENT_RECEIPTS_NOT_PROVEN",
                      r["blocker_codes"])
        self.assertIn("SCHEDULER_REPORTED_LAST_RUN_TERMINATED",
                      r["blocker_codes"])
        self.assertEqual(r["matched_event_instances"], 1)

    def test_running_task_is_not_misclassified_as_failed_or_success(self):
        r = d.analyze_scheduler_observation(fixture(
            code=0x41301, state="Running", event_count=1,
            original_status="LAST_TASK_RESULT_NO_GO"))
        self.assertEqual(r["last_task_result_hex"], "0x00041301")
        self.assertEqual(r["last_task_result_interpretation"],
                         "SCHED_S_TASK_RUNNING")
        self.assertIn("RUNNING_TASK_WAIT_FOR_COMPLETED_EVENT_BEFORE_GO",
                      r["blocker_codes"])
        self.assertEqual(r["status"], d.NO_GO)

    def test_outdated_running_code_in_ready_state_is_inconsistent(self):
        r = d.analyze_scheduler_observation(fixture(
            code=0x41301, state="Ready", event_count=1,
            original_status="LAST_TASK_RESULT_NO_GO"))
        self.assertIn("LAST_RUNNING_CODE_AND_CURRENT_STATE_DIFFER",
                      r["blocker_codes"])

    def test_unknown_nonzero_preserves_exact_numeric_code(self):
        r = d.analyze_scheduler_observation(fixture(
            code=0xDEADBEEF, event_count=1,
            original_status="LAST_TASK_RESULT_NO_GO"))
        self.assertEqual(r["last_task_result_hex"], "0xDEADBEEF")
        self.assertEqual(r["last_task_result_interpretation"],
                         "NONZERO_RESULT_UNKNOWN_EXACT_CODE_REQUIRED")
        self.assertEqual(r["status"], d.NO_GO)
        self.assertIn("UNKNOWN_RESULT_REQUIRES_EXACT_EVENT_TRIAGE",
                      r["blocker_codes"])

    def test_correct_exit_code_but_one_event_is_no_go(self):
        a = fixture(event_count=1, original_status=
                    "LAST_SCHEDULED_RUN_RECEIPT_MISMATCH_NO_GO")
        r = d.analyze_scheduler_observation(a)
        self.assertEqual(r["status"], d.NO_GO)
        self.assertIn("TWO_EXACT_INSTANCE_EVENT_RECEIPTS_NOT_PROVEN",
                      r["blocker_codes"])

    def test_zero_code_does_not_override_failed_original_proof(self):
        a = fixture()
        a["evidence"]["status"] = "TASK_IDENTITY_OR_CADENCE_NO_GO"
        r = d.analyze_scheduler_observation(a)
        self.assertIn("ORIGINAL_OWNER_EVIDENCE_NO_GO", r["blocker_codes"])
        self.assertEqual(r["status"], d.NO_GO)

    def test_fake_return_boolean_rejected(self):
        a = fixture()
        a["last_task_result"] = True
        with self.assertRaises(d.SchedulerEvidenceError):
            d.analyze_scheduler_observation(a)

    def test_forged_boolean_or_duplicate_event_count_rejected(self):
        a = fixture()
        a["evidence"]["scheduler_event_instance_receipts_verified"] = True
        with self.assertRaises(d.SchedulerEvidenceError):
            d.analyze_scheduler_observation(a)
        a = fixture()
        a["evidence"]["scheduler_event_instance_receipts_verified"] = -1
        with self.assertRaises(d.SchedulerEvidenceError):
            d.analyze_scheduler_observation(a)

    def test_missing_untrusted_or_undeclared_fields_rejected(self):
        for mutation in (
            lambda x: x["evidence"].pop("database_modified"),
            lambda x: x.update(sneaky_auto_repair=True),
            lambda x: x["evidence"].update(status="FORGED_PASS"),
            lambda x: x["evidence"].update(auto_approval=True),
            lambda x: x.update(task_state="../unsafe")):
            a = copy.deepcopy(fixture())
            mutation(a)
            with self.subTest(mutation=mutation), self.assertRaises(
                    d.SchedulerEvidenceError):
                d.analyze_scheduler_observation(a)

    def test_code_vs_original_zero_flag_inconsistent_rejected(self):
        a = fixture(code=267009)
        a["evidence"]["last_task_result_zero"] = True
        with self.assertRaises(d.SchedulerEvidenceError):
            d.analyze_scheduler_observation(a)

    def test_missing_task_never_looks_like_zero_candidates_or_success(self):
        a = fixture()
        a["task_found"] = False
        a["task_state"] = "Absent"
        a["last_task_result"] = None
        a["evidence"]["status"] = "NOT_REGISTERED_NO_GO"
        a["evidence"]["scheduled_task_registered"] = False
        a["evidence"]["last_task_result_zero"] = False
        a["evidence"]["scheduler_event_instance_receipts_verified"] = 0
        a["evidence"]["last_scheduled_run_matches_receipt"] = False
        a["evidence"]["two_recent_hourly_successes"] = False
        r = d.analyze_scheduler_observation(a)
        self.assertEqual(r["status"], d.NO_GO)
        self.assertIsNone(r["last_task_result_decimal"])
        self.assertIn("EXACT_UCIE_TASK_MISSING", r["blocker_codes"])

    def test_code_value_outside_uint32_rejected(self):
        for code in (-1, 4294967296, 1.0, "0", None):
            a = fixture()
            a["last_task_result"] = code
            a["evidence"]["last_task_result_zero"] = False
            with self.subTest(code=code), self.assertRaises(
                    d.SchedulerEvidenceError):
                d.analyze_scheduler_observation(a)

    def test_provenance_no_network_or_mutation_even_when_go(self):
        r = d.analyze_scheduler_observation(fixture())
        self.assertEqual(r["operating_database_writes"], 0)
        self.assertEqual(r["public_network_requests"], 0)
        self.assertFalse(r["other_project_access"])
        self.assertTrue(r["classification_is_not_new_event_or_process_proof"])

    def test_owner_powershell_source_fixed_task_only_and_no_mutator(self):
        from pathlib import Path
        root = Path(__file__).resolve().parents[1]
        script = (root / "scripts" /
                  "ucie_public_miner_scheduler_diagnostic_v01.ps1").read_text(
                      encoding="utf-8")
        self.assertIn("Get-ScheduledTask -TaskPath '\\' -TaskName 'UCIE-PublicMiner-Hourly'", script)
        self.assertIn("Get-ScheduledTaskInfo -TaskPath '\\' -TaskName 'UCIE-PublicMiner-Hourly'", script)
        self.assertIn("& $existing -Evidence", script)
        self.assertIn("public_scheduler_diagnostic_v01", script)
        for mutator in ("Start-ScheduledTask", "Stop-ScheduledTask",
                        "Register-ScheduledTask", "Unregister-ScheduledTask",
                        "Set-ScheduledTask", "Stop-Process", "Start-Process"):
            self.assertNotIn(mutator + " ", script)

    def test_existing_owner_report_exposes_numeric_code_and_blockers(self):
        from pathlib import Path
        report = (Path(__file__).resolve().parents[1] /
                  "scripts" / "ucie_public_collection_report_v01.ps1"
                  ).read_text(encoding="utf-8")
        self.assertIn("ucie_public_miner_scheduler_diagnostic_v01.ps1", report)
        self.assertIn("last_task_result_decimal", report)
        self.assertIn("last_task_result_hex", report)
        self.assertIn("blocker_codes", report)
        self.assertIn("diagnostic_validated", report)
        self.assertIn("SCHEDULER_NOT_ATTESTED_NO_GO", report)

    def test_operational_event_triage_reads_exact_task_only(self):
        from pathlib import Path
        source = (Path(__file__).resolve().parents[1] /
                  "scripts" / "ucie_public_miner_task_event_triage_v01.ps1"
                  ).read_text(encoding="utf-8")
        self.assertIn("TaskName']='\\UCIE-PublicMiner-Hourly'", source)
        self.assertIn("Get-WinEvent -LogName 'Microsoft-Windows-TaskScheduler/Operational'", source)
        self.assertIn("Get-ScheduledTask -TaskPath '\\' -TaskName 'UCIE-PublicMiner-Hourly'", source)
        self.assertIn("-MaxEvents 64", source)
        self.assertIn("if ($rows.Count -ge 24)", source)
        self.assertNotIn("$event.Message", source)
        for cmd in ("Start-ScheduledTask", "Stop-ScheduledTask",
                    "Register-ScheduledTask", "Unregister-ScheduledTask",
                    "Set-ScheduledTask", "Stop-Process", "Start-Process"):
            self.assertNotIn(cmd + " ", source)


if __name__ == "__main__":
    import unittest
    unittest.main()
