"""UCIE V2 bounded feedback registry, candidate triage and next-experiment planning.

Review-only, source-pinned in-memory append log of actual UCIE synthetic feedback
receipts. Does not grant independent QA or promotion, and never writes the live
Virtual Library, SQLite, files, jobs or customer systems.
"""
from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
import json
import re

from .ucie_v2_library_revision_ledger_v01 import validate_review_history
from .ucie_v2_feedback_iteration_v01 import compose_feedback_iteration, _receipt
from .ucie_v2_first_party_feedback_cycle_v01 import (
    execute_first_party_feedback_cycle, REQUIRED,
)
from .ucie_v2_hypothesis_reassessment_v01 import (
    reassess_library_hypotheses, ALLOWED_TESTS,
)

SCHEMA = "UCIE_V2_LEARNING_FEEDBACK_REGISTRY_V01"
ENTRY = "UCIE_V2_LEARNING_FEEDBACK_EVENT_V01"
PLAN = "UCIE_V2_EXPERIMENT_PRIORITY_PLAN_V01"
MAX_EVENTS = 32
HEX = re.compile(r"[0-9a-f]{64}\Z")
DECISIONS = frozenset((
    "HOLD_SOURCE_REVISION",
    "HOLD_INCOMPLETE_PAIRED_EVIDENCE",
    "REJECT_SYNTHETIC_CONTROL_FAILURE",
    "REVISE_REVIEW_ONLY_OUTPUT_GUARD",
    "REVIEW_CANDIDATE_SYNTHETIC_NOT_INDEPENDENT",
    "HOLD_PREVIEW_NOT_TESTED",
))
STATUS = frozenset((
    "HOLD_UNRESOLVED_SOURCE_REVISION",
    "HOLD_INCOMPLETE_SYNTHETIC_PAIR",
    "REJECTED_FIRST_PARTY_CONTROL_DRIFT",
    "REVIEW_ONLY_SYNTHETIC_CONTROLS_MATCH",
    "HOLD_SYNTHETIC_TEST_NOT_RUN",
))


class FeedbackRegistryError(ValueError):
    """Reject inconsistent lineage, fabricated approval or replayed evidence."""


def _sha(obj: object) -> str:
    return sha256(json.dumps(obj, ensure_ascii=False, sort_keys=True,
                             separators=(",", ":"), allow_nan=False)
                  .encode("utf-8")).hexdigest()


def empty_feedback_registry(history: dict) -> dict:
    valid = validate_review_history(history)
    payload = {"schema": SCHEMA, "history_head_sha256": valid["content_sha256"],
               "events": [], "event_count": 0, "head_hash": None,
               "signed": False, "independent_qa_verified": False,
               "automatic_promotion": False, "persisted": False}
    return {**payload, "content_sha256": _sha(payload)}


