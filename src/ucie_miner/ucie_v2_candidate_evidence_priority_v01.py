"""UCIE-only evidence-aware hypothesis priority after paired synthetic evaluation.

Each candidate receives its OWN disjoint, bounded test cases. These are
UCIE-authored synthetic observations, not independent/production proof.
No dynamic imports, customer inputs, external SDK, scheduled jobs or writes.
"""
from __future__ import annotations

from hashlib import sha256
import json

from .ucie_v2_effectiveness_evaluation_v01 import (
    _validate_cases, _rates, MAX_CASES, ORIGIN,
)
from .ucie_v2_feedback_registry_v01 import prioritize_review_experiments
from .ucie_v2_library_revision_ledger_v01 import validate_review_history

SCHEMA = "UCIE_V2_CANDIDATE_SPECIFIC_EVIDENCE_PRIORITY_V01"
MIN_CASES = 8
MIN_PER_CLASS = 3
MAX_TOTAL_CASES = 128


class CandidatePriorityError(ValueError):
    """A synthetic performance claim cannot silently expand authority."""


def _digest(value: object) -> str:
    return sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
                             separators=(",", ":"), allow_nan=False)
                  .encode("utf-8")).hexdigest()


def prioritize_candidate_evidence(history: dict, registry: dict,
                                  fixtures_by_candidate: dict, *,
                                  fixture_sha256: str) -> dict:
    """Evaluate each original hypothesis separately with explicit guardrails.

    Missing controls HOLD; an observed regression outranks possible gains.
    Unresolved source updates HOLD regardless of fixture improvements. No
    adoption or independent QA is inferred from any first-party observations.
    """
    pinned = validate_review_history(history)
    base = prioritize_review_experiments(pinned, registry)
    queue = base["priority_queue"]
    ids = {q["candidate_id"] for q in queue}
    if (type(fixtures_by_candidate) is not dict
            or any(type(k) is not str or k not in ids
                   for k in fixtures_by_candidate)
            or any(type(v) not in (list, tuple)
                   for v in fixtures_by_candidate.values())
            or sum(len(v) for v in fixtures_by_candidate.values()) > MAX_TOTAL_CASES):
        raise CandidatePriorityError("unbounded or foreign candidate fixture")
    # Even an empty evaluation must have a well-formed source digest.
    all_seen = set()
    results = []
    for entry in queue:
        cid = entry["candidate_id"]
        cases = _validate_cases(fixtures_by_candidate.get(cid, ()),
                                source_sha256=fixture_sha256)
        case_ids = {row["case_id"] for row in cases}
        if case_ids & all_seen:
            raise CandidatePriorityError("fixture used for multiple candidates")
        all_seen.update(case_ids)
        before = _rates(cases, "baseline_prediction")
        after = _rates(cases, "challenger_prediction")
        npos = before["detection_rate"]["denominator"]
        nneg = before["false_positive_rate"]["denominator"]
        adequate = (len(cases) >= MIN_CASES
                    and npos >= MIN_PER_CLASS and nneg >= MIN_PER_CLASS)
        regressed = sum(
            case["baseline_prediction"] == case["ground_truth"]
            and case["challenger_prediction"] != case["ground_truth"]
            for case in cases
        )
        improved = sum(
            case["baseline_prediction"] != case["ground_truth"]
            and case["challenger_prediction"] == case["ground_truth"]
            for case in cases
        )
        fpr_delta = (after["false_positive_rate"]["value"]
                     - before["false_positive_rate"]["value"]
                     if nneg else None)
        fnr_delta = (after["false_negative_rate"]["value"]
                     - before["false_negative_rate"]["value"]
                     if npos else None)
        if entry["blocked_by_upstream_change"]:
            verdict, priority = "HOLD_UNRESOLVED_UPSTREAM", 1
        elif not adequate:
            verdict, priority = "HOLD_INADEQUATE_SYNTHETIC_CONTROLS", 2
        elif regressed:
            verdict, priority = "REVISE_SYNTHETIC_REGRESSION", 1
        elif (fpr_delta is not None and fpr_delta > 0) or (
                fnr_delta is not None and fnr_delta > 0):
            verdict, priority = "REVISE_RISK_RATE_WORSENED", 1
        elif entry["review_decision"].startswith(("HOLD_", "REJECT_")):
            verdict, priority = "HOLD_EXISTING_REVIEW_GATE", min(2, entry["priority"])
        elif improved:
            verdict, priority = "REVIEW_SYNTHETIC_GAIN_NOT_PROVEN", 3
        else:
            verdict, priority = "NO_SYNTHETIC_EVIDENCE_OF_GAIN", 3
        results.append({
            "candidate_id": cid,
            "prior_review_decision": entry["review_decision"],
            "source_hold": entry["blocked_by_upstream_change"],
            "verdict": verdict,
            "priority": priority,
            "paired_case_count": len(cases),
            "positive_control_count": npos,
            "negative_control_count": nneg,
            "control_adequate_for_synthetic_screening": adequate,
            "paired_improved": improved,
            "paired_regressed": regressed,
            "false_positive_rate_delta": fpr_delta,
            "false_negative_rate_delta": fnr_delta,
            "fixture_sha256": _digest(cases),
            "proposed_test_names": entry["test_names"],
            "rule_approved": False,
            "customer_effect_verified": False,
            "independent_qa_verified": False,
            "test_dispatch": False,
        })
    results.sort(key=lambda r: (r["priority"], r["candidate_id"]))
    payload = {
        "schema": SCHEMA,
        "history_head_sha256": pinned["content_sha256"],
        "review_registry_sha256": base["feedback_registry_sha256"],
        "fixture_source_sha256": fixture_sha256,
        "fixture_source_authenticated": False,
        "origin": ORIGIN,
        "evaluated_candidate_count": len(results),
        "total_synthetic_cases": len(all_seen),
        "ranked_candidates": results,
        "real_user_improvement_verified": False,
        "independent_qa_verified": False,
        "rights_approved": False,
        "automatic_promotion": False,
        "tests_scheduled": False,
        "operating_database_writes": 0,
        "network_requests": 0,
    }
    return {**payload, "content_sha256": _digest(payload)}
