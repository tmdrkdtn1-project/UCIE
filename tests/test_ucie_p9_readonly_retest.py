"""P9 read-only first-party improvement retest and fail-closed review QA."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

from ucie_miner import p11_closed_loop as p11
from ucie_miner import p11_retest
from ucie_miner import pending_queue as queue
from ucie_miner.capability_trials import evaluate_ucie_owned_recipe
from ucie_miner.public_discovery import SOURCES, public_feed_url
from ucie_miner.p11_improvement_gate import ImprovementGateError

T0 = datetime(2026, 10, 30, 10, tzinfo=timezone.utc)


def source_row(number=990201, source=SOURCES[0]):
    return {
        "number": number,
        "title": "Fix regression in socket unit test",
        "merged_at": "2026-10-30T08:00:00Z",
        "html_url": f"https://github.com/{source}/pull/{number}",
        "merge_commit_sha": f"{number:040x}",
        "base": {"repo": {"full_name": source}},
    }


class P9FirstPartyRetestTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / "UCIE"
        (self.root / "runtime").mkdir(parents=True)
        queue.initialize_queue(self.root)

    def activate_and_learn(self, *, number=990201, broken=False):
        p11.activate(self.root)
        self.assertEqual(p11.collect_one(
            self.root, now=T0,
            fetch=lambda url: [source_row(number)] if url == public_feed_url(
                SOURCES[0]) else self.fail("unauthorized public source")
        )["new_unverified_leads"], 1)
        if broken:
            genuine = evaluate_ucie_owned_recipe(
                "LEARNING_FEEDBACK_LOOP", rows=128, queries=24, repeats=2)
            failed = dict(genuine)
            failed["candidate_operations_including_setup"] = (
                genuine["baseline_operations"] + 1)
            failed["synthetic_operation_reduction_observed"] = False
            failed["status"] = "UCIE_SYNTHETIC_RECIPE_REVIEW_REQUIRED_NO_GO"
            failed["next_hypothesis"] = "FIX_UCIE_RECIPE_BEFORE_RETEST"
            with patch("ucie_miner.p11_closed_loop.evaluate_ucie_owned_recipe",
                       return_value=failed):
                p11.learn_one(self.root, now=T0 + timedelta(seconds=1))
        else:
            result = p11.learn_one(
                self.root, now=T0 + timedelta(seconds=1))
            self.assertTrue(result["improvement_proposal_created"])
        self.assertEqual(p11.status(self.root)["improvement_review_record_count"], 1)

    def test_inert_not_enabled_does_not_initialize_p11(self):
        db, optin = p11._paths(self.root)
        self.assertFalse(db.exists())
        self.assertFalse(optin.exists())
        result = p11_retest.retest(self.root)
        self.assertEqual(result["status"], "P9_P11_NOT_ENABLED_READ_ONLY")
        self.assertEqual(result["operating_database_writes"], 0)
        self.assertFalse(db.exists())
        self.assertFalse(optin.exists())

    def test_no_prior_review_does_not_relabel_legacy_experience(self):
        p11.activate(self.root)
        result = p11_retest.retest(self.root)
        self.assertEqual(result["status"], "P9_NO_NEW_IMPROVEMENT_REVIEW_READ_ONLY")
        self.assertEqual(result["review_rows_checked"], 0)
        self.assertEqual(result["items"], [])
        self.assertEqual(p11.status(self.root)["improvement_review_record_count"], 0)

    def test_real_p11_review_retest_three_workloads_receipt_unchanged(self):
        self.activate_and_learn()
        path = self.root / "runtime" / p11.DB_NAME
        before = path.read_bytes()
        existing_paths = sorted(str(x.relative_to(self.root))
                                for x in self.root.rglob("*"))
        with patch("urllib.request.urlopen",
                   side_effect=AssertionError("no network in P9 retest")):
            result = p11_retest.retest(
                self.root, source=SOURCES[0], pr_number=990201, limit=1)
        self.assertEqual(result["status"],
                         "P9_FIRST_PARTY_RETEST_COMPLETE_UNADOPTED")
        self.assertEqual(result["review_rows_checked"], 1)
        self.assertEqual(result["eligible_for_manual_review_only"], 1)
        self.assertEqual(result["regression_holds"], 0)
        row = result["items"][0]
        self.assertEqual(row["retest_decision"],
                         "FIRST_PARTY_RETEST_PASS_MANUAL_REVIEW_ONLY")
        self.assertEqual(row["workloads_checked"], 3)
        self.assertEqual({t["workload"] for t in row["trials"]},
                         {128, 256, 512})
        self.assertTrue(row["trials"][0]["historical_receipt_reproduced"])
        self.assertEqual(len(row["retest_receipt_sha256"]), 64)
        self.assertFalse(row["production_code_adopted"])
        self.assertFalse(result["auto_promoted"])
        self.assertEqual(result["network_requests"], 0)
        self.assertEqual(result["operating_database_writes"], 0)
        self.assertEqual(path.read_bytes(), before)
        self.assertEqual(sorted(str(x.relative_to(self.root))
                         for x in self.root.rglob("*")), existing_paths)
        self.assertEqual(p11.status(self.root)["improvement_review_record_count"], 1)
        repeat = p11_retest.retest(self.root)
        self.assertEqual(repeat["items"][0]["retest_receipt_sha256"],
                         row["retest_receipt_sha256"])

    def test_cross_workload_new_regression_forces_no_go(self):
        self.activate_and_learn()
        genuine = evaluate_ucie_owned_recipe
        def simulate(purpose, *, rows, queries, repeats):
            out = genuine(purpose, rows=rows, queries=queries, repeats=repeats)
            if rows == 256:
                out["candidate_operations_including_setup"] = (
                    out["baseline_operations"] + 1)
                out["synthetic_operation_reduction_observed"] = False
                out["status"] = "UCIE_SYNTHETIC_RECIPE_REVIEW_REQUIRED_NO_GO"
                out["next_hypothesis"] = "FIX_UCIE_RECIPE_BEFORE_RETEST"
            return out
        with patch("ucie_miner.p11_retest.evaluate_ucie_owned_recipe",
                   side_effect=simulate):
            result = p11_retest.retest(self.root)
        self.assertEqual(result["eligible_for_manual_review_only"], 0)
        self.assertEqual(result["regression_holds"], 1)
        self.assertEqual(result["items"][0]["retest_decision"],
                         "FIRST_PARTY_RETEST_REGRESSION_HOLD_NO_GO")
        self.assertEqual(result["items"][0]["trials"][1]["decision"],
                         "FIRST_PARTY_REGRESSION_HOLD_NO_GO")
        self.assertFalse(result["production_code_adopted"])

    def test_original_regression_hold_is_never_automatically_cleared(self):
        self.activate_and_learn(broken=True)
        before = (self.root / "runtime" / p11.DB_NAME).read_bytes()
        result = p11_retest.retest(self.root)
        self.assertEqual(result["regression_holds"], 1)
        self.assertTrue(result["items"][0]["original_regression_hold_preserved"])
        self.assertFalse(result["items"][0]["trials"][0][
            "historical_receipt_reproduced"])
        self.assertEqual((self.root / "runtime" / p11.DB_NAME).read_bytes(),
                         before)

    def test_forged_side_effect_claim_fails_closed_without_db_writes(self):
        self.activate_and_learn()
        path = self.root / "runtime" / p11.DB_NAME
        before = path.read_bytes()
        genuine = evaluate_ucie_owned_recipe
        def forged(purpose, *, rows, queries, repeats):
            out = genuine(purpose, rows=rows, queries=queries, repeats=repeats)
            if rows == 256:
                out["network_requests"] = 1
            return out
        with patch("ucie_miner.p11_retest.evaluate_ucie_owned_recipe",
                   side_effect=forged):
            with self.assertRaises(ImprovementGateError):
                p11_retest.retest(self.root)
        self.assertEqual(path.read_bytes(), before)

    def test_corrupted_original_review_refuses_to_retest(self):
        self.activate_and_learn()
        path = self.root / "runtime" / p11.DB_NAME
        with sqlite3.connect(path) as conn:
            conn.execute("UPDATE improvement_review SET receipt_sha256=?",
                         ("f" * 64,))
            conn.commit()
        before = path.read_bytes()
        with self.assertRaises(p11_retest.P9RetestError):
            p11_retest.retest(self.root)
        self.assertEqual(path.read_bytes(), before)

    def test_only_exact_approved_source_and_bounded_selectors(self):
        for options in (
            {"source": "unapproved/repo", "pr_number": 1},
            {"source": SOURCES[0]},
            {"pr_number": 1},
            {"limit": 4},
            {"limit": True},
            {"source": SOURCES[0], "pr_number": -1},
        ):
            with self.subTest(options=options):
                with self.assertRaises(p11_retest.P9RetestError):
                    p11_retest.retest(self.root, **options)


if __name__ == "__main__":
    unittest.main()
