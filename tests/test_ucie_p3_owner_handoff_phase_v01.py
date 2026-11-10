"""Owner-only observational phase breakdown of the existing UCIE public handoff.

The production handoff and its validation are NOT modified; in this isolated
one-test process only, wrappers around exact original functions time phases
and immediately restore originals. No raw public rows or private data output.
"""
from __future__ import annotations

from contextlib import ExitStack
import hashlib
import json
import os
from pathlib import Path
from time import perf_counter_ns
import unittest
from unittest.mock import patch

from ucie_miner import verification_handoff as vh
from ucie_miner.p3_readonly_latency_v01 import _summary


class OwnerP3HandoffPhaseReadOnly(unittest.TestCase):
    def test_owner_handoff_stage_timing_no_source_bypass(self):
        root = Path(__file__).resolve().parents[1]
        if (os.name != "nt" or root.is_symlink()
                or root.resolve() != Path("D:/UCIE").resolve()):
            self.skipTest("OWNER_D_UCIE_WINDOWS_ONLY")

        observed = []
        snapshots = []
        # 1 warmup + 2 independent samples only. All wrappers call the
        # original source-validation functions without changing their output.
        for iteration in range(3):
            samples = {}
            names = ("_expected_record_map", "_rows_from_stage10",
                     "_rows_from_stage15", "_review_records")
            originals = {name: getattr(vh, name) for name in names}

            def timed(original, key):
                def invoke(*args, **kwargs):
                    before = perf_counter_ns()
                    try:
                        return original(*args, **kwargs)
                    finally:
                        elapsed = perf_counter_ns() - before
                        if elapsed < 0:
                            raise RuntimeError("nonmonotonic phase clock")
                        samples[key] = samples.get(key, 0) + elapsed
                return invoke

            try:
                with ExitStack() as stack:
                    for name in names:
                        stack.enter_context(patch.object(
                            vh, name, timed(originals[name], name)))
                    before = perf_counter_ns()
                    report = vh.prepare_verification_handoff(root)
                    total = perf_counter_ns() - before
                if (report.get("status") != "LINKED_UNVERIFIED_NO_GO"
                        or report.get("auto_promoted") is not False
                        or report.get("persistent_writes") != 0
                        or report.get("approved_rules") != 0
                        or type(report.get("tasks")) is not list
                        or not report["tasks"]
                        or any(key not in samples for key in names)
                        or not 0 <= samples["_expected_record_map"] <= total):
                    raise RuntimeError("public-source handoff incomplete")
                ids = [item["candidate_id_sha256"] for item in report["tasks"]]
                source_digest = hashlib.sha256(
                    json.dumps(ids, ensure_ascii=True,
                               separators=(",", ":")).encode("ascii")
                ).hexdigest()
                snapshots.append((len(ids), source_digest))
                if iteration:
                    expected = samples["_expected_record_map"]
                    nested = samples["_rows_from_stage10"] + samples[
                        "_rows_from_stage15"]
                    if expected < nested:
                        raise RuntimeError("phase accounting inconsistent")
                    observed.append({
                        "total_handoff": total,
                        "stage10_reader": samples["_rows_from_stage10"],
                        "stage15_reader": samples["_rows_from_stage15"],
                        "source_map_plus_reconstruction": expected,
                        "source_map_other": expected - nested,
                        "review_ledger_and_task_render": total - expected,
                        "review_records": samples["_review_records"],
                    })
                else:
                    del report
            except Exception as exc:
                print("UCIE_P3_OWNER_HANDOFF_PHASE_V01=" +
                      json.dumps({"status": "FAIL_CLOSED_NO_MEASUREMENT",
                                  "error_type": type(exc).__name__,
                                  "operating_database_writes": 0},
                                 sort_keys=True))
                self.fail("OWNER_P3_HANDOFF_PHASE_ACCEPTANCE_NO_GO")

        if len(set(snapshots)) != 1:
            self.fail("PUBLIC_REVIEW_SOURCE_CHANGED_DURING_MEASUREMENT")
        summary = {
            "schema": "UCIE_P3_OWNER_HANDOFF_SOURCE_PHASE_READONLY_V01",
            "status": "OWNER_READONLY_PHASE_TIMINGS_OBSERVED_NOT_OPTIMIZED",
            "source_linked_public_rows": snapshots[0][0],
            "untrusted_public_ids_digest_sha256": snapshots[0][1],
            "samples": 2,
            "warmups": 1,
            "phase_milliseconds": {
                key: _summary([sample[key] for sample in observed])
                for key in observed[0]
            },
            "source_validation_bypassed": False,
            "customer_http_latency_measured": False,
            "production_cache_or_index_modified": False,
            "operating_database_writes": 0,
            "network_requests": 0,
            "owner_release_approved": False,
        }
        print("UCIE_P3_OWNER_HANDOFF_PHASE_V01=" +
              json.dumps(summary, ensure_ascii=True, sort_keys=True))
        self.assertGreater(summary["source_linked_public_rows"], 0)
        self.assertFalse(summary["source_validation_bypassed"])
        self.assertEqual(summary["operating_database_writes"], 0)


if __name__ == "__main__":
    unittest.main()
