"""W08: real first-party UCIE capability experiment on a synthetic Library index.

Compares two executable, UCIE-authored algorithms over identical deterministic
public-domain-shaped *synthetic* records:
  baseline: linear exact-match scan for each catalog query
  candidate: build a composite hash index, then exact-key lookups

This is a bounded feasibility experiment, NOT an evaluated public PR/skill,
production speed certification, model training, library migration or rollout.
No external data, credentials, files, database, network or source code used.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
from statistics import median
from time import perf_counter_ns

from .product_plan import APPROVED_REPOSITORIES
from .public_discovery import SOURCE_SKILL
from .skill_profiles import PROFILE

SCHEMA = "UCIE_W08_OWNED_SYNTHETIC_CAPABILITY_EVALUATION_V1"
EXPERIMENT_ID = "UCIE_LIBRARY_EXACT_KEY_INDEX_EXPERIMENT_V1"
KINDS = ("DEVELOPMENT_ENGINE", "REUSABLE_SKILL", "LEARNING_LOGIC")
PURPOSES = (
    "ENGINE_INCREMENTAL_BUILD", "ENGINE_WORKFLOW_ORCHESTRATION",
    "SKILL_TEST_AUTOMATION", "SKILL_RELEASE_AUTOMATION",
    "LEARNING_FEEDBACK_LOOP",
)
NO_MATCH = "NO_SUCH_UCIE_SYNTHETIC_PURPOSE"
MIN_ROWS, MAX_ROWS = 256, 4096
MIN_QUERIES, MAX_QUERIES = 16, 96
MAX_REPEATS = 5


class CapabilityEvaluationError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class CatalogItem:
    """Only synthetic UCIE-generated fields, never an imported source record."""
    synthetic_id: str
    source_id: str
    domain: str
    kind: str
    purpose: str


@dataclass(frozen=True, slots=True)
class CatalogQuery:
    source_id: str
    domain: str
    kind: str
    purpose: str


def _contract(rows: int, queries: int, repeats: int) -> None:
    if (type(rows) is not int or not MIN_ROWS <= rows <= MAX_ROWS
            or type(queries) is not int or not MIN_QUERIES <= queries <= MAX_QUERIES
            or type(repeats) is not int or not 1 <= repeats <= MAX_REPEATS):
        raise CapabilityEvaluationError("bounded synthetic workload required")
    if (len(APPROVED_REPOSITORIES) != 5 or
            any(s not in SOURCE_SKILL or SOURCE_SKILL[s] not in PROFILE
                for s in APPROVED_REPOSITORIES)):
        raise CapabilityEvaluationError("approved public domain taxonomy changed")


def synthetic_catalog(count: int) -> tuple[CatalogItem, ...]:
    """No random seeds, external files, copied source snippets or private data."""
    _contract(count, MIN_QUERIES, 1)
    records = []
    for i in range(count):
        source = APPROVED_REPOSITORIES[i % len(APPROVED_REPOSITORIES)]
        domain = PROFILE[SOURCE_SKILL[source]]["domain"]
        # Use distinct strides to exercise all combinations, avoiding
        # artificial one-dimensional correlation in candidate match counts.
        kind = KINDS[(i // 5) % len(KINDS)]
        purpose = PURPOSES[(i // 15) % len(PURPOSES)]
        records.append(CatalogItem(
            f"UCIE_SYNTH_{i:05d}", "repo:" + source,
            domain, kind, purpose,
        ))
    return tuple(records)


def synthetic_queries(count: int) -> tuple[CatalogQuery, ...]:
    _contract(MIN_ROWS, count, 1)
    queries = []
    for i in range(count):
        source = APPROVED_REPOSITORIES[(i * 3 + i // 5) % 5]
        domain = PROFILE[SOURCE_SKILL[source]]["domain"]
        kind = KINDS[(i // 3) % len(KINDS)]
        purpose = NO_MATCH if i % 8 == 0 else PURPOSES[(i // 7) % len(PURPOSES)]
        queries.append(CatalogQuery("repo:" + source, domain, kind, purpose))
    return tuple(queries)


def linear_search(catalog: tuple[CatalogItem, ...],
                  query: CatalogQuery) -> tuple[tuple[str, ...], int]:
    """Reference algorithm, one exact filter comparison per catalog item."""
    result = tuple(row.synthetic_id for row in catalog
                   if (row.source_id, row.domain, row.kind, row.purpose)
                   == (query.source_id, query.domain, query.kind, query.purpose))
    return result, len(catalog)


def build_exact_index(catalog: tuple[CatalogItem, ...]
                      ) -> tuple[dict[tuple[str, str, str, str], tuple[str, ...]], int]:
    """Reusable first-party query index; records are only synthetic metadata."""
    temporary: dict[tuple[str, str, str, str], list[str]] = {}
    for row in catalog:
        key = (row.source_id, row.domain, row.kind, row.purpose)
        temporary.setdefault(key, []).append(row.synthetic_id)
    return {key: tuple(ids) for key, ids in temporary.items()}, len(catalog)


def indexed_search(index: dict[tuple[str, str, str, str], tuple[str, ...]],
                   query: CatalogQuery) -> tuple[tuple[str, ...], int]:
    """One dictionary lookup, including on zero-match queries."""
    return index.get((query.source_id, query.domain, query.kind, query.purpose),
                     ()), 1


def _measure_linear(catalog: tuple[CatalogItem, ...],
                    queries: tuple[CatalogQuery, ...]) -> tuple[list[tuple[str, ...]], int, int]:
    start = perf_counter_ns()
    output, examined = [], 0
    for query in queries:
        ids, checked = linear_search(catalog, query)
        output.append(ids)
        examined += checked
    return output, examined, max(0, perf_counter_ns() - start)


def _measure_indexed(catalog: tuple[CatalogItem, ...],
                     queries: tuple[CatalogQuery, ...]) -> tuple[list[tuple[str, ...]], int, int, int]:
    start = perf_counter_ns()
    index, build_checks = build_exact_index(catalog)
    output, lookups = [], 0
    for query in queries:
        ids, count = indexed_search(index, query)
        output.append(ids)
        lookups += count
    return output, build_checks + lookups, max(0, perf_counter_ns() - start), len(index)


def evaluate_synthetic_library_index(*, rows: int = 1536, queries: int = 48,
                                     repeats: int = 3) -> dict:
    """Run both real implementations and compare every exact result.

    Timing is diagnostic-only and can regress on a particular host. Operation
    counts include *building* the index; no single-loop free indexing credit.
    Synthetic correctness is NOT production correctness or performance approval.
    """
    _contract(rows, queries, repeats)
    catalog, requests = synthetic_catalog(rows), synthetic_queries(queries)
    dataset_sha = hashlib.sha256(
        json.dumps([
            [r.synthetic_id, r.source_id, r.domain, r.kind, r.purpose]
            for r in catalog
        ], separators=(",", ":"), ensure_ascii=True).encode("ascii")
    ).hexdigest()
    linear_times, indexed_times = [], []
    checked_baseline = checked_indexed = key_count = 0
    differences: list[int] = []
    no_match_queries = 0
    matched_queries = 0
    for run in range(repeats):
        reference, checked_baseline, elapsed_linear = _measure_linear(catalog, requests)
        actual, checked_indexed, elapsed_index, key_count = _measure_indexed(catalog, requests)
        linear_times.append(elapsed_linear)
        indexed_times.append(elapsed_index)
        if run == 0:
            no_match_queries = sum(not ids for ids in reference)
            matched_queries = len(reference) - no_match_queries
        differences.extend(i for i, (old, new) in enumerate(zip(reference, actual))
                           if old != new)
    equivalent = not differences
    fewer_checks = checked_indexed < checked_baseline
    status = ("SYNTHETIC_EQUIVALENCE_AND_OPERATION_REDUCTION_OBSERVED_NO_GO"
              if equivalent and fewer_checks else
              "SYNTHETIC_EVALUATION_REQUIRES_REVIEW_NO_GO")
    return {
        "schema": SCHEMA,
        "experiment_id": EXPERIMENT_ID,
        "status": status,
        "test_kind": "UCIE_AUTHORED_SYNTHETIC_LIBRARY_SEARCH",
        "baseline_algorithm": "LINEAR_EXACT_MATCH_SCAN_V1",
        "candidate_algorithm": "COMPOSITE_HASH_LOOKUP_V1",
        "dataset_sha256": dataset_sha,
        "synthetic_item_count": len(catalog),
        "query_count": len(requests),
        "measurement_repetitions": repeats,
        "matching_query_count": matched_queries,
        "no_match_query_count": no_match_queries,
        "unique_index_keys": key_count,
        "reference_comparisons_per_run": checked_baseline,
        "candidate_build_plus_lookup_operations_per_run": checked_indexed,
        "operation_reduction": checked_baseline - checked_indexed,
        "operation_reduction_observed": fewer_checks,
        "exact_result_equivalence_observed": equivalent,
        "mismatched_query_count": len(set(differences)),
        "baseline_median_elapsed_ns": int(median(linear_times)),
        "candidate_median_elapsed_ns": int(median(indexed_times)),
        "elapsed_time_guaranteed_faster": False,
        "performance_on_real_catalog_measured": False,
        "upstream_capability_implemented_or_verified": False,
        "public_source_data_used": False,
        "ucie_experience_record": {
            "kind": "UCIE_EXPERIENCE",
            "experiment_id": EXPERIMENT_ID,
            "dataset_sha256": dataset_sha,
            "outcome": status,
            "limitations": "SYNTHETIC_ONLY_NOT_REAL_USER_WORKLOAD",
            "revision_ready": False,
            "production_adopted": False,
            "human_review_required": True,
        },
        "network_requests": 0,
        "database_writes": 0,
        "project_data_accessed": False,
        "model_weights_changed": False,
        "scheduler_registered": False,
        "auto_promoted": False,
        "owner_approved": False,
        "production_approved": False,
        "v1_accepted": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="UCIE-only W08 safe synthetic Library query algorithm experiment")
    parser.add_argument("--rows", type=int, default=1536)
    parser.add_argument("--queries", type=int, default=48)
    parser.add_argument("--repeats", type=int, default=3)
    args = parser.parse_args()
    try:
        result = evaluate_synthetic_library_index(
            rows=args.rows, queries=args.queries, repeats=args.repeats)
    except CapabilityEvaluationError as exc:
        print(json.dumps({
            "schema": SCHEMA, "status": "BOUNDED_SYNTHETIC_EVALUATION_REJECTED_NO_GO",
            "error_type": type(exc).__name__,
            "network_requests": 0, "database_writes": 0,
            "production_approved": False,
        }, sort_keys=True))
        return 2
    print(json.dumps(result, ensure_ascii=True, sort_keys=True))
    return 0 if result["exact_result_equivalence_observed"] else 3


if __name__ == "__main__":
    raise SystemExit(main())
