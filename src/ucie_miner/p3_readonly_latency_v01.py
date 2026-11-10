"""P3 owner-triggered W04/engine timing baseline, never an optimization gate.

Only the existing UCIE public source-linked handoff is read. No persistent
index, host app, scheduler, external source, approval or deployment changes.
This is an observational benchmark; a slow stage is not a proven root cause.
"""
from __future__ import annotations

import argparse
import json
from math import ceil
from pathlib import Path
from platform import python_version, system
from statistics import median
from time import perf_counter_ns

from .experience_application import (
    SCHEMA as ENGINE_SCHEMA, benchmark_linked_public_catalog,
)
from .library_search import SCHEMA as W04_SCHEMA, search_linked_public_candidates
from .verification_handoff import prepare_verification_handoff

SCHEMA = "UCIE_P3_W04_ENGINE_READONLY_LATENCY_BASELINE_V01"
SEARCH_TERMS = ("python", "git", "")
MAX_SAMPLES = 5
MAX_WARMUPS = 2


class BaselineError(ValueError):
    pass


def _root(root: Path) -> Path:
    if (not isinstance(root, Path) or root.name.casefold() != "ucie"
            or root.is_symlink() or not root.is_dir()):
        raise BaselineError("dedicated UCIE source root is required")
    return root


def _time_once(action, clock):
    start = clock()
    value = action()
    finish = clock()
    if (type(start) is not int or type(finish) is not int
            or finish < start):
        raise BaselineError("invalid monotonic timing observation")
    return value, finish - start


def _summary(ns: list[int]) -> dict:
    if not ns or any(type(x) is not int or x < 0 for x in ns):
        raise BaselineError("invalid bounded timing samples")
    ordered = sorted(ns)
    return {
        "samples": len(ordered),
        "median_ms": round(median(ordered) / 1_000_000, 3),
        "p95_nearest_rank_ms": round(
            ordered[ceil(0.95 * len(ordered)) - 1] / 1_000_000, 3),
        "max_ms": round(ordered[-1] / 1_000_000, 3),
    }


def _check_search(result: dict, query: str, source_count: int | None) -> int:
    if (type(result) is not dict or result.get("schema") != W04_SCHEMA
            or result.get("status") != "READ_ONLY_UNVERIFIED_LIBRARY_SEARCH_NO_GO"
            or result.get("query") != query.casefold().strip()
            or result.get("network_requests") != 0
            or result.get("operating_database_writes") != 0
            or result.get("approved_or_exportable_items") != 0
            or result.get("auto_promoted") is not False
            or result.get("v1_library_accepted") is not False
            or type(result.get("source_linked_count")) is not int
            or result["source_linked_count"] < 1
            or type(result.get("total_matches")) is not int
            or result["total_matches"] < 0
            or type(result.get("returned_count")) is not int
            or not 0 <= result["returned_count"] <= 10
            or type(result.get("items")) is not list
            or len(result["items"]) != result["returned_count"]
            or (source_count is not None
                and result["source_linked_count"] != source_count)):
        raise BaselineError("W04 source/safety/count contract unavailable")
    if any(
            type(item) is not dict
            or item.get("lifecycle") != "UNVERIFIED_CANDIDATE_ONLY"
            or item.get("human_approved") is not False
            or item.get("export_allowed") is not False
            for item in result["items"]):
        raise BaselineError("W04 returned unapproved/public candidate state drift")
    return result["source_linked_count"]


def _check_engine(result: dict, source_count: int) -> str:
    if (type(result) is not dict or result.get("schema") != ENGINE_SCHEMA
            or result.get("status") !=
            "REAL_PUBLIC_METADATA_EXACT_QUERY_EQUIVALENT_UNAPPROVED"
            or result.get("real_public_catalog_items") != source_count
            or result.get("query_count") != 24
            or result.get("repetitions") != 2
            or result.get("mismatched_query_results") != 0
            or result.get("network_requests") != 0
            or result.get("operating_database_writes") != 0
            or result.get("production_index_applied") is not False
            or result.get("automatic_learning_or_promotion") is not False
            or result.get("upstream_code_executed") is not False
            or result.get("full_w04_substring_search_benchmarked") is not False
            or result.get("approved_or_exportable_items") != 0
            or result.get("v1_accepted") is not False):
        raise BaselineError("P8 engine source/equivalence/safety gate unavailable")
    digest = result.get("public_catalog_sha256")
    if (type(digest) is not str or len(digest) != 64
            or any(c not in "0123456789abcdef" for c in digest)):
        raise BaselineError("invalid exact public catalog snapshot fingerprint")
    if any(type(result.get(key)) is not int or result[key] < 0 for key in (
            "baseline_median_ns", "candidate_median_ns")):
        raise BaselineError("invalid internal exact-query timings")
    return digest


