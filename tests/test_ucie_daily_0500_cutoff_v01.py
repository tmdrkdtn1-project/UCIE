"""UCIE daily report 05 KST cut-off regression; synthetic DB or owner read-only."""
from __future__ import annotations

from contextlib import closing
from datetime import date
from hashlib import sha256
import json
import os
from pathlib import Path
import sqlite3
import tempfile
import unittest

from ucie_miner.daily_0500_cutoff_v01 import (
    DailyCutoffError, SCHEMA, cutoff_window, inspect_snapshot,
)


class DailyReportCutoffTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="UCIE_DAILY_TEST_")
        self.root = Path(self.temp.name) / "UCIE"
        (self.root / ".git").mkdir(parents=True)
        (self.root / "runtime").mkdir()
        self.path = self.root / "runtime" / "public_miner.sqlite3"
        with closing(sqlite3.connect(self.path)) as db, db:
            db.execute("CREATE TABLE candidates (source TEXT, observed_at TEXT, status TEXT)")
            db.execute("CREATE TABLE runs (at_utc TEXT, status TEXT)")
            db.executemany("INSERT INTO candidates VALUES (?,?,?)", [
                ("python/cpython", "2026-11-04T19:59:59+00:00", "UNVERIFIED_CANDIDATE_ONLY"),
                ("python/cpython", "2026-11-05T05:00:00+00:00", "UNVERIFIED_CANDIDATE_ONLY"),
                ("PowerShell/PowerShell", "2026-11-05T19:59:59+00:00", "UNVERIFIED_CANDIDATE_ONLY"),
                ("PowerShell/PowerShell", "2026-11-05T20:00:00+00:00", "UNVERIFIED_CANDIDATE_ONLY"),
            ])
            db.executemany("INSERT INTO runs VALUES (?,?)", [
                ("2026-11-05T19:59:59+00:00", "COLLECTED_UNVERIFIED"),
                ("2026-11-05T20:00:00+00:00", "COLLECTED_UNVERIFIED"),
            ])

    def tearDown(self):
        self.temp.cleanup()

    def test_0500_boundary_strictly_excludes_new_day_events(self):
        result = inspect_snapshot(self.root, date(2026, 11, 6))
        self.assertEqual(result["schema"], SCHEMA)
        self.assertEqual(result["window_start_utc_inclusive"],
                         "2026-11-04T20:00:00+00:00")
        self.assertEqual(result["window_end_utc_exclusive"],
                         "2026-11-05T20:00:00+00:00")
        self.assertEqual(result["candidates_all_time_as_of_cutoff"], 3)
        self.assertEqual(result["new_candidates_in_window"], 2)
        self.assertEqual(result["cycle_runs_in_window"], 1)
        self.assertEqual(result["legacy_source_counts"],
                         {"python/cpython": 2, "PowerShell/PowerShell": 1})
        self.assertFalse(result["report_sent"])
        self.assertFalse(result["delivery_receipt_verified"])

    def test_no_new_candidates_still_requires_a_report(self):
        result = inspect_snapshot(self.root, date(2026, 11, 8))
        self.assertEqual(result["new_candidates_in_window"], 0)
        self.assertEqual(result["candidates_all_time_as_of_cutoff"], 4)
        self.assertEqual(result["status_if_no_changes"], "REPORT_STILL_REQUIRED")
        self.assertFalse(result["report_sent"])

    def test_snapshot_never_writes_operating_or_synthetic_database(self):
        before = sha256(self.path.read_bytes()).hexdigest()
        first = inspect_snapshot(self.root, date(2026, 11, 6))
        second = inspect_snapshot(self.root, date(2026, 11, 6))
        self.assertEqual(first, second)
        self.assertEqual(sha256(self.path.read_bytes()).hexdigest(), before)
        self.assertEqual(first["owner_operating_database_writes"], 0)
        self.assertFalse(first["scheduled_task_changed"])
        self.assertFalse(first["rule_auto_promotion"])
        self.assertFalse((self.root / "runtime" / "reports").exists())

    def test_bad_source_and_approved_row_fail_closed(self):
        with closing(sqlite3.connect(self.path)) as db, db:
            db.execute("INSERT INTO candidates VALUES (?,?,?)", (
                "unapproved/repo", "2026-11-05T10:00:00+00:00",
                "UNVERIFIED_CANDIDATE_ONLY"))
        with self.assertRaises(DailyCutoffError):
            inspect_snapshot(self.root, date(2026, 11, 6))
        with closing(sqlite3.connect(self.path)) as db, db:
            db.execute("DELETE FROM candidates WHERE source='unapproved/repo'")
            db.execute("INSERT INTO candidates VALUES (?,?,?)", (
                "python/cpython", "2026-11-05T10:00:00+00:00", "APPROVED"))
        with self.assertRaises(DailyCutoffError):
            inspect_snapshot(self.root, date(2026, 11, 6))

    def test_rejects_other_root_or_missing_or_symlinked_db(self):
        with self.assertRaises(DailyCutoffError):
            inspect_snapshot(Path(self.temp.name), date(2026, 11, 6))
        self.path.unlink()
        with self.assertRaises(DailyCutoffError):
            inspect_snapshot(self.root, date(2026, 11, 6))

    def test_date_must_be_a_date_not_datetime_or_string(self):
        for value in ("2026-11-06", None, True):
            with self.subTest(value=value), self.assertRaises(DailyCutoffError):
                cutoff_window(value)


if __name__ == "__main__":
    unittest.main()
