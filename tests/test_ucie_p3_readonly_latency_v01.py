"""Isolated P3 timing-gate tests. No owner database or live UI is opened."""
from __future__ import annotations

import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest

from ucie_miner.p3_readonly_latency_v01 import (
    BaselineError, ENGINE_SCHEMA, SCHEMA, W04_SCHEMA,
    _summary, _time_once, main, measure_baseline,
)


class P3ReadOnlyLatencyTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / "UCIE"
        self.root.mkdir()
        self.calls = {"load": 0, "search": 0, "engine": 0}
        self.digest = "a" * 64

    def loader(self, root):
        self.assertEqual(root, self.root)
        self.calls["load"] += 1
        return {"UCIE_FIRST_PARTY_ONLY": True}

    def search(self, handoff, *, query, limit, group_revisions, offset):
        self.assertEqual(handoff, {"UCIE_FIRST_PARTY_ONLY": True})
        self.assertEqual((limit, group_revisions, offset), (10, False, 0))
        self.assertIn(query, ("python", "git", ""))
        self.calls["search"] += 1
        return {
            "schema": W04_SCHEMA,
            "status": "READ_ONLY_UNVERIFIED_LIBRARY_SEARCH_NO_GO",
            "query": query,
            "source_linked_count": 6,
            "total_matches": {"python": 3, "git": 2, "": 6}[query],
            "items": [{"lifecycle": "UNVERIFIED_CANDIDATE_ONLY",
                       "human_approved": False, "export_allowed": False}],
            "returned_count": 1,
            "network_requests": 0,
            "operating_database_writes": 0,
            "approved_or_exportable_items": 0,
            "auto_promoted": False,
            "v1_library_accepted": False,
        }

    def engine(self, handoff, *, queries, repeats):
        self.assertEqual(handoff, {"UCIE_FIRST_PARTY_ONLY": True})
        self.assertEqual((queries, repeats), (24, 2))
        self.calls["engine"] += 1
        return {
            "schema": ENGINE_SCHEMA,
            "status": "REAL_PUBLIC_METADATA_EXACT_QUERY_EQUIVALENT_UNAPPROVED",
            "real_public_catalog_items": 6,
            "query_count": 24,
            "repetitions": 2,
            "mismatched_query_results": 0,
            "public_catalog_sha256": self.digest,
            "baseline_median_ns": 300,
            "candidate_median_ns": 100,
            "network_requests": 0,
            "operating_database_writes": 0,
            "production_index_applied": False,
            "automatic_learning_or_promotion": False,
            "upstream_code_executed": False,
            "full_w04_substring_search_benchmarked": False,
            "approved_or_exportable_items": 0,
            "v1_accepted": False,
        }

    def run_fixture(self, **changes):
        inputs = dict(root=self.root, samples=2, warmups=1,
                      loader=self.loader, search=self.search, engine=self.engine)
        inputs.update(changes)
        return measure_baseline(**inputs)

    def test_bounded_readonly_baseline_only_aggregate_outputs(self):
        result = self.run_fixture()
        self.assertEqual(result["schema"], SCHEMA)
        self.assertEqual(result["status"], "OBSERVATIONAL_BASELINE_ONLY_NO_OPTIMIZATION")
        self.assertEqual(self.calls, {"load": 3, "search": 9, "engine": 3})
        self.assertEqual(result["source_linked_public_rows"], 6)
        self.assertEqual(result["samples"], 2)
        self.assertEqual(result["w04_substring_search_on_loaded_handoff"]
                         ["empty_query"]["total_matches"], 6)
        self.assertEqual(result["read_and_validate_handoff"]["samples"], 2)
        self.assertEqual(result["p8_exact_public_catalog_engine_on_loaded_handoff"]
                         ["internal_linear_scan"]["samples"], 2)
        self.assertFalse(result["customer_http_latency_measured"])
        self.assertFalse(result["performance_root_cause_proven"])
        self.assertFalse(result["persistent_index_created"])
        self.assertFalse(result["owner_release_approved"])
        self.assertEqual(result["operating_database_writes"], 0)
        self.assertNotIn("UCIE_FIRST_PARTY_ONLY", json.dumps(result))
        self.assertNotIn(self.temp.name, json.dumps(result))

    def test_boolean_and_out_of_bounds_samples_fail_before_read(self):
        for value in (0, 6, True, -1, "3"):
            with self.subTest(value=value):
                with self.assertRaises(BaselineError):
                    self.run_fixture(samples=value)
        self.assertEqual(self.calls["load"], 0)

    def test_bad_warmup_range_rejected(self):
        for value in (-1, 3, False, "1"):
            with self.subTest(value=value):
                with self.assertRaises(BaselineError):
                    self.run_fixture(warmups=value)
        self.assertEqual(self.calls["load"], 0)

    def test_wrong_root_is_rejected_before_loader(self):
        with self.assertRaises(BaselineError):
            self.run_fixture(root=self.root.parent)
        self.assertEqual(self.calls["load"], 0)

    def test_w04_incomplete_or_forged_approval_fails_closed(self):
        def unsafe(handoff, **kwargs):
            report = self.search(handoff, **kwargs)
            report["human_approved"] = True
            report["status"] = "SOURCE_LINKAGE_INCOMPLETE_NO_GO"
            return report
        with self.assertRaises(BaselineError):
            self.run_fixture(search=unsafe)

    def test_w04_fake_promotion_fails_closed(self):
        def unsafe(handoff, **kwargs):
            report = self.search(handoff, **kwargs)
            report["approved_or_exportable_items"] = 1
            return report
        with self.assertRaises(BaselineError):
            self.run_fixture(search=unsafe)

    def test_w04_per_item_forged_approval_fails_closed(self):
        for key, value in (("lifecycle", "PUBLISHED"),
                           ("human_approved", True),
                           ("export_allowed", True)):
            with self.subTest(key=key):
                def unsafe(handoff, **kwargs):
                    report = self.search(handoff, **kwargs)
                    report["items"][0][key] = value
                    return report
                with self.assertRaises(BaselineError):
                    self.run_fixture(search=unsafe)

    def test_w04_incomplete_item_fails_closed(self):
        def unsafe(handoff, **kwargs):
            report = self.search(handoff, **kwargs)
            report["items"] = [{}]
            return report
        with self.assertRaises(BaselineError):
            self.run_fixture(search=unsafe)

    def test_engine_result_mismatch_or_approval_fails_closed(self):
        for key, value in (("mismatched_query_results", 1),
                           ("production_index_applied", True),
                           ("network_requests", 1),
                           ("v1_accepted", True)):
            with self.subTest(key=key):
                def unsafe(handoff, **kwargs):
                    result = self.engine(handoff, **kwargs)
                    result[key] = value
                    return result
                with self.assertRaises(BaselineError):
                    self.run_fixture(engine=unsafe)

    def test_changing_public_snapshot_fails_closed(self):
        def drift(handoff, **kwargs):
            result = self.engine(handoff, **kwargs)
            if self.calls["engine"] > 1:
                result["public_catalog_sha256"] = "b" * 64
            return result
        with self.assertRaisesRegex(BaselineError, "snapshot changed"):
            self.run_fixture(engine=drift)

    def test_invalid_engine_timing_fails_closed(self):
        def unsafe(handoff, **kwargs):
            result = self.engine(handoff, **kwargs)
            result["baseline_median_ns"] = True
            return result
        with self.assertRaises(BaselineError):
            self.run_fixture(engine=unsafe)

    def test_bad_monotonic_clock_cannot_create_success(self):
        ticks = iter((5, 4))
        with self.assertRaisesRegex(BaselineError, "monotonic"):
            _time_once(lambda: None, lambda: next(ticks))
        with self.assertRaises(BaselineError):
            _summary([1, False])

    def test_invalid_cli_root_returns_sanitized_no_go(self):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            code = main(["--ucie-root", str(self.root.parent)])
        self.assertEqual(code, 2)
        document = json.loads(output.getvalue())
        self.assertEqual(document["status"], "FAIL_CLOSED_NO_MEASUREMENT")
        self.assertEqual(document["network_requests"], 0)
        self.assertNotIn(self.temp.name, output.getvalue())


if __name__ == "__main__":
    unittest.main()