def _check_feedback(history: dict, cycle: dict, iteration: dict) -> dict:
    _receipt(cycle, history)
    expected = reassess_library_hypotheses(history)
    results = cycle["feedback_results"]
    if (type(iteration) is not dict
            or iteration.get("history_head_sha256") != history["content_sha256"]
            or type(iteration.get("content_sha256")) is not str
            or iteration["content_sha256"] != _sha({
                k:v for k,v in iteration.items() if k != "content_sha256"})
            or iteration.get("feedback_cycle_sha256") != cycle["content_sha256"]
            or iteration.get("previous_feedback_cycle_sha256") is not None
            or iteration.get("duplicate_observation") is not False
            or iteration.get("prior_history_unchanged") is not True
            or iteration.get("no_automatic_rule_promotion") is not True
            or iteration.get("independent_qa_verified") is not False
            or iteration.get("rights_approved") is not False
            or iteration.get("customer_release_authorized") is not False
            or iteration.get("network_requests") != 0
            or iteration.get("operating_database_writes") != 0
            or type(results) is not list
            or len(results) != expected["generated_candidates_count"]
            or cycle.get("unresolved_source_changes") !=
                expected["unresolved_changed_sources"]):
        raise FeedbackRegistryError("feedback lineage, cycle or authority drift")

    rows = []
    for feedback, draft in zip(results, expected["original_falsifiable_candidates"]):
        verdict = feedback.get("verdict")
        if (verdict not in STATUS
                or feedback.get("candidate_id") != draft["candidate_id"]
                or feedback.get("candidate_sha256") != draft["candidate_sha256"]
                or feedback.get("candidate_kind") != draft["candidate_kind"]
                or feedback.get("allowed_followup_test_names") !=
                    draft["potential_engine_test_names"]
                or feedback.get("candidate_approved") is not False
                or feedback.get("independently_verified") is not False
                or feedback.get("historical_source_hold_cleared") is not False
                or feedback.get("rights_approved") is not False
                or feedback.get("external_code_executed") is not False
                or feedback.get("rejected_original_privacy_overgeneralization_preserved")
                    is not True):
            raise FeedbackRegistryError("candidate or false approval")
        ran = feedback.get("real_first_party_synthetic_tests_executed")
        observed = feedback.get("controls_observed")
        if ran is True:
            if (cycle["cycle_mode"] != "EXECUTE_UCIE_FIRST_PARTY_SYNTHETIC_ONLY"
                    or feedback.get("synthetic_fixture_count") != 3
                    or type(observed) is not list or len(observed) != 3):
                raise FeedbackRegistryError("invalid synthetic observation")
            matched = observed == REQUIRED
            if not matched:
                decision = "REJECT_SYNTHETIC_CONTROL_FAILURE"
            elif expected["review_lifecycle"].startswith("SOURCE_REVISION_HOLD"):
                decision = "HOLD_SOURCE_REVISION"
            elif expected["review_lifecycle"] == (
                    "INCOMPLETE_LATEST_PAIRED_SYNTHETIC_STUDY_HOLD"):
                decision = "HOLD_INCOMPLETE_PAIRED_EVIDENCE"
            else:
                decision = ("REVISE_REVIEW_ONLY_OUTPUT_GUARD"
                            if draft["candidate_kind"].startswith("BOUNDED_INPUT")
                            else "REVIEW_CANDIDATE_SYNTHETIC_NOT_INDEPENDENT")
            required_verdict = {
                "HOLD_SOURCE_REVISION": "HOLD_UNRESOLVED_SOURCE_REVISION",
                "HOLD_INCOMPLETE_PAIRED_EVIDENCE": "HOLD_INCOMPLETE_SYNTHETIC_PAIR",
                "REJECT_SYNTHETIC_CONTROL_FAILURE": "REJECTED_FIRST_PARTY_CONTROL_DRIFT",
                "REVISE_REVIEW_ONLY_OUTPUT_GUARD":
                    "REVIEW_ONLY_SYNTHETIC_CONTROLS_MATCH",
                "REVIEW_CANDIDATE_SYNTHETIC_NOT_INDEPENDENT":
                    "REVIEW_ONLY_SYNTHETIC_CONTROLS_MATCH",
            }[decision]
        else:
            if (cycle["cycle_mode"] != "PREVIEW_ONLY_NO_EXECUTION"
                    or feedback.get("synthetic_fixture_count") != 0
                    or observed != []):
                raise FeedbackRegistryError("invented synthetic execution")
            decision = "HOLD_PREVIEW_NOT_TESTED"
            required_verdict = "HOLD_SYNTHETIC_TEST_NOT_RUN"
        if verdict != required_verdict:
            raise FeedbackRegistryError("synthetic verdict does not match evidence")
        proposed = feedback["allowed_followup_test_names"]
        if (type(proposed) is not list or proposed != sorted(set(proposed))
                or any(x not in ALLOWED_TESTS for x in proposed)):
            raise FeedbackRegistryError("unapproved proposed test")
        rows.append({
            "candidate_id": draft["candidate_id"],
            "candidate_sha256": draft["candidate_sha256"],
            "candidate_kind": draft["candidate_kind"],
            "decision": decision,
            "source_hold_active": bool(expected["unresolved_changed_sources"]),
            "controls": list(observed),
            "proposed_test_names": list(proposed),
            "priority": (1 if decision == "HOLD_SOURCE_REVISION"
                         else 2 if decision in (
                             "REJECT_SYNTHETIC_CONTROL_FAILURE",
                             "HOLD_INCOMPLETE_PAIRED_EVIDENCE")
                         else 3),
            "approved_as_rule": False,
            "independently_verified": False,
        })
    return {"candidate_reviews": rows, "history_head_sha256": history["content_sha256"],
            "cycle_sha256": cycle["content_sha256"],
            "iteration_sha256": iteration["content_sha256"]}


