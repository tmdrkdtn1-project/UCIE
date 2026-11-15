"""P10 strict owner live CLI and synthetic one-row transaction QA.

Everything mutating runs against TemporaryDirectory/UCIE only.
The D:/UCIE test performs *read-only* Windows TaskScheduler and queue proof.
"""
from __future__ import annotations

from contextlib import closing
from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
import sqlite3
from tempfile import TemporaryDirectory
import unittest

from ucie_miner import pending_queue as queue
from ucie_miner import p10_owner_single_live_rearm_v02 as m
from ucie_miner.runtime_pipeline import DEDUPES

T0 = datetime(2026, 11, 15, 12, tzinfo=timezone.utc)
ALLOWED = ("PUBLIC_METADATA_REVIEW", "UCIE_REPORT_PREPARATION")


class P10OwnerOneLiveSyntheticTests(unittest.TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory(prefix="UCIE_P10_OWNER_ONE_LIVE_SYNTH_")
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name) / "UCIE"
        (self.root / "runtime").mkdir(parents=True)
        (self.root / "runtime" / "UCIE_P10_LIVE_REARM_SYNTH_ONLY.marker").write_text(
            m.SYNTH_MARKER, encoding="ascii")
        queue.initialize_queue(self.root)
        for kind in (*ALLOWED, "PUBLIC_INCREMENTAL_MINING"):
            queue.enqueue(self.root, kind=kind, dedupe_key=DEDUPES[kind],
                          due=T0)
        with closing(m._conn(self.root, readonly=False)) as db:
            db.execute("UPDATE jobs SET status='REVIEW_REQUIRED',attempts=5,"
                       "last_reason='RETRYABLE_ERROR' "
                       "WHERE kind IN (?,?)", ALLOWED)

    def _held_row(self, kind):
        with closing(m._conn(self.root, readonly=True)) as db:
            return dict(m._row(db, kind))

    def _fp(self, kind):
        with closing(m._conn(self.root, readonly=True)) as db:
            return m._fingerprint(m._row(db, kind))

    def _apply(self, kind="PUBLIC_METADATA_REVIEW",
               token=None, job_id=None, now=T0):
        row = self._held_row(kind)
        return m._commit_once(
            self.root, kind, row["job_id"] if job_id is None else job_id,
            self._fp(kind) if token is None else token, now,
            owner_consent=m.CONSENT)

    def test_01_one_exact_nonnetwork_job_then_bounded_rollback(self):
        first = self._held_row("PUBLIC_METADATA_REVIEW")
        second = self._held_row("UCIE_REPORT_PREPARATION")
        p11 = queue.inspect_queue(self.root)["jobs"]
        receipt = self._apply()
        self.assertEqual(receipt["status"],
                         "EXACT_ONE_NONNETWORK_JOB_DELAYED_PENDING")
        self.assertEqual(receipt["scheduled_due_at"],
                         queue._stamp(T0 + timedelta(minutes=10)))
        changed = self._held_row("PUBLIC_METADATA_REVIEW")
        self.assertEqual(changed["status"], "PENDING")
        self.assertEqual(changed["attempts"], 0)
        self.assertIsNone(changed["last_reason"])
        self.assertEqual(self._held_row("UCIE_REPORT_PREPARATION"), second)
        self.assertEqual(
            [x["status"] for x in queue.inspect_queue(self.root)["jobs"]
             if x["kind"] == "PUBLIC_INCREMENTAL_MINING"], ["PENDING"])
        self.assertFalse(receipt["worker_started"])
        self.assertEqual(receipt["public_gets"], 0)
        rollback = m._rollback_once(
            self.root, receipt["operation_sha256"],
            T0 + timedelta(minutes=1), owner_consent=m.ROLLBACK_CONSENT)
        self.assertEqual(rollback["status"],
                         "EXACT_ONE_OWNER_P10_ROLLBACK_CONFIRMED")
        self.assertEqual(self._held_row("PUBLIC_METADATA_REVIEW"), first)
        with self.assertRaises((sqlite3.IntegrityError, m.OwnerLiveRearmError)):
            self._apply()  # replay preimage is forbidden even after rollback
        self.assertEqual(self._held_row("PUBLIC_METADATA_REVIEW"), first)

    def test_02_wrong_fingerprint_and_job_id_fail_without_writes(self):
        first = self._held_row("PUBLIC_METADATA_REVIEW")
        with self.assertRaises(m.OwnerLiveRearmError):
            self._apply(token="0"*64)
        with self.assertRaises(m.OwnerLiveRearmError):
            self._apply(job_id=first["job_id"]+999)
        self.assertEqual(self._held_row("PUBLIC_METADATA_REVIEW"), first)
        with closing(m._conn(self.root, readonly=True)) as db:
            self.assertIsNone(db.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
                (m.TABLE,)).fetchone())

    def test_03_only_one_active_rearm_and_rollback_deadline(self):
        first = self._apply()
        with self.assertRaises(m.OwnerLiveRearmError):
            self._apply("UCIE_REPORT_PREPARATION")
        with self.assertRaises(m.OwnerLiveRearmError):
            m._rollback_once(self.root, first["operation_sha256"],
                             T0 + timedelta(minutes=10),
                             owner_consent=m.ROLLBACK_CONSENT)
        self.assertEqual(self._held_row("PUBLIC_METADATA_REVIEW")["status"],
                         "PENDING")

    def test_04_claimed_job_may_not_rollback(self):
        first = self._apply()
        with closing(m._conn(self.root, readonly=False)) as db:
            db.execute("UPDATE jobs SET attempts=1,status='RUNNING',"
                       "lease_token='x',lease_expires_at=? "
                       "WHERE job_id=?",
                       (queue._stamp(T0+timedelta(minutes=30)),
                        first["job_id"]))
        with self.assertRaises(m.OwnerLiveRearmError):
            m._rollback_once(self.root, first["operation_sha256"],
                             T0 + timedelta(minutes=1), owner_consent=m.ROLLBACK_CONSENT)

    def test_05_kind_and_operation_fingerprint_restricted(self):
        self.assertEqual(set(m.KINDS), set(ALLOWED))
        with self.assertRaises(m.OwnerLiveRearmError):
            m._commit_once(self.root, "PUBLIC_INCREMENTAL_MINING", 3,
                           "0"*64, T0, owner_consent=m.CONSENT)
        with self.assertRaises(m.OwnerLiveRearmError):
            m._rollback_once(self.root, "abc", T0,
                             owner_consent=m.ROLLBACK_CONSENT)
        self.assertIn("Get-ScheduledTask -TaskPath '\\' -TaskName $name",
                      m.OWNER_TASK_PS)
        for denied in ("Set-ScheduledTask ", "Start-ScheduledTask ",
                       "Unregister-ScheduledTask ", "Invoke-WebRequest "):
            self.assertNotIn(denied, m.OWNER_TASK_PS)

    def test_06_missing_marker_and_wrong_consent_block_all_writes(self):
        marker = self.root / "runtime" / "UCIE_P10_LIVE_REARM_SYNTH_ONLY.marker"
        before = self._held_row("PUBLIC_METADATA_REVIEW")
        fingerprint = self._fp("PUBLIC_METADATA_REVIEW")
        marker.unlink()
        with self.assertRaises(m.OwnerLiveRearmError):
            self._apply(token=fingerprint)
        with self.assertRaises(m.OwnerLiveRearmError):
            m._rollback_once(self.root, "0"*64, T0,
                             owner_consent=m.ROLLBACK_CONSENT)
        marker.write_text(m.SYNTH_MARKER, encoding="ascii")
        with self.assertRaises(m.OwnerLiveRearmError):
            m._commit_once(self.root, "PUBLIC_METADATA_REVIEW",
                           before["job_id"], fingerprint, T0,
                           owner_consent="FORGED")
        self.assertEqual(self._held_row("PUBLIC_METADATA_REVIEW"), before)

    def test_07_one_success_then_finalize_unlocks_second_safe_kind(self):
        first = self._apply()
        with self.assertRaises(m.OwnerLiveRearmError):
            m._finalize_once(
                self.root, first["operation_sha256"], T0 + timedelta(minutes=10),
                owner_consent=m.FINALIZE_CONSENT)
        with closing(m._conn(self.root, readonly=False)) as db:
            db.execute(
                "UPDATE jobs SET status='SUCCEEDED',completed_at=? WHERE job_id=?",
                (queue._stamp(T0 + timedelta(minutes=10, seconds=5)),
                 first["job_id"]))
        done = m._finalize_once(
            self.root, first["operation_sha256"],
            T0 + timedelta(minutes=11), owner_consent=m.FINALIZE_CONSENT)
        self.assertEqual(done["status"],
                         "EXACT_ONE_P10_COMPLETION_RECEIPT_FINALIZED")
        second = self._apply("UCIE_REPORT_PREPARATION", now=T0+timedelta(minutes=11))
        self.assertEqual(second["kind"], "UCIE_REPORT_PREPARATION")
        self.assertFalse(second["auto_promoted"])

    def test_08_historical_completion_summary_valid_after_regular_rearm(self):
        first = self._apply()
        with closing(m._conn(self.root, readonly=False)) as db:
            db.execute("CREATE TABLE p10_completed(kind TEXT PRIMARY KEY,"
                       "job_id INTEGER,finished_at TEXT,final_status TEXT,"
                       "completion_count INTEGER)")
            db.execute("INSERT INTO p10_completed VALUES(?,?,?,'SUCCEEDED',1)",
                       ("PUBLIC_METADATA_REVIEW", first["job_id"],
                        queue._stamp(T0 + timedelta(minutes=11))))
            # The normal periodic scheduler can rearm the completed job again.
            db.execute("UPDATE jobs SET status='PENDING',attempts=0,"
                       "completed_at=NULL WHERE job_id=?", (first["job_id"],))
        result = m._finalize_once(
            self.root, first["operation_sha256"],
            T0 + timedelta(minutes=11), owner_consent=m.FINALIZE_CONSENT)
        self.assertEqual(result["status"],
                         "EXACT_ONE_P10_COMPLETION_RECEIPT_FINALIZED")

    @unittest.skipUnless(os.name == "nt", "UCIE exact owner Windows only")
    def test_09_owner_readonly_preview_and_task_proof(self):
        owner = Path("D:/UCIE")
        if (owner.resolve() != Path(__file__).resolve().parents[1]
                or owner.is_symlink() or not (owner / ".git").is_dir()):
            self.skipTest("exact owner checkout unavailable")
        evidence = m._attest_windows_owner(owner)
        self.assertTrue(evidence["task_verified"])
        self.assertGreaterEqual(evidence["recent_task_instances"], 1)
        snapshots = [m.preview(owner, kind) for kind in ALLOWED]
        self.assertEqual(len(snapshots), 2)
        for r in snapshots:
            self.assertEqual(r["status"],
                             "EXACT_OWNER_P10_SINGLE_JOB_PREVIEW_ONLY")
            self.assertTrue(r["held"])
            self.assertTrue(r["eligible_for_explicit_single_owner_action"])
            self.assertEqual(len(r["exact_row_fingerprint_sha256"]), 64)
            self.assertFalse(r["apply_executed"])
            self.assertFalse(r["queue_modified"])
            self.assertFalse(r["job_completed_by_scheduler_event"])
        # No sensitive row fields or identities in the receipt.
        print("UCIE_P10_OWNER_ONE_LIVE_PREVIEW=" + json.dumps(
            snapshots, ensure_ascii=True, sort_keys=True))


if __name__ == "__main__":
    unittest.main()
