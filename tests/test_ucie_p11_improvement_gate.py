"""Real P11/P10 first-party improvement feedback and regression isolation tests."""
from __future__ import annotations

from contextlib import closing
from datetime import datetime, timedelta, timezone
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

from ucie_miner import p11_closed_loop as p11
from ucie_miner import pending_queue as queue
from ucie_miner import runtime_pipeline as pipeline
from ucie_miner.capability_trials import evaluate_ucie_owned_recipe
from ucie_miner.p11_improvement_gate import (
    ImprovementGateError, classify_existing, assess_new, GOOD, HOLD,
    PROPOSAL, STOP,
)
from ucie_miner.public_discovery import SOURCES, public_feed_url

T0 = datetime(2026, 10, 30, 9, tzinfo=timezone.utc)


def public_item(source, number, title):
    return {
        "number": number, "title": title,
        "merged_at": "2026-10-29T02:00:00Z",
        "html_url": f"https://github.com/{source}/pull/{number}",
        "merge_commit_sha": f"{number:040x}",
        "base": {"repo": {"full_name": source}},
    }


class P11RealImprovementGateTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / "UCIE"
        (self.root / "runtime").mkdir(parents=True)
        queue.initialize_queue(self.root)
        p11.activate(self.root)

    def stage(self, source, number, title, when):
        def fetch(url):
            self.assertEqual(url, public_feed_url(source))
            return [public_item(source, number, title)]
        result = p11.collect_one(self.root, fetch=fetch, now=when)
        self.assertEqual(result["new_unverified_leads"], 1)

    def snapshot(self):
        return p11.status(self.root)

    def test_recurrence_records_review_and_next_real_workload_in_same_p11_ledger(self):
        self.stage(SOURCES[0], 1, "fix regression", T0)
        before = self.snapshot()
        self.assertEqual(before["improvement_review_record_count"], 0)
        first = p11.learn_one(self.root, now=T0 + timedelta(seconds=1))
        self.assertEqual(first["workload"], 128)
        self.assertEqual(first["improvement_gate_decision"], PROPOSAL)
        self.assertTrue(first["improvement_proposal_created"])
        self.assertGreater(first["improvement_operation_reduction_ppm"], 0)
        self.assertFalse(first["production_algorithm_changed"])
        self.assertFalse(first["auto_promoted"])
        self.assertEqual(self.snapshot()["first_party_retest_proposals_not_adopted"], 1)
        with closing(sqlite3.connect(
                str(self.root / "runtime" / p11.DB_NAME))) as conn:
            rows = conn.execute(
                "SELECT source,pr_number,receipt_sha256,decision FROM improvement_review"
            ).fetchall()
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0][2], first["experiment_receipt_sha256"])
            self.assertEqual(rows[0][3], PROPOSAL)
        # Same lead cannot create another review, even after P10 re-arms.
        self.assertTrue(pipeline._safe_handler(self.root, "EXPERIENCE_CLOSED_LOOP"))
        self.assertEqual(self.snapshot()["improvement_review_record_count"], 1)
        self.stage(SOURCES[1], 2, "fix regression", T0 + timedelta(minutes=5))
        second = p11.learn_one(
            self.root, now=T0 + timedelta(minutes=5, seconds=1))
        self.assertEqual(second["workload"], 256)
        self.assertEqual(second["improvement_gate_decision"], PROPOSAL)
        self.assertEqual(self.snapshot()["first_party_retest_proposals_not_adopted"], 2)
        self.assertEqual(self.snapshot()["first_party_experiences"], 2)
        self.assertEqual(self.snapshot()["production_improvements_auto_applied"], 0)
        self.assertFalse(self.snapshot()["production_algorithm_changed"])

    def test_real_regression_holds_recipe_but_does_not_starve_other_recipe(self):
        self.stage(SOURCES[0], 3, "fix regression", T0)
        genuine = evaluate_ucie_owned_recipe(
            "LEARNING_FEEDBACK_LOOP", rows=128, queries=24, repeats=2)
        rejected = dict(genuine)
        rejected["candidate_operations_including_setup"] = (
            genuine["baseline_operations"] + 1)
        rejected["synthetic_operation_reduction_observed"] = False
        rejected["status"] = "UCIE_SYNTHETIC_RECIPE_REVIEW_REQUIRED_NO_GO"
        rejected["next_hypothesis"] = "FIX_UCIE_RECIPE_BEFORE_RETEST"
        with patch("ucie_miner.p11_closed_loop.evaluate_ucie_owned_recipe",
                   return_value=rejected):
            failed = p11.learn_one(self.root, now=T0 + timedelta(seconds=1))
        self.assertEqual(failed["improvement_gate_decision"], STOP)
        self.assertFalse(failed["improvement_proposal_created"])
        self.assertEqual(self.snapshot()["first_party_regression_holds"], 1)

        self.stage(SOURCES[1], 4, "fix regression", T0 + timedelta(minutes=5))
        snapshot = self.snapshot()
        with patch("ucie_miner.p11_closed_loop.evaluate_ucie_owned_recipe",
                   side_effect=AssertionError("held recipe must not be retested")):
            hold = p11.learn_one(self.root)
        self.assertEqual(hold["status"], "P11_IMPROVEMENT_REVIEW_HOLD_NO_GO")
        self.assertEqual(self.snapshot()["first_party_experiences"],
                         snapshot["first_party_experiences"])
        self.assertTrue(pipeline._safe_handler(self.root, "EXPERIENCE_CLOSED_LOOP"))
        self.assertEqual(self.snapshot()["awaiting_synthetic_experiment"], 1)

        self.stage(SOURCES[2], 5, "fix crash in parser",
                   T0 + timedelta(minutes=10))
        resumed = p11.learn_one(
            self.root, now=T0 + timedelta(minutes=10, seconds=2))
        self.assertEqual(resumed["recipe"], "ENGINE_INCREMENTAL_BUILD")
        self.assertEqual(resumed["workload"], 128)
        self.assertTrue(resumed["improvement_proposal_created"])
        self.assertEqual(self.snapshot()["awaiting_synthetic_experiment"], 1)
        self.assertEqual(self.snapshot()["first_party_experiences"], 2)

    def test_forged_trial_claim_fails_without_marking_lead_or_writing_review(self):
        self.stage(SOURCES[0], 6, "fix regression", T0)
        real = evaluate_ucie_owned_recipe(
            "LEARNING_FEEDBACK_LOOP", rows=128, queries=24, repeats=2)
        for key, value in (
            ("production_adopted", True),
            ("evaluates_upstream_code", True),
            ("model_weights_changed", True),
            ("network_requests", 1),
            ("synthetic_operation_reduction_observed", False),
            ("mismatched_queries_across_repetitions", 1),
        ):
            with self.subTest(field=key):
                forged = {**real, key: value}
                with patch(
                        "ucie_miner.p11_closed_loop.evaluate_ucie_owned_recipe",
                        return_value=forged):
                    with self.assertRaises(ImprovementGateError):
                        p11.learn_one(self.root)
                self.assertEqual(self.snapshot()["improvement_review_record_count"], 0)
                self.assertEqual(self.snapshot()["first_party_experiences"], 0)
                self.assertEqual(self.snapshot()["awaiting_synthetic_experiment"], 1)

    def test_corrupt_existing_history_fails_closed_without_code_change(self):
        self.stage(SOURCES[0], 7, "fix regression", T0)
        p11.learn_one(self.root)
        with closing(sqlite3.connect(str(
                self.root / "runtime" / p11.DB_NAME))) as conn:
            conn.execute(
                "UPDATE experience SET candidate_ops=baseline_ops "
                "WHERE source=? AND pr_number=?", (SOURCES[0], 7))
            conn.commit()
        self.stage(SOURCES[1], 8, "fix regression", T0 + timedelta(minutes=5))
        with self.assertRaises(ImprovementGateError):
            p11.learn_one(self.root)
        self.assertEqual(self.snapshot()["improvement_review_record_count"], 1)
        self.assertEqual(self.snapshot()["awaiting_synthetic_experiment"], 1)

    def test_legacy_experience_is_not_falsely_backfilled_as_new_improvement(self):
        self.stage(SOURCES[0], 9, "fix regression", T0)
        before = self.snapshot()
        self.assertEqual(before["improvement_review_record_count"], 0)
        p11.learn_one(self.root)
        with closing(sqlite3.connect(str(
                self.root / "runtime" / p11.DB_NAME))) as conn:
            conn.execute("DROP TABLE improvement_review")
            conn.commit()
        viewed = self.snapshot()
        self.assertEqual(viewed["first_party_experiences"], 1)
        self.assertEqual(viewed["improvement_review_record_count"], 0)
        self.assertFalse(viewed["prior_experience_auto_backfilled"])
        self.assertFalse(viewed["production_algorithm_changed"])
        self.assertFalse(viewed["auto_promoted"])

    def test_pure_history_rejects_falsified_positive(self):
        correct = {
            "recipe": "LEARNING_FEEDBACK_LOOP", "workload": 128,
            "baseline_ops": 3072, "candidate_ops": 152,
            "exact_equal": 1, "hypothesis_status": GOOD,
        }
        counts, holds = classify_existing([correct])
        self.assertEqual(counts["LEARNING_FEEDBACK_LOOP"], 1)
        self.assertFalse(holds)
        for update in (
            {"candidate_ops": 5000}, {"exact_equal": 0},
            {"hypothesis_status": HOLD}, {"recipe": "PRIVATE_UNKNOWN"},
            {"workload": 10000}, {"baseline_ops": True},
        ):
            with self.subTest(update=update):
                with self.assertRaises(ImprovementGateError):
                    classify_existing([{**correct, **update}])
        trial = evaluate_ucie_owned_recipe(
            "LEARNING_FEEDBACK_LOOP", rows=128, queries=24, repeats=2)
        assessment = assess_new(
            trial, recipe="LEARNING_FEEDBACK_LOOP", workload=128)
        self.assertEqual(assessment["decision"], PROPOSAL)
        self.assertFalse(assessment["production_code_changed"])


if __name__ == "__main__":
    unittest.main()