def measure_baseline(root: Path, *, samples: int = 3, warmups: int = 1,
                     loader=prepare_verification_handoff,
                     search=search_linked_public_candidates,
                     engine=benchmark_linked_public_catalog,
                     clock=perf_counter_ns) -> dict:
    """Bounded source reload + W04 substring + P8 exact-key engine timings.

    Dependency injection is for UCIE-owned tests. The CLI always uses fixed,
    validated production readers; it never reads other project data.
    """
    root = _root(root)
    if (type(samples) is not int or not 1 <= samples <= MAX_SAMPLES
            or type(warmups) is not int or not 0 <= warmups <= MAX_WARMUPS):
        raise BaselineError("bounded repetitions required")
    load_times: list[int] = []
    search_times: dict[str, list[int]] = {term: [] for term in SEARCH_TERMS}
    engine_times: list[int] = []
    scan_times: list[int] = []
    index_times: list[int] = []
    initial_digest: str | None = None
    source_count: int | None = None
    match_counts: dict[str, int] = {}
    for iteration in range(samples + warmups):
        handoff, load_ns = _time_once(lambda: loader(root), clock)
        current_count = None
        current_counts = {}
        current_search_ns = {}
        for term in SEARCH_TERMS:
            result, elapsed = _time_once(
                lambda term=term: search(handoff, query=term, limit=10,
                                         group_revisions=False, offset=0),
                clock)
            current_count = _check_search(result, term, current_count)
            current_counts[term] = result["total_matches"]
            current_search_ns[term] = elapsed
        engine_result, engine_ns = _time_once(
            lambda: engine(handoff, queries=24, repeats=2), clock)
        digest = _check_engine(engine_result, current_count)
        if initial_digest is None:
            initial_digest = digest
            source_count = current_count
            match_counts = current_counts
        elif (digest != initial_digest or source_count != current_count
              or current_counts != match_counts):
            raise BaselineError("public snapshot changed during timing")
        if iteration >= warmups:
            load_times.append(load_ns)
            engine_times.append(engine_ns)
            scan_times.append(engine_result["baseline_median_ns"])
            index_times.append(engine_result["candidate_median_ns"])
            for term in SEARCH_TERMS:
                search_times[term].append(current_search_ns[term])
    return {
        "schema": SCHEMA,
        "status": "OBSERVATIONAL_BASELINE_ONLY_NO_OPTIMIZATION",
        "measurement_scope": "THIS_EXECUTING_PROCESS_NOT_OWNER_HOST_ATTESTATION",
        "python_version": python_version(),
        "os_family": system(),
        "warmups": warmups,
        "samples": samples,
        "source_linked_public_rows": source_count,
        "in_run_public_catalog_sha256": initial_digest,
        "read_and_validate_handoff": _summary(load_times),
        "w04_substring_search_on_loaded_handoff": {
            (term if term else "empty_query"): {
                "total_matches": match_counts[term],
                **_summary(search_times[term]),
            } for term in SEARCH_TERMS
        },
        "p8_exact_public_catalog_engine_on_loaded_handoff": {
            "query_count_per_call": 24,
            "internal_repeats_per_call": 2,
            "full_call": _summary(engine_times),
            "internal_linear_scan": _summary(scan_times),
            "internal_ephemeral_index_including_build": _summary(index_times),
        },
        "performance_root_cause_proven": False,
        "timing_or_speedup_guaranteed": False,
        "customer_http_latency_measured": False,
        "operating_database_writes": 0,
        "network_requests": 0,
        "persistent_index_created": False,
        "owner_release_approved": False,
        "auto_promoted": False,
        "v1_accepted": False,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="UCIE P3 read-only latency observation")
    parser.add_argument("--ucie-root", type=Path, required=True)
    parser.add_argument("--samples", type=int, default=3)
    parser.add_argument("--warmups", type=int, default=1)
    args = parser.parse_args(argv)
    try:
        result = measure_baseline(
            args.ucie_root, samples=args.samples, warmups=args.warmups)
    except Exception as exc:
        print(json.dumps({
            "schema": SCHEMA, "status": "FAIL_CLOSED_NO_MEASUREMENT",
            "error_type": type(exc).__name__,
            "network_requests": 0, "operating_database_writes": 0,
            "v1_accepted": False,
        }, sort_keys=True))
        return 2
    print(json.dumps(result, ensure_ascii=True, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
