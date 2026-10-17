"""Offline Stage-3 worker schedule integration tests."""
import json
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from ucie_miner.worker import run_cycle


class WorkerScheduleTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def collect(self, root):
        return {"status": "COLLECTED_UNVERIFIED", "new_candidates": 0,
                "sources_checked": 1, "verification_pass": 0,
                "production_approved": False}

    def write_report(self, root):
        path = root / "runtime" / "reports" / "test.md"
        path.parent.mkdir(exist_ok=True)
        path.write_text("unverified", encoding="utf-8")
        return path

    def test_run_then_skip(self):
        first = run_cycle(self.root, collect=self.collect,
                          write_report=self.write_report, enforce_schedule=True)
        self.assertEqual(first["status"], "COLLECTED_UNVERIFIED")
        second = run_cycle(self.root, collect=lambda _: self.fail("called too soon"),
                           write_report=self.write_report, enforce_schedule=True)
        self.assertEqual(second["status"], "SKIPPED_NOT_DUE")

    def test_bad_prior_receipt_fails_closed(self):
        runtime = self.root / "runtime"
        runtime.mkdir()
        (runtime / "last_run.json").write_text("{", encoding="utf-8")
        with self.assertRaises(ValueError):
            run_cycle(self.root, collect=self.collect,
                      write_report=self.write_report, enforce_schedule=True)

    def test_failed_run_backoff_and_no_sensitive_error(self):
        def failing(_):
            raise ValueError("Bearer secret-value-should-not-be-recorded")
        first = run_cycle(self.root, collect=failing,
                          write_report=self.write_report, enforce_schedule=True)
        self.assertEqual(first["status"], "COLLECTION_FAILED")
        self.assertEqual(first["consecutive_failures"], 1)
        self.assertNotIn("secret-value", (self.root / "runtime" / "last_run.json").read_text())
        second = run_cycle(self.root, collect=lambda _: self.fail("backoff broken"),
                           write_report=self.write_report, enforce_schedule=True)
        self.assertEqual(second["status"], "SKIPPED_NOT_DUE")

    def test_recovery_after_elapsed_retry_window(self):
        runtime = self.root / "runtime"
        runtime.mkdir()
        previous = {
            "schema": "UCIE_MINER_CYCLE_V1",
            "finished_utc": (datetime.now(timezone.utc) - timedelta(minutes=20)).isoformat(),
            "consecutive_failures": 3,
            "status": "COLLECTION_FAILED",
        }
        (runtime / "last_run.json").write_text(json.dumps(previous), encoding="utf-8")
        result = run_cycle(self.root, collect=self.collect,
                           write_report=self.write_report, enforce_schedule=True)
        self.assertEqual(result["status"], "COLLECTED_UNVERIFIED")
        self.assertEqual(result["consecutive_failures"], 0)

    def test_invalid_failure_counter_fails_closed(self):
        runtime = self.root / "runtime"
        runtime.mkdir()
        previous = {
            "schema": "UCIE_MINER_CYCLE_V1",
            "finished_utc": (datetime.now(timezone.utc) - timedelta(hours=3)).isoformat(),
            "consecutive_failures": True,
        }
        (runtime / "last_run.json").write_text(json.dumps(previous), encoding="utf-8")
        with self.assertRaises(ValueError):
            run_cycle(self.root, collect=self.collect,
                      write_report=self.write_report, enforce_schedule=True)

    def test_task_hourly_start_timestamp_avoids_alternate_hour_skip(self):
        runtime = self.root / "runtime"
        runtime.mkdir()
        now = datetime.now(timezone.utc)
        start = now - timedelta(hours=1, seconds=5)
        prior = {
            "schema": "UCIE_MINER_CYCLE_V1",
            "started_utc": start.isoformat(),
            "finished_utc": (start + timedelta(seconds=8)).isoformat(),
            "consecutive_failures": 0,
            "status": "COLLECTED_UNVERIFIED",
        }
        (runtime / "last_run.json").write_text(json.dumps(prior), encoding="utf-8")
        outcome = run_cycle(self.root, collect=self.collect,
                            write_report=self.write_report, enforce_schedule=True)
        self.assertEqual(outcome["status"], "COLLECTED_UNVERIFIED")

    def test_optional_stage_failure_class_is_saved_without_message(self):
        def with_stage(_):
            legacy = self.collect(_)
            legacy["stage10"] = {
                "status": "STAGE10_HOURLY_FAILED_NO_GO",
                "error_type": "DiscoveryError",
            }
            return legacy
        outcome = run_cycle(self.root, collect=with_stage,
                            write_report=self.write_report, enforce_schedule=False)
        self.assertEqual(outcome["status"], "COLLECTED_UNVERIFIED")
        self.assertEqual(outcome["stage10_status"], "STAGE10_HOURLY_FAILED_NO_GO")
        self.assertEqual(outcome["stage10_error_type"], "DiscoveryError")
        last = json.loads((self.root / "runtime" / "last_run.json").read_text())
        self.assertEqual(last["stage10_error_type"], "DiscoveryError")
        self.assertEqual(last["stage10_status"], "STAGE10_HOURLY_FAILED_NO_GO")
        self.assertNotIn("stage10", last)

    def test_optional_stage_sanitized_status_and_reject_injected_error(self):
        def with_stage(_):
            legacy = self.collect(_)
            legacy["stage10"] = {"status": "STAGE10_UNVERIFIED_STAGED_NO_GO"}
            return legacy
        success = run_cycle(self.root, collect=with_stage,
                            write_report=self.write_report)
        self.assertEqual(success["stage10_status"], "STAGE10_UNVERIFIED_STAGED_NO_GO")
        self.assertNotIn("stage10_error_type", success)
        def forged(_):
            legacy = self.collect(_)
            legacy["stage10"] = {
                "status": "STAGE10_HOURLY_FAILED_NO_GO",
                "error_type": "DiscoveryError token=PRIVATE_VALUE",
            }
            return legacy
        refused = run_cycle(self.root, collect=forged, write_report=self.write_report)
        self.assertEqual(refused["status"], "COLLECTION_FAILED")
        receipt = (self.root / "runtime" / "last_run.json").read_text()
        self.assertNotIn("PRIVATE_VALUE", receipt)

    def test_partial_stage13_failure_is_persisted_without_false_success(self):
        def study_with_upstream_issue(root):
            legacy = self.collect(root)
            legacy["stage10"] = {
                "status": "STAGE10_HOURLY_PARTIAL_NO_GO",
                "stage13_history_status": "EXTERNAL_HISTORY_UPSTREAM_OR_METADATA_FAILED_NO_GO",
                "stage13_failure_source": "python/cpython",
                "stage13_failure_category": "FETCH_OR_RESPONSE_REJECTED",
                "stage12_review_status": "STAGE12_UNVERIFIED_REVIEW_UPDATED_NO_GO",
                "stage12_review_proposals_added": 2,
            }
            return legacy
        result = run_cycle(self.root, collect=study_with_upstream_issue,
                           write_report=self.write_report)
        self.assertEqual(result["status"], "COLLECTED_UNVERIFIED")
        self.assertEqual(result["stage10_status"], "STAGE10_HOURLY_PARTIAL_NO_GO")
        self.assertEqual(result["stage13_failure_source"], "python/cpython")
        self.assertEqual(result["stage13_failure_category"], "FETCH_OR_RESPONSE_REJECTED")
        self.assertEqual(result["stage12_review_proposals_added"], 2)
        self.assertEqual(result["stage12_review_status"],
                         "STAGE12_UNVERIFIED_REVIEW_UPDATED_NO_GO")
        self.assertNotIn("stage10_error_type", result)
        last = json.loads((self.root / "runtime" / "last_run.json").read_text())
        self.assertEqual(last["stage10_status"], "STAGE10_HOURLY_PARTIAL_NO_GO")
        self.assertEqual(last["stage12_review_proposals_added"], 2)

    def test_partial_stage13_invalid_details_rejected_without_hidden_approval(self):
        def forged(root):
            legacy = self.collect(root)
            legacy["stage10"] = {
                "status": "STAGE10_HOURLY_PARTIAL_NO_GO",
                "stage13_history_status": "EXTERNAL_HISTORY_UPSTREAM_OR_METADATA_FAILED_NO_GO",
                "stage13_failure_source": "foreign/private",
                "stage13_failure_category": "AUTO_APPROVED",
            }
            return legacy
        result = run_cycle(self.root, collect=forged,
                           write_report=self.write_report)
        self.assertEqual(result["status"], "COLLECTION_FAILED")
        self.assertNotIn("stage13_failure_source", result)
        self.assertNotIn("stage12_review_status", result)

    def test_legacy_unscheduled_mode_remains_available(self):
        a = run_cycle(self.root, collect=self.collect, write_report=self.write_report)
        b = run_cycle(self.root, collect=self.collect, write_report=self.write_report)
        self.assertEqual(a["status"], "COLLECTED_UNVERIFIED")
        self.assertEqual(b["status"], "COLLECTED_UNVERIFIED")