def append_feedback_evidence(history: dict, registry: dict, *,
                             cycle: dict | None = None,
                             iteration: dict | None = None,
                             execute_synthetic: bool = False) -> dict:
    """Append an independently recomputed first-party review-only receipt.

    By default preview does not execute any tests. This never writes to disk;
    returns a new value to be reviewed and versioned by the owner separately.
    """
    if type(execute_synthetic) is not bool:
        raise FeedbackRegistryError("execute flag must be bool")
    valid = validate_review_history(history)
    current = validate_feedback_registry(valid, registry)
    if cycle is None and iteration is None:
        cycle = execute_first_party_feedback_cycle(
            valid, execute_synthetic=execute_synthetic)
        iteration = compose_feedback_iteration(valid, preview_only=not execute_synthetic)
    elif cycle is None or iteration is None:
        raise FeedbackRegistryError("cycle and iteration must be paired")
    evidence = _check_feedback(valid, cycle, iteration)
    fingerprint = _sha(evidence)
    if any(e["fingerprint"] == fingerprint for e in current["events"]):
        return current
    if len(current["events"]) >= MAX_EVENTS:
        raise FeedbackRegistryError("bounded review registry full")
    prior = current["head_hash"]
    data = {"schema": ENTRY, "sequence": len(current["events"]) + 1,
            "previous_hash": prior, "fingerprint": fingerprint,
            "evidence": deepcopy(evidence)}
    event = {**data, "event_hash": _sha(data)}
    output = {k:v for k,v in current.items() if k != "content_sha256"}
    output["events"].append(event)
    output["event_count"] = len(output["events"])
    output["head_hash"] = event["event_hash"]
    return validate_feedback_registry(valid, {**output,
                                              "content_sha256": _sha(output)})


def validate_feedback_registry(history: dict, registry: object) -> dict:
    valid = validate_review_history(history)
    if (type(registry) is not dict or set(registry) != {
        "schema", "history_head_sha256", "events", "event_count",
        "head_hash", "signed", "independent_qa_verified",
        "automatic_promotion", "persisted", "content_sha256",
    } or registry["schema"] != SCHEMA
            or registry["history_head_sha256"] != valid["content_sha256"]
            or registry["signed"] is not False
            or registry["independent_qa_verified"] is not False
            or registry["automatic_promotion"] is not False
            or registry["persisted"] is not False
            or type(registry["events"]) is not list
            or len(registry["events"]) > MAX_EVENTS):
        raise FeedbackRegistryError("invalid registry schema, head or approval")
    prior = None
    seen = set()
    for index, event in enumerate(registry["events"], 1):
        if (type(event) is not dict or set(event) != {
            "schema", "sequence", "previous_hash", "fingerprint",
            "evidence", "event_hash",
        } or event["schema"] != ENTRY
                or type(event["sequence"]) is not int
                or event["sequence"] != index
                or event["previous_hash"] != prior
                or type(event["evidence"]) is not dict
                or event["evidence"].get("history_head_sha256") != valid["content_sha256"]
                or event["fingerprint"] != _sha(event["evidence"])
                or event["fingerprint"] in seen
                or type(event["event_hash"]) is not str
                or event["event_hash"] != _sha({
                    k:v for k,v in event.items() if k != "event_hash"
                })):
            raise FeedbackRegistryError("invalid registry chain or duplicate")
        # This ledger is a review receipt index; detached evidence is not
        # independent execution proof. Validate the bounded candidate fields.
        reviews = event["evidence"].get("candidate_reviews")
        if (type(reviews) is not list or len(reviews) not in (0,2)
                or any(type(r) is not dict
                       or r.get("decision") not in DECISIONS
                       or r.get("approved_as_rule") is not False
                       or r.get("independently_verified") is not False
                       or r.get("priority") not in (1,2,3)
                       for r in reviews)):
            raise FeedbackRegistryError("unsafe stored feedback decision")
        seen.add(event["fingerprint"])
        prior = event["event_hash"]
    if (registry["event_count"] != len(registry["events"])
            or registry["head_hash"] != prior
            or registry["content_sha256"] != _sha({
                k:v for k,v in registry.items() if k != "content_sha256"
            })):
        raise FeedbackRegistryError("invalid registry summary or digest")
    return deepcopy(registry)


def prioritize_review_experiments(history: dict, registry: dict) -> dict:
    """Return stable bounded proposed tests, no job execution or scheduling."""
    checked = validate_feedback_registry(history, registry)
    latest = checked["events"][-1]["evidence"] if checked["events"] else None
    reviews = latest["candidate_reviews"] if latest else []
    queue = []
    for record in reviews:
        queue.append({
            "candidate_id": record["candidate_id"],
            "priority": record["priority"],
            "review_decision": record["decision"],
            "test_names": record["proposed_test_names"],
            "blocked_by_upstream_change": record["source_hold_active"],
            "run_automatically": False,
            "evidence_independently_verified": False,
        })
    queue.sort(key=lambda r:(r["priority"], r["candidate_id"]))
    payload = {
        "schema": PLAN,
        "history_head_sha256": checked["history_head_sha256"],
        "feedback_registry_sha256": checked["content_sha256"],
        "priority_queue": queue,
        "candidate_count": len(queue),
        "source_revision_authenticated": False,
        "tests_scheduled": False,
        "owner_approval_granted": False,
        "automatic_promotion": False,
        "customer_release_authorized": False,
        "network_requests": 0,
        "operating_database_writes": 0,
    }
    return {**payload, "content_sha256": _sha(payload)}
