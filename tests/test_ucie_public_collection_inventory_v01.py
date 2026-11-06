"""Synthetic UCIE-only public collection count/report regression tests.

No real owner runtime, scheduled tasks, GitHub API, private files or
external projects are read by this test module.
"""
from __future__ import annotations

from contextlib import closing
from datetime import datetime, timedelta, timezone
from pathlib import Path
import sqlite3
import tempfile
import unittest

from ucie_miner import public_collection_inventory_v01 as inventory

NOW = datetime(2026, 11, 5, 8, 0, 0, tzinfo=timezone.utc)


def fake_hourly(root, *, now):
    return {
        "schema": "UCIE_HOURLY_PUBLIC_LIBRARY_PROOF_V12",
        "status": "TWO_FRESH_CYCLE_RECEIPTS_OBSERVED_SCHEDULER_NOT_ATTESTED",
        "latest_finished_utc": (now - timedelta(minutes=5)).isoformat(),
        "last_completed_age_minutes": 5.0,
        "latest_new_unverified_candidates": 1,
        "two_successful_collection_receipts": True,
    }


def fake_stage10(_root):
    return {"status": "UNVERIFIED_CANDIDATE_STAGING_INSPECTED_NO_GO",
            "candidate_revisions": 21, "git_commit_revisions": 13}


def fake_stage12(_root):
    return {"status": "STAGE12_UNVERIFIED_REVIEW_INSPECTED_NO_GO",
            "review_proposals": 12}


def create_legacy(runtime):
    db = runtime / inventory.LEGACY_DB
    with closing(sqlite3.connect(db)) as conn:
        conn.execute("""CREATE TABLE candidates (
          source TEXT NOT NULL, pr_number INTEGER NOT NULL,
          public_url TEXT NOT NULL, merged_at TEXT NOT NULL,
          evidence_sha256 TEXT NOT NULL, tags_json TEXT NOT NULL,
          observed_at TEXT NOT NULL,
          status TEXT NOT NULL,
          PRIMARY KEY (source, pr_number)
        )""")
        conn.execute("""CREATE TABLE runs (
          run_id INTEGER PRIMARY KEY AUTOINCREMENT,
          at_utc TEXT NOT NULL, sources_count INTEGER NOT NULL,
          added_candidates INTEGER NOT NULL, status TEXT NOT NULL
        )""")
        for source, pr in (("python/cpython", 12), ("PowerShell/PowerShell", 23)):
            conn.execute("""INSERT INTO candidates VALUES (?,?,?,?,?,?,?,?)""", (
                source, pr, "https://github.com/" + source, NOW.isoformat(),
                "a" * 64, "[]", NOW.isoformat(),
                "UNVERIFIED_CANDIDATE_ONLY",
            ))
        conn.execute("""INSERT INTO runs (at_utc, sources_count,
                        added_candidates, status) VALUES (?,?,?,?)""", (
                            (NOW - timedelta(minutes=5)).isoformat(), 2, 1,
                            "COLLECTED_UNVERIFIED"))
        conn.commit()
    return db


class CollectionInventoryTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory(prefix="ucie-collection-inventory-")
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name) / "UCIE"
        self.root.mkdir()
        self.runtime = self.root / "runtime"
        self.runtime.mkdir()
        self.db = create_legacy(self.runtime)

    def report(self, **kwargs):
        readers = {
            "stage10_reader": fake_stage10,
            "stage12_reader": fake_stage12,
            "hourly_reader": fake_hourly,
        }
        readers.update(kwargs)
        return inventory.collection_inventory(self.root, now=NOW, **readers)

    def test_distinct_ledgers_count_not_summed(self):
        got = self.report()
        self.assertEqual(got["status"], inventory.OBSERVED)
        self.assertEqual(got["legacy_miner"]["candidates"], 2)
        self.assertEqual(got["legacy_miner"]["runs"], 1)
        self.assertEqual(got["legacy_miner"]["by_source"],
                         {"python/cpython": 1, "PowerShell/PowerShell": 1})
        self.assertEqual(got["stage10_public_candidate_staging"][
                         "candidate_revisions"], 21)
        self.assertEqual(got["stage10_public_candidate_staging"][
                         "git_commit_revisions"], 13)
        self.assertEqual(got["stage12_unverified_review"][
                         "review_proposals"], 12)
        self.assertTrue(got["totals_from_distinct_ledgers_are_not_additive"])
        self.assertFalse(got["current_windows_task_scheduler_events_verified"])
        self.assertEqual(got["public_network_requests"], 0)
        self.assertEqual(got["operating_database_writes"], 0)
        self.assertFalse(got["scheduler_changed"])

    def test_read_only_does_not_mutate_operating_sqlite(self):
        before = self.db.read_bytes()
        self.report()
        self.assertEqual(self.db.read_bytes(), before)
        with closing(sqlite3.connect(self.db)) as conn:
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM candidates")
                             .fetchone()[0], 2)
        self.assertEqual(self.db.read_bytes(), before)

    def test_absent_db_is_unknown_not_fabricated_zero(self):
        self.db.unlink()
        got = self.report()
        self.assertEqual(got["status"], inventory.NO_GO)
        self.assertIsNone(got["legacy_miner"]["candidates"])
        self.assertIsNone(got["legacy_miner"]["runs"])
        self.assertIn("LEGACY_LEDGER_NOT_AVAILABLE", got["issues"])
        self.assertIn("확인 불가", inventory.render_report_markdown(got))

    def test_symlink_db_blocked_without_follow(self):
        self.db.unlink()
        link = self.runtime / inventory.LEGACY_DB
        try:
            link.symlink_to(self.runtime / "not_allowed.sqlite3")
        except (OSError, NotImplementedError):
            self.skipTest("symlink privilege unavailable")
        got = self.report()
        self.assertEqual(got["status"], inventory.NO_GO)
        self.assertIsNone(got["legacy_miner"]["candidates"])
        self.assertEqual(got["legacy_miner"]["status"],
                         "LEGACY_LEDGER_INVALID_NO_GO")

    def test_unapproved_source_in_database_blocks_counts(self):
        with closing(sqlite3.connect(self.db)) as conn:
            conn.execute("""INSERT INTO candidates VALUES
              (?,?,?,?,?,?,?,?)""", (
                "unapproved/fork", 39, "https://example.invalid", NOW.isoformat(),
                "b" * 64, "[]", NOW.isoformat(), "UNVERIFIED_CANDIDATE_ONLY"))
            conn.commit()
        got = self.report()
        self.assertEqual(got["status"], inventory.NO_GO)
        self.assertIsNone(got["legacy_miner"]["candidates"])

    def test_invalid_status_cannot_be_counted_as_trusted(self):
        with closing(sqlite3.connect(self.db)) as conn:
            conn.execute("""UPDATE candidates SET status='APPROVED'
                         WHERE pr_number=12""")
            conn.commit()
        got = self.report()
        self.assertEqual(got["status"], inventory.NO_GO)
        self.assertEqual(got["legacy_miner"]["status"],
                         "LEGACY_LEDGER_INVALID_NO_GO")

    def test_bad_schema_cannot_claim_count(self):
        with closing(sqlite3.connect(self.db)) as conn:
            conn.execute("ALTER TABLE candidates ADD COLUMN injected TEXT")
            conn.commit()
        got = self.report()
        self.assertEqual(got["status"], inventory.NO_GO)
        self.assertIsNone(got["legacy_miner"]["candidates"])

    def test_missing_stage10_ledger_does_not_disguise_as_zero(self):
        def unavailable(_root):
            raise OSError("synthetic ledger unreadable")
        got = self.report(stage10_reader=unavailable)
        self.assertEqual(got["status"], inventory.NO_GO)
        self.assertIsNone(got["stage10_public_candidate_staging"][
                          "candidate_revisions"])
        self.assertIn("STAGE10_LEDGER_INVALID", got["issues"])

    def test_stale_receipt_no_scheduler_success(self):
        def stale(_root, *, now):
            data = fake_hourly(_root, now=now)
            data["status"] = "HOURLY_CYCLE_ACTIVITY_NOT_PROVEN_NO_GO"
            return data
        got = self.report(hourly_reader=stale)
        self.assertEqual(got["status"], inventory.NO_GO)
        self.assertIn("HOURLY_RECENT_ACTIVITY_UNPROVEN", got["issues"])
        self.assertFalse(got["current_windows_task_scheduler_events_verified"])

    def test_missing_receipts_is_no_go_not_success(self):
        got = inventory.collection_inventory(self.root, now=NOW,
                                             stage10_reader=fake_stage10,
                                             stage12_reader=fake_stage12)
        self.assertEqual(got["status"], inventory.NO_GO)
        self.assertEqual(got["recent_hourly_activity"]["status"],
                         "HOURLY_RECEIPTS_UNAVAILABLE_NO_GO")

    def test_root_other_project_rejected(self):
        other = self.root.parent / "other_project"
        other.mkdir()
        (other / "runtime").mkdir()
        with self.assertRaises(inventory.CollectionInventoryError):
            inventory.collection_inventory(other, now=NOW)

    def test_markdown_truthfully_separates_ledger_and_scheduler(self):
        content = inventory.render_report_markdown(self.report())
        self.assertIn("기본 공개 PR 후보: 2건", content)
        self.assertIn("Stage10 미검증 PR 개정: 21건", content)
        self.assertIn("Stage12 별도 검토 제안: 12건", content)
        self.assertIn("Windows TaskScheduler 실이벤트 검증: 별도 확인 필요", content)
        self.assertIn("합산하지 않습니다", content)


if __name__ == "__main__":
    unittest.main()
