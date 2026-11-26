"""UCIE V2 bounded hypothesis revision and first-party retest feedback.

Uses only existing source-pinned Virtual Library candidate contracts and
candidate-specific synthetic observations. A revision is a falsifiable draft,
never a silently modified SkillBook, tested upstream rule or model update.
"""
from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
import json

from .ucie_v2_candidate_evidence_priority_v01 import (
    SCHEMA as PRIORITY_SCHEMA, prioritize_candidate_evidence,
    _digest as candidate_digest,
)
from .ucie_v2_hypothesis_reassessment_v01 import (
    reassess_library_hypotheses, REJECTED_CLAIM,
)
from .ucie_v2_library_revision_ledger_v01 import validate_review_history
from .ucie_v2_feedback_registry_v01 import validate_feedback_registry

SCHEMA = "UCIE_V2_HYPOTHESIS_REVISION_AND_RETEST_V01"
MAX_REVISIONS = 16
ALLOWED = frozenset((
    "HOLD_UNRESOLVED_UPSTREAM",
    "HOLD_INADEQUATE_SYNTHETIC_CONTROLS",
    "REVISE_SYNTHETIC_REGRESSION",
    "REVISE_RISK_RATE_WORSENED",
    "HOLD_EXISTING_REVIEW_GATE",
    "REVIEW_SYNTHETIC_GAIN_NOT_PROVEN",
    "NO_SYNTHETIC_EVIDENCE_OF_GAIN",
))
OPTIONS = frozenset(("HOLD", "REVISE_DRAFT", "RETAIN_REVIEW_ONLY",
                     "REJECT_SYNTHETIC_CHALLENGER"))


class RevisionCycleError(ValueError):
    """Untrusted evidence or fabricated approval is never a revision success."""


def _hash(value: object) -> str:
    return sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
                             separators=(",", ":"), allow_nan=False)
                  .encode("utf-8")).hexdigest()


def _validate_priority(history: dict, registry: dict,
                       report: dict, *, fixture_sha256: str) -> list[dict]:
    pinned = validate_review_history(history)
    ledger = validate_feedback_registry(pinned, registry)
    draft = reassess_library_hypotheses(pinned)
    if (type(report) is not dict or report.get("schema") != PRIORITY_SCHEMA
            or report.get("history_head_sha256") != pinned["content_sha256"]
            or report.get("review_registry_sha256") != ledger["content_sha256"]
            or report.get("fixture_source_sha256") != fixture_sha256
            or report.get("origin") != "UCIE_FIRST_PARTY_SYNTHETIC_REPLAY_ONLY"
            or report.get("fixture_source_authenticated") is not False
            or report.get("real_user_improvement_verified") is not False
            or report.get("independent_qa_verified") is not False
            or report.get("rights_approved") is not False
            or report.get("automatic_promotion") is not False
            or report.get("tests_scheduled") is not False
            or report.get("network_requests") != 0
            or report.get("operating_database_writes") != 0
            or report.get("content_sha256") != _hash({
                k:v for k,v in report.items() if k != "content_sha256"})):
        raise RevisionCycleError("untrusted priority report provenance")
    ranked = report.get("ranked_candidates")
    original = draft["original_falsifiable_candidates"]
    if (type(ranked) is not list or len(ranked) != len(original)
            or {r.get("candidate_id") for r in ranked if type(r) is dict}
                   != {r["candidate_id"] for r in original}):
        raise RevisionCycleError("candidate rank identity mismatch")
    for r in ranked:
        if (type(r) is not dict or r.get("verdict") not in ALLOWED
                or r.get("rule_approved") is not False
                or r.get("customer_effect_verified") is not False
                or r.get("independent_qa_verified") is not False
                or r.get("test_dispatch") is not False):
            raise RevisionCycleError("candidate approval or verdict drift")
    return ranked


