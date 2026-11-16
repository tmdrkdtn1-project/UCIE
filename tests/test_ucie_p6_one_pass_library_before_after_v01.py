"""UCIE P6 independently compared first-party exact Library search optimization.

Baseline is an immutable UCIE-owned Git source object pinned to PR #300's
main commit. No upstream or private project source is fetched or executed.
All inputs are synthetic UCIE-owned review metadata. Tests never request
the network, read/write operating SQLite, promote candidates or restore files.
"""
from __future__ import annotations

import gc
from hashlib import sha256
import json
from pathlib import Path
import statistics
import subprocess
import sys
from time import perf_counter_ns
import tracemalloc
import types
import unittest
from unittest.mock import patch

from test_ucie_p3_p6_exact_library_pagination_v01 import synthetic_linked_batch, KEY
from ucie_miner import library_exact_index as candidate
from ucie_miner.w10_disposable_restore_probe_v02 import git_blob_sha1
from ucie_miner.verification_handoff import PolicyError

REPO = Path(__file__).resolve().parents[1]
REFERENCE_COMMIT = "638665d7ff7f7c4d14ac689af85018ad30923b63"
REFERENCE_BLOB = "73baf4dac3bc07484a70e6c6854d5ac6937afbb7"
TARGET = "src/ucie_miner/library_exact_index.py"
NEW_DIAGNOSTIC_FIELDS = frozenset({
    "one_pass_source_normalization", "separate_intermediate_record_catalog_created",
    "validated_source_rows", "materialized_result_records",
})
RECIPE = "UCIE_P6_FIRST_PARTY_ONE_PASS_EXACT_LIBRARY_V01"
RESULT_STATUS = "SYNTHETIC_FIRST_PARTY_COMPARISON_ONLY_NO_RELEASE"


def git_readonly(*args: str) -> bytes:
    return subprocess.run(
        ["git", "-C", str(REPO), *args],
        check=True, timeout=15, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    ).stdout


def original_ucie_module():
    """Load an exact, immutable, UCIE-authored historical source from Git."""
    blob = git_readonly("rev-parse", REFERENCE_COMMIT + ":" + TARGET).strip()
    if blob.decode("ascii") != REFERENCE_BLOB:
        raise AssertionError("old UCIE source tree/blob identity changed")
    data = git_readonly("cat-file", "blob", REFERENCE_BLOB)
    if git_blob_sha1(data) != REFERENCE_BLOB:
        raise AssertionError("old UCIE first-party Git blob content changed")
    module = types.ModuleType("ucie_miner._w04_p6_pinned_first_party_baseline")
    module.__package__ = "ucie_miner"
    module.__file__ = "<immutable-ucie-git-source>"
    exec(compile(data, module.__file__, "exec"), module.__dict__)
    return module, sha256(data).hexdigest()


def old_format(result: dict) -> dict:
    return {k: v for k, v in result.items() if k not in NEW_DIAGNOSTIC_FIELDS}


def query_cases(rows: int):
    batch = synthetic_linked_batch(rows)
    miss = KEY[:3] + ("NO_UCIE_MATCH",)
    scenarios = (
        ("linear_sparse", (miss,), 10, 0),
        ("linear_full", (KEY,), 10, 10),
        ("indexed_repeated", (KEY, miss, KEY), 7, 17),
        ("indexed_missing", (miss, miss, KEY, miss), 10, 100),
    )
    return batch, scenarios


