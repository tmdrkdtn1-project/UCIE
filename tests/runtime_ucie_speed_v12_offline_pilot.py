"""UCIE SPEED V1.2 L2: disposable synthetic-only host-independent pilot.

Called only in explicitly pinned PR CI or manually for a no-network check.
Never reads owner private files, public APIs, existing UCIE runtime data,
other repositories, credentials, services, or the hourly scheduler.
Every SQLite database is in a fresh TemporaryDirectory with closed handles.
"""
from __future__ import annotations

from collections import Counter
import json
from pathlib import Path
from statistics import median
import sqlite3
import tempfile
import threading
import time

from ucie_miner.core import PUBLIC_SOURCES, mine_once

SCHEMA = "UCIE_SPEED_V12_OFFLINE_PILOT_V1"
LIST = "pulls?state=closed&sort=updated&direction=desc&per_page=20"
FILES = "/pulls/42/files?per_page=30"
SAMPLES_PER_MODE = 8
SYNTHETIC_LIST_WAIT_SECONDS = 0.09


def _p95_ms(values: list[float]) -> float:
    ordered = sorted(values)
    # Nearest-rank percentile, no population SLA implication.
    return round(ordered[max(0, ((95 * len(ordered) + 99) // 100) - 1)], 3)


def _one_synthetic_cycle(workers: int) -> tuple[float, tuple, dict]:
    timings: dict[str, tuple[int, int]] = {}
    call_counts: Counter[str] = Counter()
    counts_lock = threading.Lock()

    def fake_public_get(url: str) -> object:
        if not any(
            url.startswith("https://api.github.com/repos/" + source + "/")
            for source in PUBLIC_SOURCES
        ):
            raise AssertionError("UCIE synthetic pilot URL outside approved source")
        source = next(source for source in PUBLIC_SOURCES if
                      url.startswith("https://api.github.com/repos/" + source + "/"))
        if url.endswith(LIST):
            started = time.perf_counter_ns()
            time.sleep(SYNTHETIC_LIST_WAIT_SECONDS)
            finished = time.perf_counter_ns()
            with counts_lock:
                timings[source] = started, finished
                call_counts[source + ":LIST"] += 1
            return [{
                "number": 42,
                "title": "Fix regression in safe synthetic test",
                "merged_at": "2026-10-01T10:00:00Z",
            }]
        if url.endswith(FILES):
            with counts_lock:
                call_counts[source + ":FILES"] += 1
            suffix = ".py" if source == PUBLIC_SOURCES[0] else ".ps1"
            return [{
                "filename": "tests/synthetic" + suffix,
                "patch": "+raise RuntimeError('synthetic')" if suffix == ".py"
                         else "+throw 'synthetic'",
            }]
        raise AssertionError("unapproved UCIE pilot route")

    with tempfile.TemporaryDirectory(prefix="ucie_speed_v12_offline_") as workspace:
        repo_root = Path(workspace)
        t0 = time.perf_counter_ns()
        result = mine_once(
            repo_root,
            fetch=fake_public_get,
            sources=PUBLIC_SOURCES,
            max_new_per_source=2,
            crosscheck_origin=False,
            read_workers=workers,
        )
        elapsed_ms = (time.perf_counter_ns() - t0) / 1_000_000
        # Explicit sqlite3.close: Windows 3.15 locks files if a connection
        # context-manager is wrongly assumed to close the DB handle.
        db = sqlite3.connect(repo_root / "runtime" / "public_miner.sqlite3")
        try:
            rows = tuple(db.execute(
                "SELECT source,pr_number,evidence_sha256,tags_json,status "
                "FROM candidates ORDER BY source,pr_number"
            ).fetchall())
            runs = tuple(db.execute(
                "SELECT sources_count,added_candidates,status FROM runs"
            ).fetchall())
        finally:
            db.close()

    expected = {source + ":" + kind: 1 for source in PUBLIC_SOURCES
                for kind in ("LIST", "FILES")}
    if dict(call_counts) != expected:
        raise AssertionError("unexpected count of synthetic list/file routes")
    if result != {
        "status": "COLLECTED_UNVERIFIED",
        "sources_checked": 2,
        "new_candidates": 2,
        "incomplete_provenance": 2,
        "public_pr_crosschecked": 0,
        "verification_pass": 0,
        "production_approved": False,
    }:
        raise AssertionError("unverified-only result contract changed")
    if len(rows) != 2 or runs != ((2, 2, "COLLECTED_UNVERIFIED"),):
        raise AssertionError("SQLite single-writer/receipt changed")
    if len(timings) != 2:
        raise AssertionError("missing source timing")
    pair = tuple(timings[source] for source in PUBLIC_SOURCES)
    overlap = max(pair[0][0], pair[1][0]) < min(pair[0][1], pair[1][1])
    if overlap != (workers == 2):
        raise AssertionError("unexpected serial/parallel independent GET behavior")
    return elapsed_ms, (rows, runs), {
        "requests_total": sum(call_counts.values()),
        "list_overlap_verified": overlap,
        "dependent_file_gets": 2,
    }


def main() -> None:
    results: dict[int, list[float]] = {1: [], 2: []}
    consistent_rows = True
    observed_parallel = True
    requests = 0

    # Warm-up outside reported timing stats, all synthetic and disposable.
    for workers in (1, 2):
        _one_synthetic_cycle(workers)

    # Alternate mode order to limit warm cache / scheduling order bias.
    for index in range(SAMPLES_PER_MODE):
        order = (1, 2) if index % 2 == 0 else (2, 1)
        passes: dict[int, tuple] = {}
        for workers in order:
            elapsed, snapshot, checks = _one_synthetic_cycle(workers)
            results[workers].append(elapsed)
            passes[workers] = snapshot
            requests += checks["requests_total"]
            observed_parallel &= (
                checks["list_overlap_verified"] is (workers == 2)
            )
        consistent_rows &= passes[1] == passes[2]

    if not consistent_rows or not observed_parallel:
        raise AssertionError("quality or concurrency invariant violated")

    a, b = results[1], results[2]
    report = {
        "schema": SCHEMA,
        "project_id": "UCIE",
        "status": "SYNTHETIC_OFFLINE_PILOT_PASS_NOT_HOST_OPERATION",
        "environment": "CURRENT_PYTHON_PROCESS_EPHEMERAL_TEMP_SQLITE",
        "samples_per_mode": SAMPLES_PER_MODE,
        "synthetic_list_wait_ms": int(SYNTHETIC_LIST_WAIT_SECONDS * 1000),
        "serial_median_ms": round(median(a), 3),
        "parallel_median_ms": round(median(b), 3),
        "serial_p95_ms": _p95_ms(a),
        "parallel_p95_ms": _p95_ms(b),
        "median_speedup": round(median(a) / median(b), 3),
        "synthetic_get_requests": requests,
        "actual_network_requests": 0,
        "actual_github_rate_limit_verification": False,
        "actual_owner_host_windows_verified": False,
        "live_pilot_verified": False,
        "parallel_list_reads_overlapped": True,
        "serial_parallel_sqlite_rows_identical": True,
        "production_miner_or_schedule_modified": False,
        "runtime_db_or_receipt_modified": False,
        "external_code_executed": False,
        "automatic_rule_promotion": False,
        "performance_2x_live_pass": False,
    }
    print("UCIE_SPEED_V12_OFFLINE_PILOT=" + json.dumps(
        report, sort_keys=True, separators=(",", ":")
    ))


if __name__ == "__main__":
    main()
