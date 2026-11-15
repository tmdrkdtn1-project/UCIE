"""UCIE-only first-party synthetic P10 one-job rearm and rollback tests.

Only disposable TemporaryDirectory/UCIE roots are mutated. The actual
D:/UCIE Windows test reads preview and never calls apply or rollback.
"""
from __future__ import annotations

from contextlib import closing
from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
import sqlite3

from ucie_miner import pending_queue as q
from ucie_miner.runtime_pipeline import DEDUPES
from ucie_miner.p10_owner_rearm_v01 import (
    OwnerRearmError, SAFE_KINDS, TABLE, apply_one, preview, rollback_one,
)

NOW = datetime(2026, 11, 15, 0, 0, tzinfo=timezone.utc)


class P10OwnerOneRowSyntheticTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory(prefix="UCIE_P10_OWNER_SYNTH_")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / "UCIE"
        (self.root / "runtime").mkdir(parents=True)
        q.initialize_queue(self.root)
        self.kind = "PUBLIC_METADATA_REVIEW"
        self.job_id = q.enqueue(
            self.root, kind=self.kind, dedupe_key=DEDUPES[self.kind],
            due=NOW)["job_id"]
        with closing(q._conn(self.root)) as db:
            db.execute(
                "UPDATE jobs SET status='REVIEW_REQUIRED',attempts=5,"
                "last_reason='RETRYABLE_ERROR' WHERE job_id=?",
                (self.job_id,))

    def _p(self):
        return preview(self.root, kind=self.kind)

    def _a(self, **change):
        kwargs = dict(
            kind=self.kind,
            expected_sha256=self._p()["exact_row_fingerprint_sha256"],
            owner_authorized=True,
            task_evidence_independently_verified=True,
            now=NOW)
        kwargs.update(change)
        return apply_one(self.root, **kwargs)

    def _table_exists(self):
        with closing(q._conn(self.root)) as db:
            return db.execute(
                "SELECT COUNT(*) FROM sqlite_master WHERE "
                "type='table' AND name=?", (TABLE,)).fetchone()[0]

    def test_01_preview_does_not_create_receipts(self):
        p = self._p()
        self.assertTrue(p["held"])
        self.assertEqual(p["attempts"], 5)
        self.assertEqual(p["db_writes"], 0)
        self.assertTrue(p["candidate_for_independent_owner_review"])
        self.assertFalse(p["actual_rearm_authorized"])
        self.assertEqual(self._table_exists(), 0)

    def test_02_no_p11_network_rearm(self):
        self.assertNotIn("PUBLIC_INCREMENTAL_MINING", SAFE_KINDS)
        with self.assertRaises(OwnerRearmError):
            preview(self.root, kind="PUBLIC_INCREMENTAL_MINING")
        with self.assertRaises(OwnerRearmError):
            apply_one(self.root, kind="PUBLIC_INCREMENTAL_MINING",
                      expected_sha256="a" * 64, owner_authorized=True,
                      task_evidence_independently_verified=True, now=NOW)
        self.assertEqual(self._table_exists(), 0)

    def test_03_wrong_fingerprint_fails(self):
        with self.assertRaises(OwnerRearmError):
            self._a(expected_sha256="0" * 64)
        self.assertTrue(self._p()["held"])
        self.assertEqual(self._table_exists(), 0)

    def test_04_independent_authorizations_required(self):
        for name in ("owner_authorized", "task_evidence_independently_verified"):
            with self.subTest(name=name):
                with self.assertRaises(OwnerRearmError):
                    self._a(**{name: False})
        self.assertEqual(self._table_exists(), 0)

    def test_05_single_pending_delayed_with_receipt(self):
        out = self._a()
        self.assertEqual(out["status"], "ONE_P10_PENDING_DELAYED_OWNER_ACTION")
        self.assertEqual(
            out["scheduled_due_at"], q._stamp(NOW + timedelta(minutes=10)))
        self.assertEqual(self._p()["attempts"], 0)
        self.assertEqual(self._p()["active_rearms"], 1)
        self.assertFalse(out["worker_started"])
        with closing(q._conn(self.root)) as db:
            self.assertEqual(
                db.execute("SELECT COUNT(*) FROM " + TABLE).fetchone()[0], 1)

    def test_06_rollback_restores_exact_sha(self):
        before = self._p()["exact_row_fingerprint_sha256"]
        out = self._a()
        result = rollback_one(
            self.root, operation_sha256=out["operation_sha256"],
            owner_authorized=True, task_evidence_independently_verified=True,
            now=NOW + timedelta(seconds=30))
        self.assertEqual(result["status"], "ONE_P10_OWNER_ROLLBACK_OBSERVED")
        self.assertEqual(self._p()["exact_row_fingerprint_sha256"], before)
        self.assertEqual(self._p()["active_rearms"], 0)

    def test_07_no_rollback_after_worker_claim(self):
        out = self._a()
        claim = q.claim_ready(
            self.root, now=NOW + timedelta(minutes=11), limit=1)
        self.assertEqual(claim["claimed_count"], 1)
        with self.assertRaises(OwnerRearmError):
            rollback_one(
                self.root, operation_sha256=out["operation_sha256"],
                owner_authorized=True, task_evidence_independently_verified=True,
                now=NOW + timedelta(minutes=11))
        self.assertEqual(self._p()["running_jobs"], 1)

    def test_08_no_rearm_when_another_job_is_running(self):
        kind = "UCIE_QA_REVIEW"
        q.enqueue(self.root, kind=kind, dedupe_key=DEDUPES[kind], due=NOW)
        with closing(q._conn(self.root)) as db:
            db.execute(
                "UPDATE jobs SET status='RUNNING',attempts=1 WHERE kind=?",
                (kind,))
        with self.assertRaises(OwnerRearmError):
            self._a()
        self.assertTrue(self._p()["held"])

    def test_09_deadline_blocks_rollback_even_without_claim(self):
        out = self._a()
        with self.assertRaises(OwnerRearmError):
            rollback_one(
                self.root, operation_sha256=out["operation_sha256"],
                owner_authorized=True, task_evidence_independently_verified=True,
                now=NOW + timedelta(minutes=11))
        self.assertFalse(self._p()["held"])

    def test_10_replay_after_rollback_is_rejected(self):
        original = self._p()["exact_row_fingerprint_sha256"]
        out = self._a()
        rollback_one(
            self.root, operation_sha256=out["operation_sha256"],
            owner_authorized=True, task_evidence_independently_verified=True,
            now=NOW + timedelta(seconds=5))
        with self.assertRaises(sqlite3.IntegrityError):
            apply_one(
                self.root, kind=self.kind, expected_sha256=original,
                owner_authorized=True,
                task_evidence_independently_verified=True, now=NOW)
        self.assertEqual(self._p()["exact_row_fingerprint_sha256"], original)

    def test_11_unknown_operation_rejected(self):
        with self.assertRaises(OwnerRearmError):
            rollback_one(
                self.root, operation_sha256="0" * 64,
                owner_authorized=True, task_evidence_independently_verified=True,
                now=NOW)

    def test_12_limited_exact_no_network_kinds(self):
        self.assertEqual(SAFE_KINDS, frozenset((
            "PUBLIC_METADATA_REVIEW", "UCIE_REPORT_PREPARATION")))

    def test_13_exhausted_state_required(self):
        with closing(q._conn(self.root)) as db:
            db.execute("UPDATE jobs SET attempts=4 WHERE job_id=?",
                       (self.job_id,))
        self.assertFalse(self._p()["candidate_for_independent_owner_review"])
        with self.assertRaises(OwnerRearmError):
            self._a()

    def test_14_no_simultaneous_second_rearm(self):
        other = "UCIE_REPORT_PREPARATION"
        other_id = q.enqueue(
            self.root, kind=other, dedupe_key=DEDUPES[other], due=NOW)["job_id"]
        with closing(q._conn(self.root)) as db:
            db.execute(
                "UPDATE jobs SET status='REVIEW_REQUIRED',attempts=5,"
                "last_reason='RETRYABLE_ERROR' WHERE job_id=?", (other_id,))
        other_sha = preview(
            self.root, kind=other)["exact_row_fingerprint_sha256"]
        self._a()
        with self.assertRaises(OwnerRearmError):
            apply_one(
                self.root, kind=other, expected_sha256=other_sha,
                owner_authorized=True,
                task_evidence_independently_verified=True, now=NOW)
        self.assertTrue(preview(self.root, kind=other)["held"])


class P10OwnerRealReadOnlyPreview(unittest.TestCase):
    @unittest.skipUnless(os.name == "nt", "real owner Windows only")
    def test_15_owner_previews_but_cannot_apply_via_cli(self):
        root = Path(__file__).resolve().parents[1]
        if (root.resolve() != Path("D:/UCIE").resolve()
                or root.is_symlink() or not (root / ".git").is_dir()):
            self.skipTest("exact UCIE Windows owner checkout not mounted")
        report = [preview(root, kind=k) for k in sorted(SAFE_KINDS)]
        print("UCIE_P10_OWNER_REARM_PREVIEW=" + json.dumps(
            report, sort_keys=True, ensure_ascii=True))
        self.assertEqual(len(report), 2)
        self.assertTrue(all(r["db_writes"] == 0 for r in report))
        self.assertTrue(all(not r["actual_rearm_authorized"] for r in report))


if __name__ == "__main__":
    unittest.main()