def measured_comparison(*, rows: int = 3000, repeats: int = 5) -> dict:
    """Pair old/candidate in alternating order, include warmups and memory.

    Performance numbers are observations on one synthetic CI environment,
    NOT guarantees. This function does NOT write an experience ledger.
    """
    if (type(rows) is not int or not 128 <= rows <= 6000
            or type(repeats) is not int or not 3 <= repeats <= 7):
        raise ValueError("bounded UCIE-only benchmarking requested")
    old, original_sha = original_ucie_module()
    handoff = synthetic_linked_batch(rows)
    misses = KEY[:3] + ("NO_UCIE_MATCH",)
    scenarios = {
        "linear_sparse": (misses,),
        "indexed_repeated": (KEY, misses, KEY),
    }
    results = {}
    with patch("urllib.request.urlopen",
               side_effect=AssertionError("offline UCIE synthetic only")), \
         patch("sqlite3.connect",
               side_effect=AssertionError("operating DB forbidden")):
        for name, queries in scenarios.items():
            kwargs = {"queries": queries, "limit": 10, "offset": 0}
            functions = {
                "old": old.exact_search_linked_public_candidates,
                "candidate": candidate.exact_search_linked_public_candidates,
            }
            expected = functions["old"](handoff, **kwargs)
            actual = functions["candidate"](handoff, **kwargs)
            if expected != old_format(actual):
                raise AssertionError("historical source output behavior changed")
            for fn in functions.values():
                fn(handoff, **kwargs)  # identical warmup for each variant
            times = {"old": [], "candidate": []}
            for turn in range(repeats):
                order = ("old", "candidate") if turn % 2 else ("candidate", "old")
                for key in order:
                    t0 = perf_counter_ns()
                    observed = functions[key](handoff, **kwargs)
                    elapsed = perf_counter_ns() - t0
                    if old_format(observed) != expected:
                        raise AssertionError("benchmark result mismatch")
                    times[key].append(max(0, elapsed))
            peaks = {}
            for key, fn in functions.items():
                gc.collect()
                tracemalloc.start()
                try:
                    observed = fn(handoff, **kwargs)
                    if old_format(observed) != expected:
                        raise AssertionError("memory run result mismatch")
                    _, peak = tracemalloc.get_traced_memory()
                finally:
                    tracemalloc.stop()
                peaks[key] = peak
            prev = int(statistics.median(times["old"]))
            now = int(statistics.median(times["candidate"]))
            results[name] = {
                "query_count": len(queries),
                "old_median_elapsed_ns": prev,
                "candidate_median_elapsed_ns": now,
                "observed_speedup_ratio": round(prev / now, 3) if now else None,
                "candidate_faster_in_this_run": now < prev,
                "old_tracemalloc_peak_bytes": peaks["old"],
                "candidate_tracemalloc_peak_bytes": peaks["candidate"],
                "candidate_lower_peak_in_this_run": peaks["candidate"] < peaks["old"],
                "exact_json_equivalence": True,
                "baseline_source_sha256": original_sha,
                "result_count": sum(x["total_matches"] for x in actual["items"]),
            }
    return {
        "schema": RECIPE,
        "status": RESULT_STATUS,
        "source_baseline_commit": REFERENCE_COMMIT,
        "source_baseline_git_blob": REFERENCE_BLOB,
        "synthetic_rows": rows, "samples_per_variant": repeats,
        "workloads": results,
        "no_upstream_source_executed": True,
        "no_approved_public_metadata_fetched": True,
        "customer_release_approved": False,
        "candidate_production_adopted": False,
        "signed_owner_pack_verified": False,
        "operating_database_writes": 0,
        "external_gets": 0,
        "independent_human_qa_approved": False,
    }


@unittest.skipUnless((REPO / ".git").is_dir(),
                     "requires complete UCIE-only Git checkout")
