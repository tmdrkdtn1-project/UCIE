"""UCIE read-only W04 performance baseline QA; owner-only actual DB probe."""
from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "ucie_w04_owner_public_readonly_perf_v01.py"
spec = importlib.util.spec_from_file_location("ucie_w04_owner_perf_v01", SCRIPT)
assert spec and spec.loader
m = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = m
spec.loader.exec_module(m)


def sample_handoff():
    return {
        "status": "LINKED_UNVERIFIED_NO_GO", "approved_rules": 0,
        "auto_promoted": False, "production_approved": False,
        "linked_revisions": 4,
    }


def response(query):
    matches = {"python": 2, "git": 1, "api": 3}[query]
    return {
        "schema": "UCIE_W04_READ_ONLY_LIBRARY_CANDIDATE_SEARCH_V1",
        "status": "READ_ONLY_UNVERIFIED_LIBRARY_SEARCH_NO_GO",
        "network_requests": 0, "operating_database_writes": 0,
        "approved_or_exportable_items": 0, "auto_promoted": False,
        "v1_library_accepted": False,
        "source_linked_count": 4, "total_matches": matches,
        "returned_count": matches,
        "items": [{
            "human_approved": False, "export_allowed": False,
            "lifecycle": "UNVERIFIED_CANDIDATE_ONLY"
        } for _ in range(matches)],
    }


class W04OwnerRealPublicSearchPerformanceTests(unittest.TestCase):
    def test_exact_owner_root_and_fixed_queries(self):
        self.assertEqual(m.EXPECTED_OWNER_ROOT.as_posix().lower(), "d:/ucie")
        self.assertEqual(m.QUERIES, ("python", "git", "api"))
        self.assertFalse(m.__dict__.get("ALLOW_EXTERNAL_NETWORK", False))
        self.assertEqual(m.END_TO_END_SAMPLES, 4)

    def test_synthetic_measurement_has_no_improvement_or_approval(self):
        calls = {"load": 0, "in_memory": 0, "full": 0}
        def load(root):
            calls["load"] += 1
            return sample_handoff()
        def mem(handoff, *, query, limit):
            self.assertEqual(limit, 10)
            calls["in_memory"] += 1
            return response(query)
        def full(root, *, query, limit):
            self.assertEqual(limit, 10)
            calls["full"] += 1
            return response(query)
        report = m.measure_w04(
            Path("D:/UCIE"), load, mem, full, mem_samples=2,
            full_samples=2,
        )
        self.assertEqual(report["schema"], m.SCHEMA)
        self.assertEqual(len(report["results"]), 3)
        self.assertEqual(report["public_linked_candidate_revisions_not_approved_rules"], 4)
        self.assertEqual(calls["load"], 1)
        self.assertEqual(calls["in_memory"], 3 * (1 + m.WARMUPS + 2))
        self.assertEqual(calls["full"], 6)
        self.assertIs(report["performance_improvement_claimed"], False)
        self.assertIs(report["customer_release_authorized"], False)
        self.assertIs(report["ui_modified"], False)
        self.assertEqual(report["operating_database_writes_by_measurer"], 0)
        for entry in report["results"]:
            self.assertEqual(entry["preloaded_handoff_in_memory_filter"]["samples"], 2)
            self.assertEqual(entry["full_readonly_ledger_to_response"]["samples"], 2)
            self.assertGreaterEqual(entry["preloaded_handoff_in_memory_filter"]["median_ms"], 0)

    def test_incomplete_source_linkage_is_fail_closed(self):
        def bad_loader(_):
            return {**sample_handoff(), "status": "SOURCE_REVISIONS_PENDING_NO_GO"}
        with self.assertRaisesRegex(m.BaselineError, "HANDOFF_NOT_FULLY_LINKED"):
            m.measure_w04(Path("D:/UCIE"), bad_loader, lambda *_a, **_k: None,
                          lambda *_a, **_k: None, mem_samples=2, full_samples=2)

    def test_forged_approval_and_bad_counts_are_not_timed(self):
        bads = [
            {"export_allowed": True}, {"human_approved": True},
            {"lifecycle": "VERIFIED"}, {"status": "SOURCE_LINKAGE_INCOMPLETE_NO_GO"},
            {"network_requests": 1}, {"approved_or_exportable_items": 1},
            {"total_matches": -1}, {"returned_count": 20},
        ]
        for change in bads:
            with self.subTest(change=change):
                value = response("python")
                if "export_allowed" in change or "human_approved" in change or "lifecycle" in change:
                    value["items"][0].update(change)
                else:
                    value.update(change)
                with self.assertRaises(m.BaselineError):
                    m.checked(value)

    def test_measurement_count_bounds_fail_before_search(self):
        def fail(*args, **kwargs):
            raise AssertionError("no data access should happen")
        for settings in ({"mem_samples": 1}, {"full_samples": 0},
                         {"mem_samples": 21}, {"full_samples": 11}):
            with self.subTest(settings=settings):
                with self.assertRaises(m.BaselineError):
                    m.measure_w04(Path("D:/UCIE"), fail, fail, fail, **settings)

    def test_invalid_or_other_root_is_denied(self):
        with self.assertRaises(m.BaselineError):
            m.measure_w04(Path("D:/OTHER"), lambda *_: None,
                          lambda *_a, **_k: None,
                          lambda *_a, **_k: None)
        if os.name != "nt":
            with self.assertRaisesRegex(m.BaselineError, "WINDOWS_UCIE_OWNER_ONLY"):
                m.owner_root()

    @unittest.skipUnless(os.name == "nt" and Path("D:/UCIE").is_dir(),
                         "exact owner D:/UCIE only; not a synthetic CI acceptance")
    def test_actual_owner_public_readonly_w04_baseline(self):
        actual = m.run_owner()
        self.assertEqual(actual["status"], "OWNER_PUBLIC_READONLY_LATENCY_BASELINE_OBSERVED")
        self.assertEqual(len(actual["results"]), 3)
        self.assertFalse(actual["performance_improvement_claimed"])
        self.assertFalse(actual["customer_release_authorized"])
        print("UCIE_W04_READONLY_OWNER_LATENCY=" + json.dumps(
            actual, sort_keys=True, ensure_ascii=False))


if __name__ == "__main__":
    unittest.main()
