"""UCIE P8 first-party synthetic improvement gate; NO code promotion or ML.

Public PR metadata only picks which already-authored UCIE recipe to inspect.
The gate checks algorithmic parity, *including setup* operation counts and
explicit no-side-effect claims; it never evaluates upstream code, rewrites an
algorithm, signs a rulepack, or consumes another project's artifacts.
"""
from __future__ import annotations

from .capability_trials import RECIPES, SCHEMA as TRIAL_SCHEMA

GOOD = "SYNTHETIC_UNVERIFIED_PROMISING"
HOLD = "NEEDS_REVIEW"
PROPOSAL = "FIRST_PARTY_RETEST_PROPOSAL_NOT_ADOPTED"
STOP = "FIRST_PARTY_REGRESSION_HOLD_NO_GO"
MAX_HISTORY = 2400


class ImprovementGateError(ValueError):
    pass


def classify_existing(history: object) -> tuple[dict[str, int], frozenset[str]]:
    """Validate existing P11 records and exclude recipes with failed trials."""
    if type(history) is not list or len(history) > MAX_HISTORY:
        raise ImprovementGateError("bounded P11 experience history required")
    successes: dict[str, int] = {key: 0 for key in RECIPES}
    held: set[str] = set()
    for row in history:
        if type(row) is not dict or set(row) != {
                "recipe", "workload", "baseline_ops", "candidate_ops",
                "exact_equal", "hypothesis_status"}:
            raise ImprovementGateError("untrusted P11 prior record shape")
        recipe = row["recipe"]
        if (recipe not in RECIPES or type(row["workload"]) is not int
                or row["workload"] not in (128, 256, 512)
                or type(row["baseline_ops"]) is not int
                or type(row["candidate_ops"]) is not int
                or not 0 < row["baseline_ops"] <= 100_000
                or not 0 < row["candidate_ops"] <= 100_000
                or type(row["exact_equal"]) is not int
                or row["exact_equal"] not in (0, 1)
                or row["hypothesis_status"] not in (GOOD, HOLD)):
            raise ImprovementGateError("untrusted P11 prior experiment")
        passed = row["exact_equal"] == 1 and row["candidate_ops"] < row["baseline_ops"]
        if (row["hypothesis_status"] == GOOD) != passed:
            raise ImprovementGateError("prior review status contradicted metrics")
        if passed:
            successes[recipe] += 1
        else:
            held.add(recipe)
    return successes, frozenset(held)


def assess_new(outcome: object, *, recipe: str, workload: int) -> dict:
    """Analyze the real UCIE-owned trial; never accept fabricated upstream QA."""
    if recipe not in RECIPES or workload not in (128, 256, 512):
        raise ImprovementGateError("unrecognized first-party recipe/workload")
    if type(outcome) is not dict or outcome.get("schema") != TRIAL_SCHEMA:
        raise ImprovementGateError("unexpected first-party trial contract")
    baseline = outcome.get("baseline_operations")
    candidate = outcome.get("candidate_operations_including_setup")
    mismatches = outcome.get("mismatched_queries_across_repetitions")
    if (outcome.get("purpose_code") != recipe
            or outcome.get("kind") != RECIPES[recipe][0]
            or outcome.get("recipe_id") != RECIPES[recipe][1]
            or outcome.get("synthetic_records") != workload
            or outcome.get("queries") != 24
            or outcome.get("repetitions") != 2
            or type(baseline) is not int or type(candidate) is not int
            or not 0 < baseline <= 100_000 or not 0 < candidate <= 100_000
            or type(mismatches) is not int or not 0 <= mismatches <= 48
            or type(outcome.get("exact_result_equivalence_observed")) is not bool
            or type(outcome.get("synthetic_operation_reduction_observed")) is not bool
            or outcome["exact_result_equivalence_observed"] != (mismatches == 0)
            or outcome["synthetic_operation_reduction_observed"] != (
                mismatches == 0 and candidate < baseline)
            or outcome.get("evaluates_upstream_code") is not False
            or outcome.get("upstream_benefit_verified") is not False
            or outcome.get("production_adopted") is not False
            or outcome.get("model_weights_changed") is not False
            or outcome.get("auto_promoted") is not False
            or outcome.get("v1_accepted") is not False
            or outcome.get("network_requests") != 0
            or outcome.get("operating_database_writes") != 0
            or outcome.get("status") not in (
                "UCIE_SYNTHETIC_RECIPE_WORTH_MORE_TESTING_NO_GO",
                "UCIE_SYNTHETIC_RECIPE_REVIEW_REQUIRED_NO_GO")):
        raise ImprovementGateError("trial contract, safety or metrics mismatch")
    positive = mismatches == 0 and candidate < baseline
    if (outcome["status"] == "UCIE_SYNTHETIC_RECIPE_WORTH_MORE_TESTING_NO_GO") != positive:
        raise ImprovementGateError("trial status contradicts regression metrics")
    return {
        "decision": PROPOSAL if positive else STOP,
        "hypothesis_status": GOOD if positive else HOLD,
        "mismatched_queries": mismatches,
        "baseline_operations": baseline,
        "candidate_operations_including_setup": candidate,
        "relative_operation_reduction_ppm": (
            ((baseline - candidate) * 1_000_000) // baseline if positive else 0),
        "verified_only_ucie_authored_synthetic_experiment": True,
        "improvement_proposal_created": positive,
        "production_code_changed": False,
        "rule_approved": False,
        "model_weights_changed": False,
        "original_upstream_code_executed": False,
    }