class UCIEP6RealFirstPartyBeforeAfterTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.old, cls.sha = original_ucie_module()

    def test_01_original_source_comes_from_fixed_old_git_commit(self):
        self.assertEqual(git_blob_sha1(git_readonly(
            "cat-file", "blob", REFERENCE_BLOB)), REFERENCE_BLOB)
        self.assertEqual(len(cls_src := git_readonly(
            "cat-file", "blob", REFERENCE_BLOB)), 9330)
        self.assertEqual(self.sha, sha256(cls_src).hexdigest())
        self.assertNotEqual(candidate.__file__, self.old.__file__)

    def test_02_exact_full_output_equivalence_on_distinct_and_duplicate_keys(self):
        for n in (27, 128, 2048):
            handoff, scenarios = query_cases(n)
            for name, keys, limit, offset in scenarios:
                with self.subTest(rows=n, scenario=name):
                    before = self.old.exact_search_linked_public_candidates(
                        handoff, queries=keys, limit=limit, offset=offset)
                    after = candidate.exact_search_linked_public_candidates(
                        handoff, queries=keys, limit=limit, offset=offset)
                    self.assertEqual(before, old_format(after))
                    self.assertTrue(after["one_pass_source_normalization"])
                    self.assertFalse(after["separate_intermediate_record_catalog_created"])
                    self.assertEqual(after["validated_source_rows"], n)
                    if name == "linear_sparse":
                        self.assertEqual(after["materialized_result_records"], 0)
                        self.assertFalse(after["index_built"])
                    self.assertFalse(after["v1_accepted"])
                    self.assertEqual(after["operating_database_writes"], 0)

    def test_03_original_source_validation_preserved_even_for_nonmatching_item(self):
        data = synthetic_linked_batch(128)
        data["tasks"][-1]["skill_id"] = "unapproved-skill"
        miss = KEY[:3] + ("NO_UCIE_MATCH",)
        for fn in (self.old.exact_search_linked_public_candidates,
                   candidate.exact_search_linked_public_candidates):
            with self.subTest(fn=fn.__module__):
                with self.assertRaises(ValueError):
                    fn(data, queries=(miss,))

    def test_04_original_untrusted_approval_forgery_rejected(self):
        data = synthetic_linked_batch(128)
        data["tasks"][0]["approval"] = True
        for fn in (self.old.exact_search_linked_public_candidates,
                   candidate.exact_search_linked_public_candidates):
            with self.subTest(fn=fn.__module__):
                with self.assertRaises(PolicyError):
                    fn(data, queries=(KEY,))

    def test_05_original_incomplete_ledger_reports_no_go_unchanged(self):
        data = synthetic_linked_batch(128)
        data["status"] = "SOURCE_REVISIONS_PENDING_NO_GO"
        data["pending_source_revisions"] = 1
        for keys in ((KEY,), (KEY, KEY, KEY)):
            old = self.old.exact_search_linked_public_candidates(
                data, queries=keys, offset=10)
            new = candidate.exact_search_linked_public_candidates(
                data, queries=keys, offset=10)
            self.assertEqual(old, old_format(new))
            self.assertEqual(new["items"], [])
            self.assertFalse(new["v1_accepted"])

    def test_06_static_work_ratio_and_memory_not_a_release_gate(self):
        report = measured_comparison(rows=3000, repeats=5)
        self.assertEqual(report["status"], RESULT_STATUS)
        self.assertEqual(report["synthetic_rows"], 3000)
        for scenario in report["workloads"].values():
            self.assertTrue(scenario["exact_json_equivalence"])
            self.assertGreater(scenario["old_median_elapsed_ns"], 0)
            self.assertGreater(scenario["candidate_median_elapsed_ns"], 0)
            self.assertGreater(scenario["old_tracemalloc_peak_bytes"], 0)
            self.assertGreater(scenario["candidate_tracemalloc_peak_bytes"], 0)
        # Time and memory deltas are reported, NOT assumed or converted into
        # automatic promotion, especially across different CI runners.
        self.assertFalse(report["candidate_production_adopted"])
        self.assertFalse(report["customer_release_approved"])
        print("UCIE_P6_FIRST_PARTY_MEASURED=" + json.dumps(report,sort_keys=True))


    def test_07_independent_isolated_python_benchmark_entrypoint(self):
        result = subprocess.run(
            [sys.executable, "-I", "-B",
             str(REPO / "scripts" / "p6_library_one_pass_benchmark.py"),
             "--rows", "256", "--repeats", "3"],
            cwd=REPO, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            timeout=90)
        self.assertEqual(result.returncode, 0, result.stderr.decode("utf-8", errors="replace")[-700:])
        report = json.loads(result.stdout.decode("utf-8"))
        self.assertEqual(report["status"], RESULT_STATUS)
        self.assertEqual(report["synthetic_rows"], 256)
        self.assertEqual(report["source_baseline_commit"], REFERENCE_COMMIT)
        self.assertEqual(set(report["workloads"]), {"linear_sparse", "indexed_repeated"})
        self.assertFalse(report["candidate_production_adopted"])
        self.assertFalse(report["customer_release_approved"])
        self.assertEqual(report["operating_database_writes"], 0)
        self.assertEqual(report["external_gets"], 0)

    def test_08_independent_benchmark_invalid_size_fails_closed(self):
        result = subprocess.run(
            [sys.executable, "-I", "-B",
             str(REPO / "scripts" / "p6_library_one_pass_benchmark.py"),
             "--rows", "6001", "--repeats", "3"],
            cwd=REPO, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            timeout=20)
        self.assertEqual(result.returncode, 2)
        report = json.loads(result.stdout.decode("utf-8"))
        self.assertEqual(report["status"], "FIRST_PARTY_P6_BENCHMARK_FAIL_CLOSED")
        self.assertFalse(report["customer_release_approved"])



if __name__ == "__main__":
    unittest.main()
