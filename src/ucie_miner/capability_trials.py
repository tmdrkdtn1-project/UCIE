"""UCIE W05 -> P8: bounded first-party engine, skill, learning-logic trials.

Public W05 merged PR title cues are unverified provenance *only*. All code
executed here is UCIE-authored; original public PR code is never executed.
No imports from any other project, HTTP, DB, scheduler or automatic promotion.
"""
from __future__ import annotations

from hashlib import sha256
import argparse
import json
from statistics import median
from time import perf_counter_ns

SCHEMA = "UCIE_W05_P8_FIRST_PARTY_CAPABILITY_TRIALS_V1"
RECIPES = {
    "ENGINE_INCREMENTAL_BUILD": ("DEVELOPMENT_ENGINE", "CHAIN_REBUILD_REUSE_V1"),
    "SKILL_TEST_AUTOMATION": ("REUSABLE_SKILL", "TAGGED_TEST_CASE_LOOKUP_V1"),
    "LEARNING_FEEDBACK_LOOP": ("LEARNING_LOGIC", "INCREMENTAL_FEEDBACK_AGGREGATE_V1"),
}
KNOWN_NOT_IMPLEMENTED = frozenset({
    "ENGINE_WORKFLOW_ORCHESTRATION", "SKILL_RELEASE_AUTOMATION",
})
MAX_FEED_TRIALS = 30


class CapabilityTrialError(ValueError):
    pass


def _bounds(rows: int, queries: int, repeats: int) -> None:
    if (type(rows) is not int or not 64 <= rows <= 512
            or type(queries) is not int or not 8 <= queries <= 64
            or type(repeats) is not int or not 1 <= repeats <= 5):
        raise CapabilityTrialError("bounded UCIE synthetic workload required")


def _chain(values: tuple[int, ...]) -> tuple[str, ...]:
    prev = "GENESIS"
    result = []
    for i, value in enumerate(values):
        prev = sha256(f"{prev}:{i}:{value}".encode("ascii")).hexdigest()
        result.append(prev)
    return tuple(result)


def _chain_baseline(n: int, q: int) -> tuple[tuple, int]:
    base = tuple(i % 11 for i in range(n))
    output = []
    for j in range(q):
        index = n - 1 - (j % 8)
        values = list(base)
        values[index] += 1 + j
        output.append(_chain(tuple(values)))
    return tuple(output), n * q


def _chain_improved(n: int, q: int) -> tuple[tuple, int]:
    base = tuple(i % 11 for i in range(n))
    cached = _chain(base)
    output, cost = [], n
    for j in range(q):
        index = n - 1 - (j % 8)
        prefix = list(cached[:index])
        prev = cached[index - 1]
        for k in range(index, n):
            value = base[k] + (1 + j if k == index else 0)
            prev = sha256(f"{prev}:{k}:{value}".encode("ascii")).hexdigest()
            prefix.append(prev)
            cost += 1
        output.append(tuple(prefix))
    return tuple(output), cost


def _tests_baseline(n: int, q: int) -> tuple[tuple, int]:
    tags = tuple(i % 8 for i in range(n))
    return tuple(tuple(i for i, tag in enumerate(tags) if tag == j % 9)
                 for j in range(q)), n * q


def _tests_improved(n: int, q: int) -> tuple[tuple, int]:
    tags = tuple(i % 8 for i in range(n))
    index: dict[int, list[int]] = {}
    for i, tag in enumerate(tags):
        index.setdefault(tag, []).append(i)
    return tuple(tuple(index.get(j % 9, ())) for j in range(q)), n + q


def _feedback_baseline(n: int, q: int) -> tuple[tuple, int]:
    labels = tuple(i % 7 for i in range(n))
    values = tuple(1 + i % 5 for i in range(n))
    results = []
    for j in range(q):
        changed = (j * 11) % n
        total = [0] * 7
        for i, label in enumerate(labels):
            total[label] += values[i] + (2 if i == changed else 0)
        results.append(tuple(total))
    return tuple(results), n * q


def _feedback_improved(n: int, q: int) -> tuple[tuple, int]:
    labels = tuple(i % 7 for i in range(n))
    values = tuple(1 + i % 5 for i in range(n))
    total = [0] * 7
    for label, value in zip(labels, values):
        total[label] += value
    results = []
    for j in range(q):
        changed = (j * 11) % n
        current = total.copy()
        current[labels[changed]] += 2
        results.append(tuple(current))
    return tuple(results), n + q