def revise_and_retest_hypotheses(history: dict, registry: dict,
                                  initial_fixtures: dict, retest_fixtures: dict,
                                  *, fixture_sha256: str) -> dict:
    """Compare SAME candidate and case IDs before and after revision proposal.

    No arbitrary challenger source is executed. The retest's baseline labels
    must match the original baseline, labels and source for every case;
    otherwise a dataset swap can masquerade as an improvement.
    """
    pinned = validate_review_history(history)
    validate_feedback_registry(pinned, registry)
    initial = prioritize_candidate_evidence(pinned, registry,
                                           initial_fixtures,
                                           fixture_sha256=fixture_sha256)
    retested = prioritize_candidate_evidence(pinned, registry,
                                             retest_fixtures,
                                             fixture_sha256=fixture_sha256)
    previous = _validate_priority(pinned, registry, initial,
                                  fixture_sha256=fixture_sha256)
    current = _validate_priority(pinned, registry, retested,
                                 fixture_sha256=fixture_sha256)
    if set(initial_fixtures) != set(retest_fixtures):
        raise RevisionCycleError("retest candidate cohort changed")
    for cid in initial_fixtures:
        before = {r["case_id"]: r for r in initial_fixtures[cid]}
        after = {r["case_id"]: r for r in retest_fixtures[cid]}
        if before.keys() != after.keys():
            raise RevisionCycleError("retest case cohort changed")
        for key in before:
            if any(before[key].get(field) != after[key].get(field)
                   for field in ("case_id", "ground_truth",
                                 "baseline_prediction", "source_sha256",
                                 "origin")):
                raise RevisionCycleError("retest truth or baseline changed")
    parent_by_id = {r["candidate_id"]: r for r in previous}
    draft = reassess_library_hypotheses(pinned)
    revisions = []
    for after in current:
        before = parent_by_id[after["candidate_id"]]
        old_regressions = before["paired_regressed"]
        new_regressions = after["paired_regressed"]
        old_fpr, new_fpr = (before["false_positive_rate_delta"],
                            after["false_positive_rate_delta"])
        old_fnr, new_fnr = (before["false_negative_rate_delta"],
                            after["false_negative_rate_delta"])
        comparable = (before["control_adequate_for_synthetic_screening"]
                      and after["control_adequate_for_synthetic_screening"])
        # Fixed baseline, same cases, balanced controls are mandatory.
        no_worse = (comparable and new_regressions <= old_regressions
                    and new_fpr is not None and old_fpr is not None
                    and new_fnr is not None and old_fnr is not None
                    and new_fpr <= old_fpr and new_fnr <= old_fnr)
        evidence_gain = no_worse and (
            new_regressions < old_regressions
            or new_fpr < old_fpr or new_fnr < old_fnr
        )
        source_hold = before["source_hold"] or after["source_hold"]
        if source_hold or not comparable:
            option = "HOLD"
        elif new_regressions > old_regressions or (
                new_fpr is not None and old_fpr is not None and new_fpr > old_fpr
        ) or (new_fnr is not None and old_fnr is not None and new_fnr > old_fnr):
            option = "REJECT_SYNTHETIC_CHALLENGER"
        elif evidence_gain:
            option = "REVISE_DRAFT"
        else:
            option = "RETAIN_REVIEW_ONLY"
        draft_source = next(x for x in draft["original_falsifiable_candidates"]
                            if x["candidate_id"] == after["candidate_id"])
        revision_core = {
            "candidate_id": after["candidate_id"],
            "parent_candidate_sha256": draft_source["candidate_sha256"],
            "parent_hypothesis_id": draft_source["parent_hypothesis_id"],
            "revision_hypothesis_text": draft_source["proposed_hypothesis"],
            "counterexample_preserved": REJECTED_CLAIM,
            "previous_synthetic_fixture_sha256": before["fixture_sha256"],
            "retest_synthetic_fixture_sha256": after["fixture_sha256"],
            "retest_same_cases_and_baseline": True,
            "previous_regressed": old_regressions,
            "retest_regressed": new_regressions,
            "previous_fpr_delta": old_fpr,
            "retest_fpr_delta": new_fpr,
            "previous_fnr_delta": old_fnr,
            "retest_fnr_delta": new_fnr,
            "observed_synthetic_nonworsening": bool(no_worse),
            "observed_synthetic_gain": bool(evidence_gain),
            "review_option": option,
            "source_hold_not_cleared": bool(source_hold),
            "proposed_test_names": after["proposed_test_names"],
        }
        revisions.append({
            **revision_core,
            "revision_id": "UCIE-VLIB-REV-" + _hash(revision_core)[:24],
            "revision_sha256": _hash(revision_core),
            "original_skillbook_replaced": False,
            "engine_contract_activated": False,
            "rule_approved": False,
            "independent_qa_verified": False,
            "real_customer_effect_verified": False,
            "automatic_learning_or_training": False,
        })
    revisions.sort(key=lambda item: item["candidate_id"])
    if len(revisions) > MAX_REVISIONS:
        raise RevisionCycleError("review-only revision capacity")
    payload = {
        "schema": SCHEMA, "history_head_sha256": pinned["content_sha256"],
        "registry_sha256": registry["content_sha256"],
        "initial_priority_sha256": initial["content_sha256"],
        "retest_priority_sha256": retested["content_sha256"],
        "fixture_source_sha256": fixture_sha256,
        "revision_drafts": revisions, "draft_count": len(revisions),
        "previous_source_holds_preserved": True,
        "original_history_mutated": False, "feedback_registry_mutated": False,
        "source_revision_authenticated": False,
        "real_sdk_rerun_verified": False, "independent_qa_verified": False,
        "rights_approved": False, "customer_release_authorized": False,
        "automatic_rule_promotion": False, "automatic_model_training": False,
        "test_jobs_scheduled": False,
        "operating_database_writes": 0, "network_requests": 0,
    }
    return {**payload, "content_sha256": _hash(payload)}
