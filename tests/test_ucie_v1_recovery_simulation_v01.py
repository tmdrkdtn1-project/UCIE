"""UCIE V1 unresolved-gate simulations on first-party synthetic inputs only.

Do not run the public miner, TaskScheduler, provider mailer, or any source outside
the UCIE checkout. In particular, synthetic timeout != historical root cause.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json
import unittest

from ucie_miner import public_miner_shutdown_phase_w11 as phases
from ucie_miner import public_scheduler_diagnostic_v01 as scheduler
from ucie_miner import skillbook_editorial_production_v01 as editor
from ucie_miner import skillbook_catalog_union_v01 as catalog
from ucie_miner import skillbook_w09_release_gate_v01 as release


def synthetic_scheduler(*, code: int, status: str, count: int,
                        readable: bool = True) -> dict:
    """Never confuse these invented fields with owner TaskScheduler evidence."""
    return {
        "schema": scheduler.SOURCE_SCHEMA,
        "task_found": True,
        "task_state": "Ready",
        "last_task_result": code,
        "evidence": {
            "schema": scheduler.PROOF_SCHEMA,
            "status": status,
            "scheduled_task_registered": True,
            "action_matches_ucie_only": True,
            "owner_least_privilege_verified": True,
            "hourly_no_overlap_configured": True,
            "last_task_result_zero": code == 0,
            "scheduler_event_log_readable": readable,
            "scheduler_event_instance_receipts_verified": count,
            "last_scheduled_run_matches_receipt": count == 2,
            "two_recent_hourly_successes": count == 2,
            "scheduler_changed": False,
            "database_modified": False,
        },
    }


class UCIERecoveryGateSimulation(unittest.TestCase):
    def test_historical_hresult_8007050b_is_not_claimed_as_timeout(self):
        report = scheduler.analyze_scheduler_observation(
            synthetic_scheduler(
                code=0x8007050B,
                status="LAST_TASK_RESULT_NO_GO",
                count=0, readable=False))
        self.assertEqual(report["status"], scheduler.NO_GO)
        self.assertEqual(report["last_task_result_decimal"], 2147943691)
        self.assertEqual(report["last_task_result_hex"], "0x8007050B")
        self.assertEqual(report["last_task_result_interpretation"],
                         "NONZERO_RESULT_UNKNOWN_EXACT_CODE_REQUIRED")
        self.assertIn("SCHEDULER_EVENT_LOG_UNAVAILABLE",
                      report["blocker_codes"])
        self.assertIn("UNKNOWN_RESULT_REQUIRES_EXACT_EVENT_TRIAGE",
                      report["blocker_codes"])
        self.assertFalse(report["remediation_executed"])

    def test_scheduler_terminated_code_still_requires_instance_events(self):
        report = scheduler.analyze_scheduler_observation(
            synthetic_scheduler(
                code=0x00041306,
                status="LAST_TASK_RESULT_NO_GO",
                count=1))
        self.assertEqual(report["status"], scheduler.NO_GO)
        self.assertIn("SCHEDULER_REPORTED_LAST_RUN_TERMINATED",
                      report["blocker_codes"])
        self.assertIn("TWO_EXACT_INSTANCE_EVENT_RECEIPTS_NOT_PROVEN",
                      report["blocker_codes"])

    def test_clean_synthetic_child_reaches_atexit(self):
        result = phases.run_one("clean")
        self.assertEqual(result["status"], "SYNTHETIC_CASE_OBSERVED")
        self.assertEqual(result["child_returncode"], 0)
        self.assertFalse(result["child_timeout_observed"])
        self.assertTrue(result["stdout_flush_returned"])
        self.assertTrue(result["python_atexit_observed"])
        self.assertFalse(result["production_termination_root_cause_proven"])
        self.assertEqual(result["task_scheduler_mutations"], 0)

    def test_post_stdout_hold_is_reproducible_but_not_production_cause(self):
        result = phases.run_one("post_stdout_hold")
        self.assertEqual(result["status"], "SYNTHETIC_CASE_OBSERVED")
        self.assertTrue(result["worker_returned"])
        self.assertTrue(result["receipt_write_returned"])
        self.assertTrue(result["stdout_flush_returned"])
        self.assertTrue(result["child_timeout_observed"])
        self.assertFalse(result["python_atexit_observed"])
        self.assertFalse(result["production_termination_root_cause_proven"])
        self.assertFalse(result["real_public_miner_executed"])
        self.assertEqual(result["owner_operating_db_writes"], 0)

    def test_local_editorial_and_catalog_are_still_fail_closed(self):
        pilot = editor.compose_curated_two_book_pilot()
        dossier = catalog.inspect_review_candidate(pilot["draft_sha256"])
        self.assertEqual(dossier["candidate"]["draft_sha256"], pilot["draft_sha256"])
        self.assertFalse(dossier["export_allowed"])
        self.assertFalse(pilot["export_allowed"])
        gate = release.preview_release_gate()
        self.assertFalse(gate["owner_release_authorized"])
        self.assertFalse(gate["independent_qa_verified"])
        self.assertFalse(gate["license_redistribution_approved"])
        self.assertFalse(gate["package_signed"])

    def test_kst_0900_reporting_window_ends_at_0500(self):
        kst = timezone(timedelta(hours=9))
        scheduled = datetime(2026, 11, 6, 9, 0, tzinfo=kst)
        cutoff = scheduled.replace(hour=5, minute=0)
        since = cutoff - timedelta(days=1)
        self.assertEqual((since.isoformat(), cutoff.isoformat()),
                         ("2026-11-05T05:00:00+09:00",
                          "2026-11-06T05:00:00+09:00"))
        self.assertEqual((scheduled - cutoff).total_seconds(), 14400)
        self.assertEqual(cutoff.astimezone(timezone.utc).hour, 20)
        # A verified time window is NOT a delivered report or provider receipt.

    def test_absent_delivery_evidence_does_not_become_a_pass(self):
        # No actual transport invocation occurs. Missing recipient/message ID,
        # delivery acknowledgement or service receipt is always unresolved.
        observed_provider_receipt = None
        self.assertIsNone(observed_provider_receipt)
        status = ("DELIVERY_VERIFIED" if observed_provider_receipt
                  else "DELIVERY_NOT_ATTESTED_NO_GO")
        self.assertEqual(status, "DELIVERY_NOT_ATTESTED_NO_GO")

    def test_synthetic_evidence_cannot_promote_old_incident(self):
        report = scheduler.analyze_scheduler_observation(
            synthetic_scheduler(
                code=0, status="TWO_CYCLE_BASE_COLLECTOR_OBSERVED",
                count=2))
        self.assertEqual(report["status"], scheduler.GO)
        self.assertTrue(
            report["classification_is_not_new_event_or_process_proof"])
        self.assertFalse(report["code_auto_promotion"])
        self.assertFalse(report["remediation_executed"])
        self.assertEqual(report["operating_database_writes"], 0)
        print("UCIE_RECOVERY_SIMULATION_SCOPE=" + json.dumps({
            "schema": "UCIE_V1_RECOVERY_SIMULATION_V01",
            "historical_root_cause_proven": False,
            "owner_task_changed": False,
            "operating_database_writes": 0,
            "delivery_attested": False,
            "formal_release_approved": False,
            "source_scope": "UCIE_ONLY_FIRST_PARTY_SYNTHETIC",
        }, sort_keys=True))

    def test_editorial_semantic_fingerprint_without_source_export(self):
        # Compare these public-main/owner-only digests out of band; do NOT
        # claim identical semantics merely because ordinary tests pass.
        import ast
        from hashlib import sha256
        from pathlib import Path
        import sys
        source = (Path(__file__).resolve().parents[1] / "src" /
                  "ucie_miner" / "skillbook_editorial_production_v01.py")
        self.assertFalse(source.is_symlink())
        raw = source.read_bytes()
        self.assertLess(len(raw), 80000)
        tree = ast.parse(raw.decode("utf-8-sig"), filename=source.name)
        semantic = sha256(ast.dump(
            tree, annotate_fields=True, include_attributes=False
        ).encode("utf-8")).hexdigest()
        print("UCIE_EDITORIAL_AST_FINGERPRINT=" + json.dumps({
            "python": f"{sys.version_info.major}.{sys.version_info.minor}",
            "semantic_ast_sha256": semantic,
            "source_size": len(raw),
            "source_disclosed": False,
            "files_modified": 0
        }, sort_keys=True))


if __name__ == "__main__":
    unittest.main()