ALGORITHMS = {
    "ENGINE_INCREMENTAL_BUILD": (_chain_baseline, _chain_improved),
    "SKILL_TEST_AUTOMATION": (_tests_baseline, _tests_improved),
    "LEARNING_FEEDBACK_LOOP": (_feedback_baseline, _feedback_improved),
}


def evaluate_ucie_owned_recipe(purpose: str, *, rows: int = 128,
                               queries: int = 24, repeats: int = 3) -> dict:
    _bounds(rows, queries, repeats)
    if type(purpose) is not str or purpose not in RECIPES:
        raise CapabilityTrialError("no implemented first-party recipe")
    baseline, improved = ALGORITHMS[purpose]
    times_a, times_b, mismatch = [], [], 0
    cost_a = cost_b = 0
    for _ in range(repeats):
        start = perf_counter_ns()
        a, cost_a = baseline(rows, queries)
        times_a.append(max(0, perf_counter_ns() - start))
        start = perf_counter_ns()
        b, cost_b = improved(rows, queries)
        times_b.append(max(0, perf_counter_ns() - start))
        if len(a) != queries or len(b) != queries:
            mismatch += max(abs(len(a) - queries), abs(len(b) - queries), 1)
        mismatch += sum(x != y for x, y in zip(a, b))
    good = not mismatch and cost_b < cost_a
    fingerprint = sha256(json.dumps(
        ["UCIE_SYNTHETIC_RECIPE_V1", purpose, rows, queries],
        separators=(",", ":")).encode("ascii")).hexdigest()
    return {
        "schema": SCHEMA, "kind": RECIPES[purpose][0], "purpose_code": purpose,
        "recipe_id": RECIPES[purpose][1], "workload_sha256": fingerprint,
        "synthetic_records": rows, "queries": queries, "repetitions": repeats,
        "baseline_operations": cost_a, "candidate_operations_including_setup": cost_b,
        "baseline_median_elapsed_ns": int(median(times_a)),
        "candidate_median_elapsed_ns": int(median(times_b)),
        "mismatched_queries_across_repetitions": mismatch,
        "exact_result_equivalence_observed": mismatch == 0,
        "synthetic_operation_reduction_observed": good,
        "status": ("UCIE_SYNTHETIC_RECIPE_WORTH_MORE_TESTING_NO_GO" if good
                   else "UCIE_SYNTHETIC_RECIPE_REVIEW_REQUIRED_NO_GO"),
        "next_hypothesis": ("RETEST_ON_DIFFERENT_UCIE_SYNTHETIC_WORKLOAD" if good
                            else "FIX_UCIE_RECIPE_BEFORE_RETEST"),
        "evaluates_upstream_code": False, "upstream_benefit_verified": False,
        "network_requests": 0, "operating_database_writes": 0,
        "experience_ledger_writes": 0, "model_weights_changed": False,
        "production_adopted": False, "auto_promoted": False, "v1_accepted": False,
    }


def verified_w05_cues(source_rows: object, *, source_id: str, now=None) -> tuple[dict, ...]:
    """Actual existing W05 validation; public URL/SHA, NOT upstream capability proof."""
    from .positive_capability_discovery import classify_public_capability_metadata
    classified = classify_public_capability_metadata(
        source_rows, source_id=source_id, now=now)
    if (type(classified) is not dict
            or classified.get("schema") != "UCIE_W05_POSITIVE_PUBLIC_CAPABILITY_DISCOVERY_V1"
            or classified.get("status") != "POSITIVE_CAPABILITY_HINTS_UNVERIFIED_NO_GO"
            or classified.get("source_id") != source_id
            or type(classified.get("candidates")) is not list
            or classified.get("candidate_count") != len(classified["candidates"])):
        raise CapabilityTrialError("original W05 classifier contract changed")
    records = []
    for row in classified["candidates"]:
        if (type(row) is not dict or row.get("source_id") != source_id
                or row.get("evidence_strength") != "MERGED_PR_TITLE_CUE_ONLY"
                or row.get("actual_capability_verified") is not False
                or row.get("benefit_measured") is not False
                or row.get("approved") is not False
                or row.get("export_allowed") is not False
                or row.get("license_independently_reviewed") is not False):
            raise CapabilityTrialError("unapproved source cue cannot become experience")
        purpose, kind = row.get("purpose_code"), row.get("kind")
        if (purpose not in RECIPES and purpose not in KNOWN_NOT_IMPLEMENTED):
            raise CapabilityTrialError("unsupported W05 purpose label")
        if purpose in RECIPES and RECIPES[purpose][0] != kind:
            raise CapabilityTrialError("upstream cue kind/recipe mismatch")
        if (type(row.get("library_item_id")) is not str
                or len(row["library_item_id"]) != 64
                or any(x not in "0123456789abcdef" for x in row["library_item_id"])):
            raise CapabilityTrialError("invalid W05 Library item identity")
        records.append(row)
    if len(records) > MAX_FEED_TRIALS:
        raise CapabilityTrialError("too many candidate title cues")
    return tuple(records)


