"""P8 bridge: inspect real UCIE experience and test a better query on *real UCIE public ledgers*.

This module bridges the first P8 saved experiment to a meaningful next
question: does the UCIE-authored composite hash lookup preserve exact answers
and reduce work on W04's already source-linked public review metadata?

It is read-only. It DOES NOT benchmark the full W04 substring search API,
apply an index to production, reclassify public leads as verified skills,
import any private project information, use a remote API, or write to the
operating database. No P8 experiment is automatically repeated.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from statistics import median
from time import perf_counter_ns

from .automated_candidate_qa import _checked_handoff
from .experience_evolution import (
    _load_events, _workload_id, WORKLOADS, GENESIS,
    OWNER_OBSERVED_REFERENCE, EvolutionError,
)
from .library_entry import build_library_entry
from .verification_handoff import prepare_verification_handoff

SCHEMA = "UCIE_P8_EXPERIENCE_TO_REAL_CATALOG_BRIDGE_V1"
MAX_CATALOG_ROWS = 1000
MIN_QUERIES, MAX_QUERIES = 8, 96
MAX_REPEATS = 5
MISSING_PURPOSE = "P8_SYNTHETIC_MISSING_EXACT_KEY"


class ExperienceApplicationError(ValueError):
    pass


def experience_library_preview(root: Path) -> dict:
    """Read and verify the original P8 hash chain; do not re-run experiments."""
    events = _load_events(root)
    entries = []
    for event in events:
        receipt = event["receipt"]
        baseline = receipt["baseline_operations"]
        candidate = receipt["candidate_operations"]
        entries.append({
            "library_item_id": event["event_sha256"],
            "kind": "UCIE_EXPERIENCE",
            "experiment_id": receipt["experiment_id"],
            "workload_id": _workload_id(receipt["rows"], receipt["queries"]),
            "dataset_sha256": receipt["dataset_sha256"],
            "source": "UCIE_FIRST_PARTY_SYNTHETIC_EXECUTION",
            "sequence": event["seq"],
            "prev_hash": event["prev_hash"],
            "baseline_operations": baseline,
            "index_build_and_lookup_operations": candidate,
            "operation_reduction_percent": round(
                100.0 * (baseline - candidate) / baseline, 3),
            "baseline_median_ns": receipt["baseline_median_ns"],
            "candidate_median_ns": receipt["candidate_median_ns"],
            "same_workload_runtime_ratio_diagnostic": round(
                receipt["baseline_median_ns"] / receipt["candidate_median_ns"], 3)
                if receipt["candidate_median_ns"] > 0 else None,
            "exact_results_equivalent": receipt["result_equivalent"],
            "decision": receipt["decision"],
            "provenance": "LOCAL_P8_HASH_CHAIN_NOT_THIRD_PARTY_ATTESTATION",
            "real_library_benefit_verified": False,
            "independent_qa": False,
            "production_adopted": False,
        })
    used = {(e["receipt"]["rows"], e["receipt"]["queries"]) for e in events}
    next_case = next((x for x in WORKLOADS if x not in used), None)
    hold = bool(events) and events[-1]["receipt"]["decision"] != (
        "SYNTHETIC_CANDIDATE_WORTH_MORE_TESTING")
    next_case = None if hold else next_case
    return {
        "schema": SCHEMA,
        "status": ("EXPERIENCE_REQUIRES_REVIEW_NO_GO" if hold else
                   "P8_HASH_CHAIN_EXPERIENCE_SEARCHABLE_NO_GO"),
        "shelf": "UCIE_EXPERIENCE",
        "recorded_experiments": len(entries),
        "last_event_sha256": events[-1]["event_sha256"] if events else GENESIS,
        "items": entries,
        "next_unexecuted_workload": (
            {"rows": next_case[0], "queries": next_case[1]}
            if next_case else None),
        "owner_observed_reference": OWNER_OBSERVED_REFERENCE,
        "historical_w08_reference_counted_as_recorded": False,
        "time_samples_comparable_only_within_same_workload": True,
        "source_ledger_modified": False,
        "network_requests": 0,
        "operating_database_writes": 0,
        "other_projects_accessed": False,
        "auto_promoted": False,
        "v1_accepted": False,
    }


def _normalized_catalog_tasks(handoff: dict) -> tuple[tuple[str, str, str, str, str], ...]:
    """Use exactly the same source-linkage validator and W02 contract as W04."""
    complete, tasks = _checked_handoff(handoff)
    if not complete:
        return ()
    if len(tasks) > MAX_CATALOG_ROWS:
        raise ExperienceApplicationError("unbounded public review candidate count")
    rows = []
    for task in tasks:
        if (type(task) is not dict or type(task.get("source")) is not str
                or type(task.get("reference")) is not str
                or type(task.get("pattern_code")) is not str
                or type(task.get("evidence_sha256")) is not str):
            raise ExperienceApplicationError("incomplete public source-linked task")
        kind = ("PREVENTION_RULE" if task.get("stage6_candidate") is not None
                else "PUBLIC_TECHNICAL_EVIDENCE")
        entry = build_library_entry({
            "kind": kind,
            "source_id": "repo:" + task["source"],
            "evidence_reference": task["reference"],
            "evidence_sha256": task["evidence_sha256"],
            "purpose_code": task["pattern_code"],
            "version_scope": "UNDETERMINED",
            "dependencies": [],
        })
        if task.get("skill_id") != entry["skill_profile"]:
            raise ExperienceApplicationError("source skill profile mismatch")
        rows.append((
            entry["source_id"], entry["domain"], entry["kind"],
            entry["purpose_code"], entry["library_item_id"],
        ))
    rows.sort()
    return tuple(rows)


def benchmark_linked_public_catalog(handoff: dict, *,
                                    queries: int = 32,
                                    repeats: int = 3) -> dict:
    """Compare baseline and index for the SAME exact-key public W04 metadata.

    Does not modify the P8 synthetic ledger or run public source code. Index
    creation is INCLUDED in measured operations and elapsed time.
    """
    if (type(queries) is not int or not MIN_QUERIES <= queries <= MAX_QUERIES
            or type(repeats) is not int or not 1 <= repeats <= MAX_REPEATS):
        raise ExperienceApplicationError("unbounded catalog workload")
    catalog = _normalized_catalog_tasks(handoff)
    if not catalog:
        return {
            "schema": SCHEMA,
            "status": "NO_COMPLETE_SOURCE_LINKED_PUBLIC_CATALOG_NO_GO",
            "real_public_catalog_items": 0,
            "experiments_run": 0, "network_requests": 0,
            "operating_database_writes": 0,
            "production_index_applied": False, "v1_accepted": False,
        }
    # Fixed UCIE-created test keys. All successful keys come from the
    # *already approved metadata contract*, never arbitrary upstream text.
    keys = tuple(sorted({row[:4] for row in catalog}))
    requests = []
    for i in range(queries):
        key = keys[i % len(keys)]
        if i % 7 == 0:
            key = (*key[:3], MISSING_PURPOSE)
        requests.append(key)
    baseline_times = []
    candidate_times = []
    mismatch_count = 0
    hits = 0
    for repeat in range(repeats):
        start = perf_counter_ns()
        expected = [
            tuple(row[4] for row in catalog if row[:4] == key)
            for key in requests
        ]
        baseline_times.append(max(0, perf_counter_ns() - start))
        start = perf_counter_ns()
        index = {}
        for row in catalog:
            index.setdefault(row[:4], []).append(row[4])
        actual = [
            tuple(index.get(key, ()))
            for key in requests
        ]
        candidate_times.append(max(0, perf_counter_ns() - start))
        mismatch_count += sum(a != b for a, b in zip(expected, actual))
        if repeat == 0:
            hits = sum(bool(item) for item in expected)
    op_baseline = len(catalog) * queries
    op_indexed = len(catalog) + queries
    digest = hashlib.sha256(json.dumps(
        catalog, ensure_ascii=True, separators=(",", ":")
    ).encode("ascii")).hexdigest()
    return {
        "schema": SCHEMA,
        "status": ("REAL_PUBLIC_METADATA_EXACT_QUERY_EQUIVALENT_UNAPPROVED"
                   if mismatch_count == 0 else
                   "REAL_PUBLIC_METADATA_QUERY_MISMATCH_HOLD"),
        "test_kind": "EXISTING_UCIE_APPROVED_PUBLIC_REVIEW_METADATA_ONLY",
        "public_catalog_sha256": digest,
        "real_public_catalog_items": len(catalog),
        "unique_exact_keys": len(keys),
        "query_count": queries,
        "matched_query_count": hits,
        "missing_query_count": queries - hits,
        "repetitions": repeats,
        "mismatched_query_results": mismatch_count,
        "baseline_scan_operations": op_baseline,
        "candidate_index_build_and_lookup_operations": op_indexed,
        "operation_reduction": op_baseline - op_indexed,
        "baseline_median_ns": int(median(baseline_times)),
        "candidate_median_ns": int(median(candidate_times)),
        "time_guaranteed_faster": False,
        "full_w04_substring_search_benchmarked": False,
        "limited_to_exact_source_domain_kind_purpose_queries": True,
        "upstream_code_executed": False,
        "approved_or_exportable_items": 0,
        "production_index_applied": False,
        "automatic_learning_or_promotion": False,
        "network_requests": 0,
        "operating_database_writes": 0,
        "experience_ledger_writes": 0,
        "v1_accepted": False,
    }


def benchmark_existing_ucie_public_catalog(root: Path, *,
                                           queries: int = 32,
                                           repeats: int = 3) -> dict:
    """Re-use the current W04 Stage10/12/15 validated read-only handoff."""
    if (not isinstance(root, Path) or root.name.casefold() != "ucie"
            or root.is_symlink() or not root.is_dir()):
        raise ExperienceApplicationError("only dedicated UCIE root allowed")
    handoff = prepare_verification_handoff(root)
    return benchmark_linked_public_catalog(handoff, queries=queries, repeats=repeats)


def main() -> int:
    parser = argparse.ArgumentParser(description="UCIE P8 experience and real-public-metadata read-only evaluation")
    parser.add_argument("--ucie-root", type=Path, required=True)
    parser.add_argument("--mode", choices=("experience", "real-catalog"), default="experience")
    parser.add_argument("--queries", type=int, default=32)
    parser.add_argument("--repeats", type=int, default=3)
    args = parser.parse_args()
    try:
        result = (experience_library_preview(args.ucie_root)
                  if args.mode == "experience" else
                  benchmark_existing_ucie_public_catalog(
                      args.ucie_root, queries=args.queries, repeats=args.repeats))
    except (ValueError, OSError) as exc:
        print(json.dumps({
            "schema": SCHEMA, "status": "FAIL_CLOSED",
            "error_type": type(exc).__name__,
            "network_requests": 0, "operating_database_writes": 0,
            "v1_accepted": False,
        }, sort_keys=True))
        return 2
    print(json.dumps(result, sort_keys=True, ensure_ascii=True))
    return 0 if result["status"] not in (
        "REAL_PUBLIC_METADATA_QUERY_MISMATCH_HOLD", "FAIL_CLOSED") else 3


if __name__ == "__main__":
    raise SystemExit(main())
