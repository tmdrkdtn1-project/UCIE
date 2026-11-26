"""UCIE V2 first-party bounded learning loop from history to real synthetic tests.

The source-pinned original Virtual Library supplies evidence and counterexamples,
the reassessor supplies candidates, and UCIE's OWN three-case in-memory MCP
regression supplies runnable control results. No upstream SDK, customer data,
workflow execution, OS command or automatic rule/rights promotion is permitted.
"""
from __future__ import annotations

from hashlib import sha256
import json

from .ucie_v2_library_revision_ledger_v01 import validate_review_history
from .ucie_v2_hypothesis_reassessment_v01 import (
    reassess_library_hypotheses, _hash as proposal_hash,
)
from .ucie_v2_generalization_transfer_v01 import (
    build_hypothesis, run_bounded_transfer, SCHEMA as B4_SCHEMA,
)

SCHEMA = "UCIE_V2_FIRST_PARTY_LEARNING_FEEDBACK_CYCLE_V01"
REQUIRED = ["CONTRACT_MATCH", "CONTRACT_VIOLATION", "CONTROL_ONLY"]
KINDS = frozenset((
    "BOUNDED_INPUT_TRANSFER_WITH_SOURCE_SPECIFIC_OUTPUT_GUARDS",
    "MCP_TARGET_IN_MEMORY_THIRD_TECHNOLOGY_FALSIFICATION",
))
VERDICTS = frozenset((
    "REVIEW_ONLY_SYNTHETIC_CONTROLS_MATCH",
    "HOLD_UNRESOLVED_SOURCE_REVISION",
    "HOLD_INCOMPLETE_SYNTHETIC_PAIR",
    "REJECTED_FIRST_PARTY_CONTROL_DRIFT",
))


class LearningFeedbackError(ValueError):
    """Evidence/receipt drift is not a successful learning result."""


def _digest(obj: object) -> str:
    return sha256(json.dumps(obj, sort_keys=True, ensure_ascii=False,
                             separators=(",", ":"), allow_nan=False)
                  .encode("utf-8")).hexdigest()


def _validate_candidate(candidate: dict) -> None:
    if (type(candidate) is not dict
            or candidate.get("candidate_kind") not in KINDS
            or type(candidate.get("candidate_sha256")) is not str
            or type(candidate.get("candidate_id")) is not str
            or candidate.get("candidate_id") != "UCIE-VLIB-REVIEW-" +
                    candidate["candidate_sha256"][:20]
            or candidate.get("synthetic_required_control_statuses") != REQUIRED
            or candidate.get("negative_lesson_reused") !=
                "ALL_BOUNDED_METADATA_PROCESSES_HIDE_SOURCE_NAMES"
            or any(candidate.get(key) is not False for key in (
                "real_new_principle_discovered_by_model",
                "source_revision_independently_authenticated",
                "actual_tests_executed", "independent_qa_verified",
                "rights_approved", "automatic_promotion", "export_allowed"
            ))):
        raise LearningFeedbackError("candidate validation or authority drift")
    definition = {k:v for k,v in candidate.items() if k in (
        "candidate_kind", "parent_hypothesis_id", "parent_hypothesis_sha256",
        "parent_bundle_sha256", "human_chapter_sha256", "source_revision_ids",
        "proposed_hypothesis", "counterfactual_rejected",
        "synthetic_required_control_statuses",
    )}
    if proposal_hash(definition) != candidate["candidate_sha256"]:
        raise LearningFeedbackError("candidate source/idea digest mismatch")