def evaluate_approved_w05_feed(source_rows: object, *, source_id: str,
                               now=None, max_trials: int = 5) -> dict:
    if type(max_trials) is not int or not 1 <= max_trials <= 5:
        raise CapabilityTrialError("bounded W05 candidate trial count required")
    cues = verified_w05_cues(source_rows, source_id=source_id, now=now)
    records = []
    for cue in cues[:max_trials]:
        purpose = cue["purpose_code"]
        recipe = RECIPES.get(purpose)
        output = (evaluate_ucie_owned_recipe(purpose) if recipe else None)
        records.append({
            "library_item_id": cue["library_item_id"],
            "source_id": source_id, "public_url": cue["public_url"],
            "evidence_sha256": cue["evidence_sha256"],
            "merge_commit_sha": cue["merge_commit_sha"],
            "kind": cue["kind"], "purpose_code": purpose,
            "trial_id": sha256((cue["library_item_id"] + ":" + purpose +
                              ":UCIE_RECIPE_V1").encode("ascii")).hexdigest(),
            "candidate_status": "UPSTREAM_TITLE_CUE_ONLY_UNVERIFIED",
            "evaluation_status": ("UCIE_FIRST_PARTY_SURROGATE_ONLY" if recipe
                                  else "NO_FIRST_PARTY_RECIPE_IMPLEMENTED"),
            "synthetic_experiment": output,
            "upstream_capability_tested": False,
            "upstream_benefit_measured": False, "license_reviewed": False,
            "export_allowed": False, "human_approved": False,
        })
    return {
        "schema": SCHEMA, "status": "W05_LINKED_TO_UCIE_SURROGATE_EXPERIMENTS_NO_GO",
        "source_id": source_id, "source_candidate_count": len(cues),
        "returned_count": len(records), "items": records,
        "network_requests": 0, "operating_database_writes": 0,
        "experience_ledger_writes": 0,
        "public_source_code_executed": False,
        "actual_upstream_skill_verified": False,
        "auto_promoted": False, "v1_accepted": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="UCIE-only W05/P8 synthetic recipe trials")
    parser.add_argument("--demo", action="store_true")
    parser.add_argument("--rows", type=int, default=128)
    parser.add_argument("--queries", type=int, default=24)
    parser.add_argument("--repeats", type=int, default=3)
    args = parser.parse_args()
    if not args.demo:
        print(json.dumps({"schema": SCHEMA, "status": "EXPLICIT_DEMO_REQUIRED_NO_GO",
                          "network_requests": 0, "operating_database_writes": 0},
                         sort_keys=True))
        return 0
    try:
        results = [evaluate_ucie_owned_recipe(purpose, rows=args.rows,
                   queries=args.queries, repeats=args.repeats)
                   for purpose in RECIPES]
    except CapabilityTrialError as exc:
        print(json.dumps({"schema": SCHEMA, "status": "FAIL_CLOSED",
                          "error_type": type(exc).__name__}, sort_keys=True))
        return 2
    print(json.dumps({"schema": SCHEMA, "status": "UCIE_FIRST_PARTY_DEMO_ONLY",
                      "experiments": results, "network_requests": 0,
                      "operating_database_writes": 0, "auto_promoted": False},
                     sort_keys=True))
    return 0 if all(x["exact_result_equivalence_observed"] for x in results) else 3


if __name__ == "__main__":
    raise SystemExit(main())
