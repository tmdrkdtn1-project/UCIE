"""Compare two UCIE-only first-party learning feedback receipts safely.

An improvement is not a passing synthetic fixture by itself. This module
ties review-only feedback to history head, separates repeated observations
from new information and keeps all source-change HOLDs fail-closed.
"""
from __future__ import annotations

from hashlib import sha256
import json

from .ucie_v2_library_revision_ledger_v01 import validate_review_history
from .ucie_v2_first_party_feedback_cycle_v01 import (
    SCHEMA as CYCLE_SCHEMA, execute_first_party_feedback_cycle,
)
from .ucie_v2_hypothesis_reassessment_v01 import reassess_library_hypotheses

SCHEMA = "UCIE_V2_LIBRARY_FEEDBACK_ITERATION_V01"
FOLLOWUP = (
    "REVIEW_SOURCE_CHANGE_AUTHENTICITY_SEPARATELY",
    "REVIEW_AFFECTED_ONLY_RETESTS",
    "REVIEW_ORIGINAL_COUNTEREXAMPLE_CONTRACT",
    "REVIEW_RIGHTS_AND_INDEPENDENT_QA_SEPARATELY",
)


class FeedbackIterationError(ValueError):
    """Block stale, unsupported or fabricated learning-loop receipts."""


def _sha(obj: object) -> str:
    return sha256(json.dumps(obj, sort_keys=True, ensure_ascii=False,
                             separators=(",", ":"), allow_nan=False
                             ).encode("utf-8")).hexdigest()


def _receipt(cycle: dict, history: dict) -> None:
    if (type(cycle) is not dict or cycle.get("schema") != CYCLE_SCHEMA
            or type(cycle.get("content_sha256")) is not str
            or cycle["content_sha256"] != _sha({
                k:v for k,v in cycle.items() if k != "content_sha256"})
            or cycle.get("history_head_sha256") != history["content_sha256"]
            or cycle.get("prior_history_length") != history["record_count"]
            or cycle.get("history_mutated") is not False
            or cycle.get("history_written") is not False
            or cycle.get("source_revision_authenticated") is not False
            or cycle.get("independent_qa_verified") is not False
            or cycle.get("real_upstream_sdk_executed") is not False
            or cycle.get("customer_release_authorized") is not False
            or cycle.get("automatic_model_training") is not False
            or cycle.get("automatic_rule_promotion") is not False
            or cycle.get("network_requests") != 0
            or cycle.get("operating_database_writes") != 0):
        raise FeedbackIterationError("forged or stale feedback cycle")
    proposal = reassess_library_hypotheses(history)
    if (cycle.get("proposal_sha256") != proposal["content_sha256"]
            or cycle.get("review_lifecycle") != proposal["review_lifecycle"]
            or cycle.get("feedback_count") != proposal["generated_candidates_count"]):
        raise FeedbackIterationError("stale hypothesis source")
    items = cycle.get("feedback_results")
    if type(items) is not list or len(items) != proposal["generated_candidates_count"]:
        raise FeedbackIterationError("feedback record count mismatch")
    for actual, expected in zip(items, proposal["original_falsifiable_candidates"]):
        if (type(actual) is not dict
                or actual.get("candidate_id") != expected["candidate_id"]
                or actual.get("candidate_sha256") != expected["candidate_sha256"]
                or actual.get("candidate_kind") != expected["candidate_kind"]
                or actual.get("candidate_approved") is not False
                or actual.get("independently_verified") is not False
                or actual.get("rights_approved") is not False
                or actual.get("historical_source_hold_cleared") is not False
                or actual.get("external_code_executed") is not False):
            raise FeedbackIterationError("feedback candidate identity/approval drift")


def compose_feedback_iteration(history: dict, *,
                               preview_only: bool = False,
                               prior_cycle: dict | None = None) -> dict:
    """Create new original decision aid with prior-receipt dedupe, never persist.

    A prior receipt must belong to the same exact source-pinned history. A
    preview is not accepted as real executed evidence. An attached prior
    cycle is not an authorization to write files or clear a HOLD.
    """
    if type(preview_only) is not bool:
        raise FeedbackIterationError("preview switch must be bool")
    valid = validate_review_history(history)
    if prior_cycle is not None:
        _receipt(prior_cycle, valid)
    now = execute_first_party_feedback_cycle(valid, execute_synthetic=not preview_only)
    _receipt(now, valid)
    previous_same = prior_cycle is not None and now["content_sha256"] == prior_cycle["content_sha256"]
    if preview_only:
        disposition = "PREVIEW_ONLY_NO_TEST_EXECUTION"
    elif now["review_lifecycle"] == "SOURCE_REVISION_HOLD_NOT_CLEARED_BY_SYNTHETIC_REPLAY":
        disposition = "HOLD_SOURCE_REVISION_UNRESOLVED"
    elif now["review_lifecycle"] == "INCOMPLETE_LATEST_PAIRED_SYNTHETIC_STUDY_HOLD":
        disposition = "HOLD_PAIRED_SYNTHETIC_INCOMPLETE"
    elif now["feedback_count"] == 0:
        disposition = "NO_HYPOTHESIS_FROM_EMPTY_HISTORY"
    elif previous_same:
        disposition = "NO_NEW_EVIDENCE_DUPLICATE_SYNTHETIC_CYCLE"
    else:
        disposition = "FIRST_PARTY_SYNTHETIC_REVIEW_CANDIDATES_ONLY"

    requested = []
    if now["unresolved_source_changes"]:
        requested.extend(FOLLOWUP[:2])
    if now["feedback_count"]:
        requested.extend(FOLLOWUP[2:])
    # Deduplicate without losing stable order or creating extra requests.
    requested = list(dict.fromkeys(requested))
    payload = {
        "schema": SCHEMA,
        "history_head_sha256": valid["content_sha256"],
        "feedback_cycle_sha256": now["content_sha256"],
        "previous_feedback_cycle_sha256": (
            prior_cycle["content_sha256"] if prior_cycle else None),
        "duplicate_observation": previous_same,
        "new_approved_technical_evidence": False,
        "disposition": disposition,
        "source_change_hold_active": bool(now["unresolved_source_changes"]),
        "review_candidate_ids": [r["candidate_id"] for r in now["feedback_results"]],
        "real_first_party_synthetic_cases_run": now["executed_ucie_synthetic_fixture_count"],
        "proposed_next_review_steps": requested,
        "negative_privacy_lesson_preserved": now["rejected_negative_lesson"],
        "prior_history_unchanged": True,
        "no_automatic_customer_fix": True,
        "no_automatic_rule_promotion": True,
        "no_automatic_model_training": True,
        "independent_qa_verified": False,
        "rights_approved": False,
        "customer_release_authorized": False,
        "operating_database_writes": 0,
        "network_requests": 0,
    }
    return {**payload, "content_sha256": _sha(payload)}