def execute_first_party_feedback_cycle(history: dict, *,
                                       execute_synthetic: bool = True) -> dict:
    """Evidence -> draft hypotheses -> bounded real UCIE controls -> new review.

    execute_synthetic=False enables preview with zero tests executed.
    The historical source-revision HOLD is never cleared, even after controls
    match. No persistent ledger or user environment is mutated.
    """
    if type(execute_synthetic) is not bool:
        raise LearningFeedbackError("synthetic execution flag must be boolean")
    pinned = validate_review_history(history)
    draft = reassess_library_hypotheses(pinned)
    if (draft.get("history_head_sha256") != pinned["content_sha256"]
            or draft.get("history_event_hash") != pinned["latest_hash"]
            or draft.get("generated_candidates_count") !=
                len(draft.get("original_falsifiable_candidates", ()))
            or draft.get("generated_candidates_count") not in (0,2)
            or draft.get("content_sha256") !=
                proposal_hash({k:v for k,v in draft.items() if k != "content_sha256"})
            or any(draft.get(key) is not False for key in (
                "source_revision_authenticated", "real_user_study_completed",
                "independent_qa_verified", "rights_approved",
                "automatic_experiment_scheduled", "model_training_performed",
                "customer_release_authorized"))):
        raise LearningFeedbackError("history or original draft changed")
    candidates = draft["original_falsifiable_candidates"]
    if candidates and {x.get("candidate_kind") for x in candidates} != KINDS:
        raise LearningFeedbackError("missing control or candidate arm")
    for candidate in candidates:
        _validate_candidate(candidate)
    trial = None
    if execute_synthetic and candidates:
        h = build_hypothesis()
        trial = run_bounded_transfer(h)
        if (trial.get("schema") != B4_SCHEMA
                or trial.get("hypothesis_id") != candidates[0]["parent_hypothesis_id"]
                or trial.get("content_sha256") != candidates[0]["parent_hypothesis_sha256"]
                or trial.get("synthetic_cases_executed") != 3
                or trial.get("real_upstream_sdk_rerun") is not False
                or trial.get("independent_qa_verified") is not False
                or trial.get("candidate_automatically_approved") is not False
                or trial.get("export_allowed") is not False
                or trial.get("network_requests") != 0
                or trial.get("operating_database_writes") != 0):
            raise LearningFeedbackError("first-party synthetic test provenance drift")

    results = []
    for candidate in candidates:
        results_match = trial is not None and trial.get(
            "positive_negative_control") == REQUIRED
        if trial is None:
            verdict = "HOLD_SYNTHETIC_TEST_NOT_RUN"
        elif not results_match:
            verdict = "REJECTED_FIRST_PARTY_CONTROL_DRIFT"
        elif candidate["status"] == "HOLD_UNRESOLVED_SOURCE_REVISION":
            verdict = "HOLD_UNRESOLVED_SOURCE_REVISION"
        elif candidate["status"] == "HOLD_INCOMPLETE_SYNTHETIC_PAIR":
            verdict = "HOLD_INCOMPLETE_SYNTHETIC_PAIR"
        else:
            verdict = "REVIEW_ONLY_SYNTHETIC_CONTROLS_MATCH"
        result = {
            "candidate_id": candidate["candidate_id"],
            "candidate_sha256": candidate["candidate_sha256"],
            "candidate_kind": candidate["candidate_kind"],
            "verdict": verdict,
            "controls_observed": list(trial["positive_negative_control"]) if trial else [],
            "real_first_party_synthetic_tests_executed": trial is not None,
            "synthetic_fixture_count": trial["synthetic_cases_executed"] if trial else 0,
            "rejected_original_privacy_overgeneralization_preserved": True,
            "historical_source_hold_cleared": False,
            "allowed_followup_test_names": candidate["potential_engine_test_names"],
            "independently_verified": False,
            "candidate_approved": False,
            "rights_approved": False,
            "external_code_executed": False,
        }
        results.append(result)

    payload = {
        "schema": SCHEMA,
        "history_head_sha256": pinned["content_sha256"],
        "proposal_sha256": draft["content_sha256"],
        "cycle_mode": "EXECUTE_UCIE_FIRST_PARTY_SYNTHETIC_ONLY" if execute_synthetic
                     else "PREVIEW_ONLY_NO_EXECUTION",
        "prior_history_length": pinned["record_count"],
        "prior_history_preserved": True,
        "review_lifecycle": draft["review_lifecycle"],
        "feedback_results": results,
        "feedback_count": len(results),
        "executed_ucie_synthetic_fixture_count": (
            trial["synthetic_cases_executed"] if trial else 0),
        "unresolved_source_changes": draft["unresolved_changed_sources"],
        "rejected_negative_lesson": draft["reusable_failed_transfer_claim"],
        "history_mutated": False,
        "history_written": False,
        "source_revision_authenticated": False,
        "real_upstream_sdk_executed": False,
        "independent_qa_verified": False,
        "real_user_study": False,
        "customer_release_authorized": False,
        "automatic_model_training": False,
        "automatic_rule_promotion": False,
        "network_requests": 0,
        "operating_database_writes": 0,
    }
    return {**payload, "content_sha256": _digest(payload)}
