"""UCIE-only synthetic regression: optional Stage10 failure must not erase receipts.

A successful legacy collection receipt is not proof that the scheduled
Python action exited 0. No real task, operating DB or network is accessed.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
from hashlib import sha256
import json
import tempfile
import unittest

from ucie_miner.library_hourly_proof_v12 import (
    HourlyProofError, inspect_hourly_public_library,
)
from ucie_miner.public_collection_inventory_v01 import (
    NO_GO, collection_inventory,
)

NOW = datetime(2026, 11, 8, 6, 0, tzinfo=timezone.utc)
GOOD = "STAGE10_UNVERIFIED_STAGED_NO_GO"
FAILED = "STAGE10_HOURLY_FAILED_NO_GO"
PARTIAL = "STAGE10_HOURLY_PARTIAL_NO_GO"
PROOF_OK = "TWO_FRESH_CYCLE_RECEIPTS_OBSERVED_SCHEDULER_NOT_ATTESTED"
PROOF_FAIL = "HOURLY_CYCLE_ACTIVITY_NOT_PROVEN_NO_GO"


def receipt(time: datetime, stage10: str) -> dict:
    return {
        "schema": "UCIE_MINER_CYCLE_V1",
        "status": "COLLECTED_UNVERIFIED",
        "started_utc": time.isoformat(timespec="seconds"),
        "finished_utc": (time + timedelta(seconds=18)).isoformat(timespec="seconds"),
        "new_candidates": 0,
        "sources_checked": 2,
        "verification_pass": 0,
        "production_approved": False,
        "consecutive_failures": 0,
        "stage10_status": stage10,
    }


class Stage10IncidentReceiptReconciliation(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="ucie-stage10-gate-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / "UCIE"
        self.runtime = self.root / "runtime"
        self.runtime.mkdir(parents=True)

    def store(self, before_stage10: str, latest_stage10: str):
        before = receipt(NOW - timedelta(minutes=83), before_stage10)
        latest = receipt(NOW - timedelta(minutes=23), latest_stage10)
        lines = [json.dumps(d, sort_keys=True) for d in (before, latest)]
        (self.runtime / "run_history.jsonl").write_text(
            "\n".join(lines) + "\n", encoding="utf-8")
        (self.runtime / "last_run.json").write_text(
            lines[-1] + "\n", encoding="utf-8")

    def test_prior_stage10_failure_is_readable_and_fails_hourly_health(self):
        self.store(FAILED, GOOD)
        proof = inspect_hourly_public_library(self.root, now=NOW)
        self.assertEqual(proof["status"], PROOF_FAIL)
        self.assertTrue(proof["two_successful_collection_receipts"])
        self.assertTrue(proof["stage10_failure_or_partial_in_last_two"])
        self.assertEqual(proof["last_two_stage10_statuses"], [FAILED, GOOD])
        self.assertEqual(proof["started_cadence_minutes"], 60)
        self.assertFalse(proof["task_scheduler_event_proof_checked"])
        self.assertEqual(proof["operating_db_writes"], 0)

    def test_latest_stage10_failure_is_not_mistaken_for_missing_history(self):
        self.store(GOOD, FAILED)
        proof = inspect_hourly_public_library(self.root, now=NOW)
        self.assertEqual(proof["status"], PROOF_FAIL)
        self.assertTrue(proof["stage10_failure_or_partial_in_last_two"])
        self.assertEqual(proof["stage_statuses"][
            "stage10_public_candidate_collection"], FAILED)
        self.assertIsNotNone(proof["latest_finished_utc"])
        self.assertFalse(proof["model_weights_trained"])

    def test_stage10_partial_is_also_unhealthy(self):
        self.store(PARTIAL, GOOD)
        proof = inspect_hourly_public_library(self.root, now=NOW)
        self.assertEqual(proof["status"], PROOF_FAIL)
        self.assertTrue(proof["stage10_failure_or_partial_in_last_two"])

    def test_two_normal_legacy_staging_outcomes_remain_truthful(self):
        self.store(GOOD, GOOD)
        proof = inspect_hourly_public_library(self.root, now=NOW)
        self.assertEqual(proof["status"], PROOF_OK)
        self.assertFalse(proof["stage10_failure_or_partial_in_last_two"])
        self.assertEqual(proof["last_two_stage10_statuses"], [GOOD, GOOD])
        # A healthy receipt-only result does NOT assert scheduler health.
        self.assertFalse(proof["task_scheduler_event_proof_checked"])

    def test_unrecognized_stage10_status_remains_rejected(self):
        self.store("STAGE10_APPROVED_FOR_CUSTOMER", GOOD)
        with self.assertRaises(HourlyProofError):
            inspect_hourly_public_library(self.root, now=NOW)

    def test_read_only_proof_keeps_receipt_bytes_identical(self):
        self.store(FAILED, GOOD)
        paths = [self.runtime / "last_run.json",
                 self.runtime / "run_history.jsonl"]
        old = [sha256(p.read_bytes()).hexdigest() for p in paths]
        self.assertEqual(
            inspect_hourly_public_library(self.root, now=NOW)["status"],
            PROOF_FAIL)
        self.assertEqual([sha256(p.read_bytes()).hexdigest()
                          for p in paths], old)

    def test_inventory_preserves_failure_and_timestamp_instead_of_missing(self):
        self.store(FAILED, GOOD)
        report = collection_inventory(
            self.root, now=NOW,
            legacy_reader=lambda _runtime: {
                "status": "LEGACY_UNVERIFIED_COUNT_READ_ONLY",
                "candidates": 2, "runs": 2, "by_source": {
                    "python/cpython": 1, "PowerShell/PowerShell": 1},
                "invalid_status_rows": 0,
                "last_run_utc": (NOW - timedelta(minutes=23)).isoformat(),
                "latest_added_candidates": 0},
            stage10_reader=lambda _root: {
                "status": "UNVERIFIED_CANDIDATE_STAGING_INSPECTED_NO_GO",
                "candidate_revisions": 1, "git_commit_revisions": 0},
            stage12_reader=lambda _root: {
                "status": "STAGE12_UNVERIFIED_REVIEW_INSPECTED_NO_GO",
                "review_proposals": 1},
            hourly_reader=lambda root, now: inspect_hourly_public_library(
                root, now=now))
        self.assertEqual(report["status"], NO_GO)
        self.assertIn("HOURLY_RECENT_ACTIVITY_UNPROVEN", report["issues"])
        self.assertNotIn("HOURLY_RECEIPTS_UNAVAILABLE", report["issues"])
        self.assertEqual(report["recent_hourly_activity"]["status"],
                         PROOF_FAIL)
        self.assertTrue(report["recent_hourly_activity"][
            "two_successful_collection_receipts"])
        self.assertIsNotNone(report["recent_hourly_activity"][
            "last_finished_utc"])
        self.assertFalse(report["current_windows_task_scheduler_events_verified"])
        self.assertEqual(report["operating_database_writes"], 0)
        self.assertFalse(report["scheduler_changed"])


if __name__ == "__main__":
    unittest.main()
