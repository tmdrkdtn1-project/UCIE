"""P9 real integration: P10 existing 15-minute worker -> P8 review -> P9 receipt.

No new task kind or scheduler, no network, no real operating UCIE DB.
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
from ucie_miner import runtime_pipeline as pipeline
from ucie_miner import p11_closed_loop as p11
from ucie_miner import p9_auto_retest as auto
from ucie_miner import p11_retest as retest
from ucie_miner.capability_trials import evaluate_ucie_owned_recipe
from ucie_miner.public_discovery import SOURCES, public_feed_url

T0 = datetime(2026, 10, 30, 9, tzinfo=timezone.utc)


def approved_item(source, number):
    return {
        "number": number,
        "title": "Fix regression in public socket test",
        "merged_at": "2026-10-29T06:00:00Z",
        "html_url": f"https://github.com/{source}/pull/{number}",
        "merge_commit_sha": f"{number:040x}",
        "base": {"repo": {"full_name": source}},
    }


class P9P10ExistingWorkerAutonomousRetestTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name) / "UCIE"
        (self.root / "runtime").mkdir(parents=True)
        pipeline.initialize(self.root)
        self.queue_db = self.root / "runtime" / queue.DB_NAME
        self.p11_db = self.root / "runtime" / p11.DB_NAME

    def records(self):
        with closing(sqlite3.connect(self.queue_db)) as db:
            has_table = db.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' "
                "AND name='p9_retest_receipts'").fetchone()
            if has_table is None:
                return []
            return db.execute(
                "SELECT source,pr_number,original_receipt_sha256,"
                "retest_receipt_sha256,decision FROM p9_retest_receipts "
                "ORDER BY pr_number").fetchall()

    def stage_learn(self, *, source=SOURCES[0], numbers=(100110,)):
        if not p11.enabled(self.root):
            p11.activate(self.root)
        def feed(url):
            self.assertEqual(url, public_feed_url(source))
            return [approved_item(source, number) for number in numbers]
        when = T0 if source == SOURCES[0] else T0 + timedelta(minutes=5)
        out = p11.collect_one(self.root, fetch=feed, now=when)
        self.assertEqual(out["new_unverified_leads"], len(numbers))
        return [
            p11.learn_one(self.root, now=when + timedelta(seconds=i + 1))
            for i in range(len(numbers))
        ]

    def test_existing_experiment_worker_is_silent_when_no_p11_review(self):
        self.assertEqual(len(pipeline.PERIODS), 7)
        self.assertEqual(len(queue.KINDS), 7)
        self.assertTrue(pipeline._safe_handler(
            self.root, "UCIE_FIRST_PARTY_EXPERIMENT"))
        self.assertFalse(self.p11_db.exists())
        self.assertEqual(self.records(), [])
        p11.activate(self.root)
        self.assertTrue(pipeline._safe_handler(
            self.root, "UCIE_FIRST_PARTY_EXPERIMENT"))
        self.assertEqual(self.records(), [])
        self.assertEqual(p11.status(self.root)["improvement_review_record_count"], 0)

    def test_new_p8_lead_triggers_one_p9_receipt_then_idles_without_duplicate(self):
        learned = self.stage_learn()
        self.assertEqual(learned[0]["improvement_review_records_written"], 1)
        before = self.p11_db.read_bytes()
        self.assertEqual(self.records(), [])
        with patch("urllib.request.urlopen",
                   side_effect=AssertionError("no network GET in P9 worker")):
            self.assertTrue(pipeline._safe_handler(
                self.root, "UCIE_FIRST_PARTY_EXPERIMENT"))
        self.assertEqual(self.p11_db.read_bytes(), before)
        rows = self.records()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0][:2], (SOURCES[0], 100110))
        self.assertEqual(rows[0][2], learned[0]["experiment_receipt_sha256"])
        self.assertEqual(len(rows[0][3]), 64)
        self.assertEqual(rows[0][4], "FIRST_PARTY_RETEST_PASS_MANUAL_REVIEW_ONLY")
        self.assertEqual(p11.status(self.root)["production_improvements_auto_applied"], 0)
        self.assertTrue(pipeline._safe_handler(
            self.root, "UCIE_FIRST_PARTY_EXPERIMENT"))
        self.assertEqual(self.records(), rows)
        self.assertEqual(self.p11_db.read_bytes(), before)

    def test_multiple_new_reviews_processed_one_per_existing_rearmed_experiment(self):
        self.stage_learn(numbers=(100110, 100111))
        self.assertEqual(len(self.records()), 0)
        first = auto.run_one(self.root)
        self.assertEqual(first["status"], auto.RECORDED)
        self.assertEqual(first["retest_receipts_written"], 1)
        second = auto.run_one(self.root)
        self.assertEqual(second["status"], auto.RECORDED)
        third = auto.run_one(self.root)
        self.assertEqual(third["status"], auto.NO_WORK)
        self.assertEqual(third["retest_receipts_written"], 0)
        self.assertEqual(len(self.records()), 2)
        self.assertEqual({r[1] for r in self.records()}, {100110, 100111})

    def test_corrupted_original_review_after_receipt_fails_closed(self):
        self.stage_learn()
        self.assertEqual(auto.run_one(self.root)["status"], auto.RECORDED)
        stored = self.records()
        with closing(sqlite3.connect(self.p11_db)) as db:
            db.execute(
                "UPDATE improvement_review SET receipt_sha256=?",
                ("f" * 64,))
            db.commit()
        with self.assertRaises(auto.P9AutoRetestError):
            auto.run_one(self.root)
        self.assertEqual(self.records(), stored)

    def test_untrusted_retest_claim_rejected_without_new_p9_table(self):
        self.stage_learn()
        valid = retest.retest(self.root, limit=1)
        forged = {**valid, "network_requests": 1}
        with patch("ucie_miner.p9_auto_retest.p9.retest",
                   return_value=forged):
            with self.assertRaises(auto.P9AutoRetestError):
                auto.run_one(self.root)
        self.assertEqual(self.records(), [])

    def test_cross_workload_regression_persists_hold_not_manual_pass(self):
        self.stage_learn()
        genuine = evaluate_ucie_owned_recipe

        def new_regression(purpose, *, rows, queries, repeats):
            out = genuine(purpose, rows=rows, queries=queries,
                          repeats=repeats)
            if rows == 256:
                out["candidate_operations_including_setup"] = (
                    out["baseline_operations"] + 1)
                out["synthetic_operation_reduction_observed"] = False
                out["status"] = "UCIE_SYNTHETIC_RECIPE_REVIEW_REQUIRED_NO_GO"
            return out

        with patch("ucie_miner.p11_retest.evaluate_ucie_owned_recipe",
                   side_effect=new_regression):
            observed = auto.run_one(self.root)
        self.assertEqual(observed["status"], auto.RECORDED)
        self.assertEqual(observed["retest_decision"],
                         "FIRST_PARTY_RETEST_REGRESSION_HOLD_NO_GO")
        self.assertEqual(self.records()[0][4],
                         "FIRST_PARTY_RETEST_REGRESSION_HOLD_NO_GO")
        self.assertFalse(observed["auto_promoted"])
        self.assertEqual(auto.run_one(self.root)["status"], auto.NO_WORK)

    def test_non_p9_worker_does_not_call_retest(self):
        with patch("ucie_miner.p9_auto_retest.run_one",
                   side_effect=AssertionError("P9 isolated to experiment worker")):
            self.assertTrue(pipeline._safe_handler(
                self.root, "UCIE_QA_REVIEW"))
        self.assertEqual(self.records(), [])


if __name__ == "__main__":
    unittest.main()
