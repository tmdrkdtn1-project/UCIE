"""UCIE W08: executable first-party Library experiment, strict offline synthetic scope."""
from __future__ import annotations

from dataclasses import replace
import json
import unittest
from unittest.mock import patch

from ucie_miner import capability_evaluator as ev


class W08SyntheticCatalogEvaluationTests(unittest.TestCase):
    def test_first_party_exact_index_matches_linear_and_reduces_work(self):
        result = ev.evaluate_synthetic_library_index(
            rows=1536, queries=48, repeats=2)
        self.assertEqual(result["schema"], ev.SCHEMA)
        self.assertEqual(result["status"],
                         "SYNTHETIC_EQUIVALENCE_AND_OPERATION_REDUCTION_OBSERVED_NO_GO")
        self.assertTrue(result["exact_result_equivalence_observed"])
        self.assertEqual(result["mismatched_query_count"], 0)
        self.assertGreater(result["matching_query_count"], 0)
        self.assertGreater(result["no_match_query_count"], 0)
        self.assertEqual(result["reference_comparisons_per_run"], 1536 * 48)
        self.assertEqual(result["candidate_build_plus_lookup_operations_per_run"],
                         1536 + 48)
        self.assertGreater(result["operation_reduction"], 0)
        self.assertGreater(result["unique_index_keys"], 1)
        self.assertEqual(result["measurement_repetitions"], 2)
        self.assertGreaterEqual(result["baseline_median_elapsed_ns"], 0)
        self.assertGreaterEqual(result["candidate_median_elapsed_ns"], 0)
        self.assertFalse(result["elapsed_time_guaranteed_faster"])
        self.assertFalse(result["production_approved"])
        self.assertFalse(result["v1_accepted"])

    def test_catalog_is_deterministic_approved_domain_shaped_but_synthetic(self):
        first = ev.synthetic_catalog(256)
        second = ev.synthetic_catalog(256)
        self.assertEqual(first, second)
        self.assertEqual(len(set(r.synthetic_id for r in first)), len(first))
        self.assertTrue(all(x.source_id.removeprefix("repo:")
                            in ev.APPROVED_REPOSITORIES for x in first))
        result = ev.evaluate_synthetic_library_index(
            rows=256, queries=16, repeats=1)
        self.assertEqual(result["dataset_sha256"],
                         ev.evaluate_synthetic_library_index(
                             rows=256, queries=16, repeats=1)["dataset_sha256"])
        self.assertFalse(result["public_source_data_used"])
        self.assertFalse(result["upstream_capability_implemented_or_verified"])

    def test_real_algorithms_equal_for_each_match_and_miss(self):
        records = ev.synthetic_catalog(256)
        index, built = ev.build_exact_index(records)
        self.assertEqual(built, 256)
        for q in ev.synthetic_queries(48):
            baseline, checks = ev.linear_search(records, q)
            improved, lookups = ev.indexed_search(index, q)
            self.assertEqual(improved, baseline)
            self.assertEqual(checks, 256)
            self.assertEqual(lookups, 1)

    def test_change_to_candidate_algorithm_is_detected_and_not_passed(self):
        saved = ev._measure_indexed
        def broken(catalog, queries):
            outputs, checks, elapsed, keys = saved(catalog, queries)
            outputs[0] = ("UCIE_FAKE_RESULT",)
            return outputs, checks, elapsed, keys
        with patch.object(ev, "_measure_indexed", broken):
            result = ev.evaluate_synthetic_library_index(
                rows=256, queries=16, repeats=1)
        self.assertEqual(result["status"], "SYNTHETIC_EVALUATION_REQUIRES_REVIEW_NO_GO")
        self.assertFalse(result["exact_result_equivalence_observed"])
        self.assertEqual(result["mismatched_query_count"], 1)
        self.assertFalse(result["production_approved"])

    def test_reject_unbounded_or_non_integer_workloads(self):
        for settings in (
            {"rows": 0},
            {"rows": 4097},
            {"rows": True},
            {"rows": "1000"},
            {"queries": 0},
            {"queries": 97},
            {"queries": False},
            {"repeats": 0},
            {"repeats": 6},
            {"repeats": 1.5},
        ):
            with self.subTest(settings=settings):
                with self.assertRaises(ev.CapabilityEvaluationError):
                    ev.evaluate_synthetic_library_index(**settings)

    def test_no_source_calls_files_scheduler_signing_or_persistent_changes(self):
        with patch("urllib.request.urlopen",
                   side_effect=AssertionError("unexpected network")):
            with patch("sqlite3.connect",
                       side_effect=AssertionError("unexpected database")):
                result = ev.evaluate_synthetic_library_index(
                    rows=256, queries=16, repeats=1)
        self.assertEqual(result["network_requests"], 0)
        self.assertEqual(result["database_writes"], 0)
        self.assertFalse(result["project_data_accessed"])
        self.assertFalse(result["auto_promoted"])
        self.assertFalse(result["owner_approved"])
        self.assertFalse(result["scheduler_registered"])
        self.assertFalse(result["model_weights_changed"])

    def test_experience_receipt_is_unsaved_and_requires_review(self):
        result = ev.evaluate_synthetic_library_index(
            rows=256, queries=16, repeats=1)
        experience = result["ucie_experience_record"]
        self.assertEqual(experience["kind"], "UCIE_EXPERIENCE")
        self.assertEqual(experience["dataset_sha256"], result["dataset_sha256"])
        self.assertEqual(experience["outcome"], result["status"])
        self.assertTrue(experience["human_review_required"])
        self.assertFalse(experience["revision_ready"])
        self.assertFalse(experience["production_adopted"])
        self.assertFalse(result["performance_on_real_catalog_measured"])
        self.assertNotIn("source_code", json.dumps(result))

    def test_read_only_cli_json_and_bounds(self):
        with patch("sys.argv", ["ucie-capability-eval", "--rows", "256",
                                "--queries", "16", "--repeats", "1"]):
            with patch("builtins.print") as rendered:
                self.assertEqual(ev.main(), 0)
        result = json.loads(rendered.call_args.args[0])
        self.assertEqual(result["synthetic_item_count"], 256)
        self.assertTrue(result["exact_result_equivalence_observed"])
        with patch("sys.argv", ["ucie-capability-eval", "--rows", "999999"]):
            with patch("builtins.print") as rendered:
                self.assertEqual(ev.main(), 2)
        denial = json.loads(rendered.call_args.args[0])
        self.assertEqual(denial["status"],
                         "BOUNDED_SYNTHETIC_EVALUATION_REJECTED_NO_GO")


if __name__ == "__main__":
    unittest.main()
