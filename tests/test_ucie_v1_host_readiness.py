"""UCIE-owned host readiness tests. Disposable UCIE root, never a real host DB."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from hashlib import sha256
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest

from ucie_miner.v1_host_readiness import (
    SCHEMA, HostAcceptanceError, _miner, observe_ucie_host,
)


class UCIEV1HostReadinessTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name) / "UCIE"
        self.runtime = self.root / "runtime"
        self.runtime.mkdir(parents=True)
        self.now = datetime(2026, 10, 30, 0, 0, tzinfo=timezone.utc)

    def _miner_db(self, *, age_minutes: int = 30, state: str =
                  "UNVERIFIED_CANDIDATE_ONLY", source: str = "python/cpython"):
        db = self.runtime / "public_miner.sqlite3"
        with sqlite3.connect(db) as c:
            c.execute("CREATE TABLE candidates("
                      "source TEXT,pr_number INTEGER,public_url TEXT,"
                      "merged_at TEXT,evidence_sha256 TEXT,tags_json TEXT,"
                      "observed_at TEXT,status TEXT)")
            c.execute("CREATE TABLE runs("
                      "run_id INTEGER PRIMARY KEY,at_utc TEXT,"
                      "sources_count INTEGER,added_candidates INTEGER,status TEXT)")
            c.execute("INSERT INTO candidates VALUES(?,?,?,?,?,?,?,?)", (
                source, 12345, "https://github.com/python/cpython/pull/12345",
                "2026-10-29T11:00:00+00:00", "a" * 64, "[]",
                "2026-10-29T11:00:00+00:00", state))
            observed = (self.now - timedelta(minutes=age_minutes)).isoformat()
            c.execute("INSERT INTO runs VALUES(1,?,2,1,?)",
                      (observed, "COLLECTED_UNVERIFIED"))
        (self.runtime / "last_run.json").write_text(
            json.dumps({
                "schema": "UCIE_MINER_CYCLE_V1",
                "status": "COLLECTED_UNVERIFIED",
                "finished_utc": observed,
                "production_approved": False,
                "verification_pass": 0,
                "consecutive_failures": 0,
            }), encoding="utf-8")
        return db

    def test_missing_db_is_never_a_pass_and_creates_nothing(self):
        pre = set(p.name for p in self.runtime.iterdir())
        got = observe_ucie_host(self.root, now=self.now)
        self.assertEqual(got["schema"], SCHEMA)
        self.assertEqual(got["status"], "UCIE_V1_LOCAL_OBSERVATIONS_NO_GO")
        self.assertEqual(got["collector"]["status"],
                         "MINER_OPERATING_DB_NOT_FOUND_NO_GO")
        self.assertIn("MINER_OPERATING_DB_UNVERIFIED", got["blockers"])
        self.assertEqual(set(p.name for p in self.runtime.iterdir()), pre)
        self.assertFalse(got["real_host_v1_accepted"])
        self.assertEqual(got["network_requests_this_command"], 0)
        self.assertEqual(got["scheduler_actions_this_command"], 0)
        self.assertEqual(got["rule_promotion_actions_this_command"], 0)

    def test_fresh_genuine_sqlite_snapshot_stays_unverified(self):
        db = self._miner_db()
        original = sha256(db.read_bytes()).hexdigest()
        miner = _miner(self.runtime, self.now)
        self.assertEqual(miner["database_integrity"], "ok")
        self.assertEqual(miner["candidate_count"], 1)
        self.assertEqual(miner["run_count"], 1)
        self.assertEqual(miner["last_run_freshness"], "FRESH_WITHIN_THREE_HOURS")
        self.assertEqual(miner["last_stored_run_age_seconds"], 1800)
        self.assertEqual(miner["invalid_candidate_states"], 0)
        self.assertEqual(miner["foreign_sources"], 0)
        self.assertFalse(miner["continuous_hourly_execution_verified"])
        self.assertFalse(miner["windows_scheduled_task_verified"])
        self.assertEqual(sha256(db.read_bytes()).hexdigest(), original)
        report = observe_ucie_host(self.root, now=self.now)
        self.assertEqual(report["collector"]["run_count"], 1)
        self.assertEqual(report["status"], "UCIE_V1_LOCAL_OBSERVATIONS_NO_GO")
        self.assertIn("WINDOWS_SCHEDULED_TASK_RUN_RESULT_NOT_INSPECTED",
                      report["blockers"])
        self.assertIn("APPROVED_GENERIC_PACKAGE_EXPORT_NOT_EVIDENCED",
                      report["blockers"])
        self.assertFalse(report["real_host_v1_accepted"])
        self.assertEqual(sha256(db.read_bytes()).hexdigest(), original)

    def test_recent_partial_cycle_does_not_look_healthy(self):
        self._miner_db()
        file = self.runtime / "last_run.json"
        receipt = json.loads(file.read_text(encoding="utf-8"))
        receipt["status"] = "COLLECTED_UNVERIFIED_PARTIAL_NO_GO"
        file.write_text(json.dumps(receipt), encoding="utf-8")
        observed = _miner(self.runtime, self.now)
        self.assertFalse(observed["last_observed_complete_collection"])
        self.assertEqual(
            observed["last_run_freshness"],
            "RECENT_BUT_COLLECTION_INCOMPLETE_OR_UNRECEIPTED_NO_GO")
        report = observe_ucie_host(self.root, now=self.now)
        self.assertIn("MINER_LAST_RUN_NOT_FRESH", report["blockers"])
        self.assertFalse(report["real_host_v1_accepted"])

    def test_stale_cycle_and_receipt_are_not_silent_operating_pass(self):
        self._miner_db(age_minutes=300)
        report = observe_ucie_host(self.root, now=self.now)
        self.assertEqual(report["collector"]["last_run_freshness"],
                         "STALE_OVER_THREE_HOURS_NO_GO")
        self.assertIn("MINER_LAST_RUN_NOT_FRESH", report["blockers"])
        self.assertFalse(report["real_host_v1_accepted"])

    def test_unapproved_or_foreign_db_candidate_fails_closed(self):
        for bad in (("APPROVED", "python/cpython"),
                    ("UNVERIFIED_CANDIDATE_ONLY", "other/foreign")):
            with self.subTest(bad=bad):
                target = self.runtime / "public_miner.sqlite3"
                receipt = self.runtime / "last_run.json"
                target.unlink(missing_ok=True)
                receipt.unlink(missing_ok=True)
                self._miner_db(state=bad[0], source=bad[1])
                with self.assertRaises(HostAcceptanceError):
                    _miner(self.runtime, self.now)
                report = observe_ucie_host(self.root, now=self.now)
                self.assertEqual(
                    report["collector"]["status"],
                    "COMPONENT_READONLY_CHECK_FAILED_NO_GO")
                self.assertFalse(report["real_host_v1_accepted"])

    def test_corrupt_last_receipt_and_wrong_root_fail_closed(self):
        self._miner_db()
        (self.runtime / "last_run.json").write_text(
            '{"schema":"UCIE_MINER_CYCLE_V1","status":"COLLECTED_UNVERIFIED",'
            '"production_approved":true}', encoding="utf-8")
        report = observe_ucie_host(self.root, now=self.now)
        self.assertEqual(
            report["collector"]["status"],
            "COMPONENT_READONLY_CHECK_FAILED_NO_GO")
        with self.assertRaises(HostAcceptanceError):
            observe_ucie_host(self.root.parent)
        with self.assertRaises(HostAcceptanceError):
            observe_ucie_host(self.root, owner_public_trust=self.root / "key")
        with self.assertRaises(HostAcceptanceError):
            observe_ucie_host(self.root, serial5_pack=self.root / "fifth.zip")


if __name__ == "__main__":
    unittest.main()
