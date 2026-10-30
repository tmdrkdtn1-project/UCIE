"""Offline P10 -> P11 -> P8 full-loop acceptance on an isolated UCIE root.

This exercises real first-party queue scheduling, source-bound metadata parsing,
P11 synthesis, atomic improvement-review receipts and deduped rearm. Only the
public feed response and unrelated five P10 handlers are synthetic; no live
host worker, public API, operator settings or production DB is touched.
"""
from __future__ import annotations

from contextlib import closing
from datetime import datetime, timedelta, timezone
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

from ucie_miner import pending_queue as queue
from ucie_miner import p11_closed_loop as p11
from ucie_miner import runtime_pipeline as pipeline
from ucie_miner.public_discovery import SOURCES, public_feed_url

T0 = datetime(2026, 10, 30, 9, tzinfo=timezone.utc)


def _approved_public_item(source: str, number: int) -> dict:
    return {
        "number": number,
        "title": "fix regression in public python test suite",
        "merged_at": "2026-10-29T02:00:00Z",
        "html_url": f"https://github.com/{source}/pull/{number}",
        "merge_commit_sha": f"{number:040x}",
        "base": {"repo": {"full_name": source}},
    }


class P8EndToEndRecurringAcceptanceTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name) / "UCIE"
        (self.root / "runtime").mkdir(parents=True)
        pipeline.initialize(self.root)
        p11.activate(self.root)
        self.source = SOURCES[0]
        self.fetched = []
        self.worker_kinds = []

    def _feed(self, url: str):
        self.assertEqual(url, public_feed_url(self.source))
        self.fetched.append(url)
        return [_approved_public_item(self.source, 56399)]

    def _dispatch(self, when: datetime) -> dict:
        original = p11.collect_one

        def _one_worker(_root: Path, leased: dict):
            kind = leased["kind"]
            self.worker_kinds.append(kind)
            if kind == "PUBLIC_INCREMENTAL_MINING":
                with patch("ucie_miner.p11_closed_loop.collect_one",
                           side_effect=lambda root: original(
                               root, fetch=self._feed, now=when)):
                    ok = pipeline._safe_handler(self.root, kind)
            elif kind == "EXPERIENCE_CLOSED_LOOP":
                ok = pipeline._safe_handler(self.root, kind)
            else:
                # Scope this acceptance to P10 scheduling and P11:
                # other five handlers have separate real offline tests.
                ok = True
            self.assertTrue(ok, kind)
            result = queue.finish_job(
                self.root, job_id=leased["job_id"],
                lease_token=leased["lease_token"],
                outcome="SUCCEEDED", now=when)
            self.assertEqual(result["status"], "SUCCEEDED")

        return pipeline.dispatch_tick(
            self.root, now=when, spawn=_one_worker)

    def test_new_public_evidence_reaches_atomic_feedback_once_through_real_queue(self):
        initial = p11.status(self.root)
        self.assertEqual(initial["first_party_experiences"], 0)
        self.assertEqual(initial["improvement_review_record_count"], 0)

        with patch("urllib.request.urlopen",
                   side_effect=AssertionError("network must not be used")):
            for offset in (0, 1, 2):
                tick = self._dispatch(T0 + timedelta(seconds=offset))
                self.assertEqual(tick["status"],
                                 "P10_NONBLOCKING_TICK_DISPATCHED")
                self.assertEqual(tick["launch_failures_pending"], 0)

            # Repeated P10 jobs are real queue rows, not duplicate lead trials.
            first = p11.status(self.root)
            self.assertEqual(first["unverified_leads"], 1)
            self.assertEqual(first["awaiting_synthetic_experiment"], 0)
            self.assertEqual(first["first_party_experiences"], 1)
            self.assertEqual(first["improvement_review_record_count"], 1)
            self.assertEqual(first["first_party_retest_proposals_not_adopted"], 1)
            self.assertEqual(first["production_improvements_auto_applied"], 0)
            self.assertEqual(len(self.fetched), 1)
            self.assertEqual(len(self.worker_kinds), 7)
            self.assertEqual(len(set(self.worker_kinds)), 7)

            with closing(sqlite3.connect(
                    self.root / "runtime" / p11.DB_NAME)) as db:
                receipt = db.execute(
                    "SELECT e.receipt_sha256,r.receipt_sha256,r.decision,"
                    "l.reviewed FROM experience AS e "
                    "JOIN improvement_review AS r USING(source,pr_number) "
                    "JOIN leads AS l USING(source,pr_number)").fetchone()
            self.assertIsNotNone(receipt)
            self.assertEqual(receipt[0], receipt[1])
            self.assertEqual(receipt[2],
                             "FIRST_PARTY_RETEST_PROPOSAL_NOT_ADOPTED")
            self.assertEqual(receipt[3], 1)

            # A subsequent real dispatcher recurrence must not invent a
            # new experience or rewrite an old P8 improvement receipt.
            recurring = self._dispatch(T0 + timedelta(minutes=1, seconds=5))
            self.assertGreaterEqual(recurring["rearmed_successful_jobs"], 2)
            later = p11.status(self.root)
            self.assertEqual(later["first_party_experiences"], 1)
            self.assertEqual(later["improvement_review_record_count"], 1)
            self.assertEqual(len(self.fetched), 1)

        with closing(sqlite3.connect(
                self.root / "runtime" /
                "ucie_internal_pending_queue_v1.sqlite3")) as db:
            count = db.execute(
                "SELECT SUM(completion_count) FROM p10_completed").fetchone()[0]
        self.assertGreaterEqual(count, 2)
        self.assertFalse(later["auto_promoted"])

    def test_no_public_lead_is_successful_idle_not_fake_learning(self):
        def empty(url):
            self.assertEqual(url, public_feed_url(self.source))
            self.fetched.append(url)
            return []

        self._feed = empty
        with patch("urllib.request.urlopen",
                   side_effect=AssertionError("network must not be used")):
            for offset in (0, 1, 2):
                self._dispatch(T0 + timedelta(seconds=offset))
        snapshot = p11.status(self.root)
        self.assertEqual(len(self.fetched), 1)
        self.assertEqual(snapshot["total_successful_public_gets"], 1)
        self.assertEqual(snapshot["first_party_experiences"], 0)
        self.assertEqual(snapshot["improvement_review_record_count"], 0)
        self.assertEqual(snapshot["awaiting_synthetic_experiment"], 0)
        self.assertEqual(queue.inspect_queue(self.root)["counts"]["SUCCEEDED"], 7)


if __name__ == "__main__":
    unittest.main()
