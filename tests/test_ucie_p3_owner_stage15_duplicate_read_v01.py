"""Owner-only Stage15 repeated-source-read timing, observing original UCIE code.

All instrumentation is local to one test process; original public audit,
SQLite integrity, source provenance and opt-in checks execute unchanged.
No source rows, DB paths or upstream code are emitted.
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

from ucie_miner import public_evidence_chain_audit as audit
from ucie_miner import public_candidate_learning as learning
from ucie_miner.p3_readonly_latency_v01 import _summary


class OwnerStage15ReadOnlyTiming(unittest.TestCase):
    def test_original_audit_and_repeated_reads_are_observed(self):
        root = Path(__file__).resolve().parents[1]
        if (os.name != "nt" or root.is_symlink()
                or root.resolve() != Path("D:/UCIE").resolve()):
            self.skipTest("OWNER_D_UCIE_WINDOWS_ONLY")
        collected = []
        snapshots = []
        # A warmup and two bounded measurements; no reader is replaced.
        for i in range(3):
            readings = {"stage13_history": [], "stage15_fixes": []}

            def measure(original, key):
                def invoke(*args, **kwargs):
                    before = perf_counter_ns()
                    try:
                        return original(*args, **kwargs)
                    finally:
                        elapsed = perf_counter_ns() - before
                        if elapsed < 0:
                            raise RuntimeError("nonmonotonic source read")
                        readings[key].append(elapsed)
                return invoke

            original_history, original_fix = audit._history, audit._fix
            try:
                with ExitStack() as stack:
                    stack.enter_context(patch.object(
                        audit, "_history",
                        measure(original_history, "stage13_history")))
                    stack.enter_context(patch.object(
                        audit, "_fix",
                        measure(original_fix, "stage15_fixes")))
                    start = perf_counter_ns()
                    rows = learning._rows_from_stage15(root)
                    total = perf_counter_ns() - start
                # Original Stage15 performs Stage16 audit then re-reads the
                # source ledgers. A future change in this behavior blocks
                # this diagnostic rather than silently changing semantics.
                if (len(readings["stage13_history"]) != 2
                        or len(readings["stage15_fixes"]) != 2
                        or not rows or total <= 0):
                    raise RuntimeError("stage15 original source read shape drift")
                digest = hashlib.sha256(json.dumps(
                    [(row[0], row[1], row[3]) for row in rows],
                    ensure_ascii=True, separators=(",", ":")
                ).encode("ascii")).hexdigest()
                snapshots.append((len(rows), digest))
                if i:
                    first = readings["stage13_history"][0] + readings[
                        "stage15_fixes"][0]
                    second = readings["stage13_history"][1] + readings[
                        "stage15_fixes"][1]
                    if total < first + second:
                        raise RuntimeError("invalid nested read accounting")
                    collected.append({
                        "whole_stage15": total,
                        "audit_first_history": readings["stage13_history"][0],
                        "audit_first_fix": readings["stage15_fixes"][0],
                        "post_audit_second_history": readings[
                            "stage13_history"][1],
                        "post_audit_second_fix": readings["stage15_fixes"][1],
                        "post_audit_second_combined": second,
                        "other_audit_and_row_processing": total - first - second,
                    })
            except Exception as exc:
                print("UCIE_P3_OWNER_STAGE15_REPEAT_READ_V01="
                      + json.dumps({
                          "status": "FAIL_CLOSED_NO_MEASUREMENT",
                          "error_type": type(exc).__name__,
                          "operating_database_writes": 0,
                      }, sort_keys=True))
                self.fail("OWNER_STAGE15_REPEAT_READ_ACCEPTANCE_NO_GO")
        if len(set(snapshots)) != 1:
            self.fail("PUBLIC_STAGE15_SOURCE_CHANGED_DURING_OBSERVATION")
        data = {
            "schema": "UCIE_P3_OWNER_STAGE15_REPEATED_READ_OBSERVATION_V01",
            "status": "STAGE15_REPEATED_SOURCE_READ_OBSERVED_ONLY",
            "stage15_unverified_public_revisions": snapshots[0][0],
            "stage15_snapshot_sha256": snapshots[0][1],
            "warmups": 1, "samples": 2,
            "phases": {name: _summary([sample[name] for sample in collected])
                       for name in collected[0]},
            "original_audit_invoked": True,
            "original_readers_invoked_twice_per_source": True,
            "source_validation_bypassed": False,
            "operating_database_writes": 0,
            "network_requests": 0,
            "production_code_modified": False,
            "safe_refactor_proven": False,
        }
        print("UCIE_P3_OWNER_STAGE15_REPEAT_READ_V01="
              + json.dumps(data, sort_keys=True))
        self.assertGreater(data["stage15_unverified_public_revisions"], 0)
        self.assertFalse(data["source_validation_bypassed"])
        self.assertFalse(data["safe_refactor_proven"])


if __name__ == "__main__":
    unittest.main()
