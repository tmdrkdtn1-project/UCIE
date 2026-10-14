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

    def test_legacy_unscheduled_mode_remains_available(self):
        a = run_cycle(self.root, collect=self.collect, write_report=self.write_report)
        b = run_cycle(self.root, collect=self.collect, write_report=self.write_report)
        self.assertEqual(a["status"], "COLLECTED_UNVERIFIED")
        self.assertEqual(b["status"], "COLLECTED_UNVERIFIED")
