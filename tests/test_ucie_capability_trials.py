"""UCIE W05/P8 self-owned trials and real W05 classifier integration."""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
import json
import unittest
from unittest.mock import patch

from ucie_miner import capability_trials as t
from ucie_miner.public_discovery import DiscoveryError
from test_ucie_positive_capability_discovery import public_pr, NOW


class W05P8FirstPartyTrials(unittest.TestCase):
    def test_three_real_self_owned_algorithms_agree_on_all_bounded_scenarios(self):
        for purpose, (baseline, improved) in t.ALGORITHMS.items():
            for n, q in ((64, 8), (128, 24), (512, 64)):
                with self.subTest(purpose=purpose, n=n, q=q):
                    expected, first_ops = baseline(n, q)
                    actual, improved_ops = improved(n, q)
                    self.assertEqual(expected, actual)
                    self.assertEqual(len(actual), q)
                    self.assertEqual(first_ops, n * q)
                    self.assertLess(improved_ops, first_ops)
                    r = t.evaluate_ucie_owned_recipe(
                        purpose, rows=n, queries=q, repeats=1)
                    self.assertTrue(r["exact_result_equivalence_observed"])
                    self.assertEqual(r["mismatched_queries_across_repetitions"], 0)
                    self.assertTrue(r["synthetic_operation_reduction_observed"])
                    self.assertFalse(r["evaluates_upstream_code"])
                    self.assertFalse(r["upstream_benefit_verified"])
                    self.assertFalse(r["auto_promoted"])
                    self.assertFalse(r["production_adopted"])

    def test_bad_trial_is_failure_not_positive(self):
        original = t.ALGORITHMS["SKILL_TEST_AUTOMATION"]
        def broken(n, q):
            values, ops = original[1](n, q)
            return ((9999,),) + values[1:], ops
        with patch.dict(t.ALGORITHMS, {
            "SKILL_TEST_AUTOMATION": (original[0], broken)
        }):
            result = t.evaluate_ucie_owned_recipe(
                "SKILL_TEST_AUTOMATION", rows=64, queries=8, repeats=1)
        self.assertFalse(result["synthetic_operation_reduction_observed"])
        self.assertFalse(result["exact_result_equivalence_observed"])
        self.assertEqual(result["status"],
                         "UCIE_SYNTHETIC_RECIPE_REVIEW_REQUIRED_NO_GO")

    def test_no_unsupported_upstream_recipe_invented(self):
        for purpose in (
            "ENGINE_WORKFLOW_ORCHESTRATION", "SKILL_RELEASE_AUTOMATION",
            "UNAPPROVED_PRIVATE_SKILL",
        ):
            with self.assertRaises(t.CapabilityTrialError):
                t.evaluate_ucie_owned_recipe(purpose)

    def test_workload_is_strictly_bounded(self):
        for kwargs in (
            {"rows": 0}, {"rows": True}, {"rows": 513},
            {"queries": False}, {"queries": 65}, {"repeats": 0},
            {"repeats": 6}, {"repeats": 1.5},
        ):
            with self.subTest(kwargs=kwargs):
                with self.assertRaises(t.CapabilityTrialError):
                    t.evaluate_ucie_owned_recipe(
                        "LEARNING_FEEDBACK_LOOP", **kwargs)

    def test_real_w05_normalizer_connects_only_approved_cues(self):
        metadata = [
            public_pr(11101, "Add incremental build cache for compilation"),
            public_pr(11102, "Introduce test automation"),
            public_pr(11103, "Introduce adaptive learning feedback loop"),
            public_pr(11104, "Add build orchestration"),
            public_pr(11105, "Fix regression in incremental build cache"),
        ]
        with patch("urllib.request.urlopen",
                   side_effect=AssertionError("no public GET")):
            result = t.evaluate_approved_w05_feed(
                metadata, source_id="repo:python/cpython", now=NOW)
        self.assertEqual(result["source_candidate_count"], 4)
        self.assertEqual(result["returned_count"], 4)
        self.assertEqual({x["kind"] for x in result["items"]},
                         {"DEVELOPMENT_ENGINE", "REUSABLE_SKILL", "LEARNING_LOGIC"})
        self.assertEqual(sum(x["synthetic_experiment"] is not None
                             for x in result["items"]), 3)
        self.assertEqual(sum(x["synthetic_experiment"] is None
                             for x in result["items"]), 1)
        self.assertTrue(all(not x["upstream_capability_tested"]
                            and not x["export_allowed"]
                            for x in result["items"]))
        self.assertEqual(result["network_requests"], 0)
        self.assertEqual(result["experience_ledger_writes"], 0)

    def test_unimplemented_w05_cue_has_no_fabricated_trial(self):
        r = t.evaluate_approved_w05_feed(
            [public_pr(33330, "Introduce workflow engine")],
            source_id="repo:python/cpython", now=NOW)
        self.assertEqual(r["source_candidate_count"], 1)
        self.assertEqual(r["items"][0]["evaluation_status"],
                         "NO_FIRST_PARTY_RECIPE_IMPLEMENTED")
        self.assertIsNone(r["items"][0]["synthetic_experiment"])

    def test_unapproved_or_forged_pr_is_blocked_by_real_w05_classifier(self):
        rows = [public_pr(11101, "Add incremental build cache for compilation")]
        for source in ("research:GH Archive", "repo:unapproved/private"):
            with self.assertRaises(DiscoveryError):
                t.verified_w05_cues(rows, source_id=source, now=NOW)
        changed = deepcopy(rows)
        changed[0]["html_url"] = "https://example.invalid/evil"
        with self.assertRaises(DiscoveryError):
            t.verified_w05_cues(
                changed, source_id="repo:python/cpython", now=NOW)

    def test_cli_is_inert_by_default_and_explicit_demo_never_calls_http_or_db(self):
        with patch("sys.argv", ["capability_trials"]), patch("builtins.print") as printed:
            self.assertEqual(t.main(), 0)
        self.assertEqual(json.loads(printed.call_args.args[0])["status"],
                         "EXPLICIT_DEMO_REQUIRED_NO_GO")
        with (patch("sys.argv", [
                "capability_trials", "--demo", "--rows", "64",
                "--queries", "8", "--repeats", "1"]),
              patch("urllib.request.urlopen",
                    side_effect=AssertionError("no GET")),
              patch("sqlite3.connect", side_effect=AssertionError("no DB")),
              patch("builtins.print") as printed):
            self.assertEqual(t.main(), 0)
        output = json.loads(printed.call_args.args[0])
        self.assertEqual(len(output["experiments"]), 3)
        self.assertEqual(output["operating_database_writes"], 0)
        self.assertFalse(output["auto_promoted"])


if __name__ == "__main__":
    unittest.main()
