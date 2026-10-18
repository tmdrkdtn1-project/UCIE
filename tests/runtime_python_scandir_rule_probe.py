"""Fourth rule calibration: inert Python AST and safe guarded runtime only."""
from __future__ import annotations
from concurrent.futures import ThreadPoolExecutor
import json
import os
from pathlib import Path
import sys
import tempfile
import threading

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from ucie_miner.static_concurrency import inspect_python_scandir_source
from ucie_miner.guarded_scandir import GuardedScandir

POSITIVE = """import os
from concurrent.futures import ThreadPoolExecutor
def run(directory, worker):
    iterator = os.scandir(directory)
    with ThreadPoolExecutor(max_workers=2) as pool:
        return pool.submit(worker, iterator).result()
"""
NEGATIVE = """def run(directory, pool, worker):
    with GuardedScandir(directory) as iterator:
        return pool.submit(worker, iterator).result()
"""


def main() -> None:
    positive = inspect_python_scandir_source(POSITIVE)
    negative = inspect_python_scandir_source(NEGATIVE)
    if (positive["finding_count"] != 1
            or positive["findings"][0]["pattern_code"] !=
               "PY_SCANDIR_SHARED_ITERATOR_RACE"
            or positive["findings"][0]["thread_boundary"] !=
               "EXECUTOR_ARGUMENT"
            or negative["finding_count"] != 0
            or positive["parser_executed_supplied_code"] is not False
            or negative["parser_executed_supplied_code"] is not False):
        raise RuntimeError("fourth-rule AST receipt calibration failed")

    with tempfile.TemporaryDirectory(prefix="ucie-safe-scandir-") as tmp:
        expected = {f"entry_{i}" for i in range(36)}
        for name in expected:
            Path(tmp, name).touch()
        barrier = threading.Barrier(3)
        def worker(it):
            barrier.wait(timeout=5)
            return [entry.name for entry in it]
        with GuardedScandir(tmp) as safe:
            with ThreadPoolExecutor(max_workers=3) as executor:
                futures = [executor.submit(worker, safe) for _ in range(3)]
                actual = [name for f in futures for name in f.result(timeout=10)]
        if len(actual) != 36 or set(actual) != expected:
            raise RuntimeError("guarded multithreaded scandir dropped entries")
    print("UCIE_FOURTH_SAFE_RULE_EVIDENCE=" + json.dumps({
        "schema": "UCIE_SCANDIR_FOURTH_SAFE_REGRESSION_V1",
        "platform": sys.platform,
        "runtime_version": ".".join(map(str, sys.version_info[:3])),
        "public_merge_pr": "python/cpython#153462",
        "candidate_id": "PY_SCANDIR_SHARED_ITERATOR_RACE",
        "synthetic_positive": positive["finding_count"],
        "synthetic_negative": negative["finding_count"],
        "guarded_iterator_entries_verified": len(actual),
        "raw_native_race_executed": False,
        "source_executed": False,
        "independent_before_after_binary_verified": False,
        "auto_promoted": False,
        "owner_approved": False,
    }, sort_keys=True))


if __name__ == "__main__":
    try:
        main()
    except (OSError, RuntimeError, ValueError) as exc:
        print("UCIE_FOURTH_SAFE_RULE_NO_GO=" + str(exc), file=sys.stderr)
        raise SystemExit(1)
