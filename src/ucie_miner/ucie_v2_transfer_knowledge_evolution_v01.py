"""Bounded UCIE V2 hypothesis knowledge-evolution index (review-only).

Consumes the exact source-pinned third-technology review and records original
first-party counterexample knowledge in memory. Not autonomous discovery.
No operating database, external source execution, promotion or distribution.
"""
from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
import json

from .local_v1_priority_v01 import require_local_work
from .ucie_v2_library_third_technology_transfer_v01 import (
    build_heldout_transfer_review, TransferReviewError,
)

SCHEMA = "UCIE_V2_B4_TRANSFER_KNOWLEDGE_EVOLUTION_V01"
MAX_EVENTS = 24
SOURCE_IDS = frozenset((
    "doc:python/cpython", "doc:git/git", "repo:modelcontextprotocol/python-sdk",
))
DECISIONS = frozenset(("COUNTEREXAMPLE_RETAINED", "RETEST_PROPOSED", "NO_CHANGE"))
ALLOWED_CLAIMS = frozenset((
    "BOUNDED_INPUT_AND_EXPLICIT_SCOPE",
    "ALL_OUTPUTS_ANONYMIZED",
    "UNIVERSAL_SDK_COMPATIBILITY",
))


class EvolutionError(ValueError):
    """Unverifiable or potentially promotive input must fail closed."""


def _digest(data: object) -> str:
    return sha256(json.dumps(data, ensure_ascii=False, sort_keys=True,
                             separators=(",", ":"), allow_nan=False
                             ).encode("utf-8")).hexdigest()


def _baseline() -> dict:
    review = build_heldout_transfer_review()
    source_pins = {
        row["source_id"]: row["source_sha256"]
        for row in review["parents"]
    }
    source_pins[review["third_technology"]["approved_source_id"]] = (
        review["third_technology"]["source_commit"]
    )
    if (set(source_pins) != SOURCE_IDS
            or len(review["heldout_trials"]) != 3
            or {x["claim_code"] for x in review["heldout_trials"]}
               != ALLOWED_CLAIMS
            or review["independent_qa_verified"] is not False
            or review["rights_approved"] is not False
            or review["customer_release_authorized"] is not False):
        raise EvolutionError("pinned review mismatch")
    return {"review": review, "source_pins": source_pins}


def _core(state: dict) -> dict:
    return {k: v for k, v in state.items() if k != "content_sha256"}


def build_knowledge_index() -> dict:
    """Create deduplicated concepts, not one skill per source occurrence."""
    require_local_work("VIRTUAL_LIBRARY")
    baseline = _baseline()
    review = baseline["review"]
    concepts = {}
    for trial in review["heldout_trials"]:
        claim = trial["claim_code"]
        if claim in concepts:
            raise EvolutionError("ambiguous duplicate claim in baseline")
        # Stable claim identity is separate from evidence revision identity.
        concept_id = "UCIE-HYP-" + _digest({"claim": claim})[:20]
        accepted = trial["observed_first_party_review_result"] is True
        concepts[claim] = {
            "concept_id": concept_id,
            "claim_code": claim,
            "disposition": ("REVIEW_ONLY_LIMITED_TRANSFER" if accepted
                            else "REJECTED_OVERBROAD_TRANSFER"),
            "counterexamples": ([] if accepted else [trial["scenario"]]),
            "evidence_review_sha256": review["content_sha256"],
            "source_ids": sorted(SOURCE_IDS),
            "source_pins": dict(sorted(baseline["source_pins"].items())),
            "reproducible_test_module":
                review["machine_test_contract"]["reproducible_test_module"],
            "independent_qa_verified": False,
            "rights_approved": False,
            "export_allowed": False,
        }
    base = {
        "schema": SCHEMA,
        "baseline_review_sha256": review["content_sha256"],
        "concepts": [concepts[k] for k in sorted(concepts)],
        "events": [],
        "event_count": 0,
        "latest_event_hash": None,
        "source_version_current_verified": False,
        "independent_qa_verified": False,
        "rights_approved": False,
        "customer_release_authorized": False,
        "auto_promotion": False,
        "history_persisted": False,
        "operating_database_writes": 0,
        "network_requests": 0,
    }
    return {**base, "content_sha256": _digest(base)}


def validate_knowledge_index(index: dict) -> dict:
    """Check exact fixed source and every event, including hash chain."""
    baseline = build_knowledge_index()
    if type(index) is not dict or set(index) != set(baseline):
        raise EvolutionError("unknown evolution index schema")
    immutable = (set(baseline) - {
        "events", "event_count", "latest_event_hash", "content_sha256"
    })
    if any(index[k] != baseline[k] for k in immutable):
        raise EvolutionError("baseline or authorization drift")
    events = index["events"]
    if type(events) is not list or len(events) > MAX_EVENTS:
        raise EvolutionError("unbounded evolution events")
    previous = None
    seen = set()
    pins = _baseline()["source_pins"]
    for number, event in enumerate(events, 1):
        if type(event) is not dict or set(event) != {
            "sequence", "previous_event_hash", "source_id", "observed_pin",
            "claim_code", "decision", "reason_code", "affected_concepts",
            "retest_proposed", "historical_evidence_preserved",
            "actual_upstream_change_verified", "test_executed",
            "event_hash",
        }:
            raise EvolutionError("unrecognized event")
        claim = event["claim_code"]
        source = event["source_id"]
        reason = event["reason_code"]
        if (type(claim) is not str or type(source) is not str
                or type(reason) is not str
                or type(event["observed_pin"]) is not str
                or type(event["decision"]) is not str
                or type(event["affected_concepts"]) is not list
                or any(type(x) is not str for x in event["affected_concepts"])
                or type(event["retest_proposed"]) is not bool):
            raise EvolutionError("malformed event field type")
        if (type(event["sequence"]) is not int or event["sequence"] != number
                or event["previous_event_hash"] != previous
                or claim not in ALLOWED_CLAIMS or source not in SOURCE_IDS
                or event["observed_pin"] != pins[source]
                or event["decision"] not in DECISIONS
                or reason not in ("FIRST_PARTY_COUNTEREXAMPLE",
                                  "SOURCE_REVALIDATION_NEEDED",
                                  "UNCHANGED_PIN")
                or event["actual_upstream_change_verified"] is not False
                or event["test_executed"] is not False
                or event["historical_evidence_preserved"] is not True):
            raise EvolutionError("unsupported source or evidence")
        expected_decision = {
            "FIRST_PARTY_COUNTEREXAMPLE": "COUNTEREXAMPLE_RETAINED",
            "SOURCE_REVALIDATION_NEEDED": "RETEST_PROPOSED",
            "UNCHANGED_PIN": "NO_CHANGE",
        }[reason]
        rejected = claim != "BOUNDED_INPUT_AND_EXPLICIT_SCOPE"
        if (event["decision"] != expected_decision
                or (reason == "FIRST_PARTY_COUNTEREXAMPLE" and not rejected)
                or event["affected_concepts"] != (
                    [claim] if reason != "UNCHANGED_PIN" else [])
                or event["retest_proposed"] is not (
                    reason == "SOURCE_REVALIDATION_NEEDED"
                )):
            raise EvolutionError("false change impact or counterexample")
        key = (source, claim, reason)
        if key in seen:
            raise EvolutionError("duplicate evidence masquerading as new")
        seen.add(key)
        if event["event_hash"] != _digest({
            k: v for k, v in event.items() if k != "event_hash"
        }):
            raise EvolutionError("event hash mismatch")
        previous = event["event_hash"]
    if (index["event_count"] != len(events)
            or index["latest_event_hash"] != previous
            or index["content_sha256"] != _digest(_core(index))):
        raise EvolutionError("altered event lineage")
    return deepcopy(index)


def record_review_observation(index: dict, *, source_id: str,
                              claim_code: str, reason_code: str,
                              observed_pin: str) -> dict:
    """Append only a bounded, already-pinned UCIE review observation."""
    state = validate_knowledge_index(index)
    if (type(source_id) is not str or type(claim_code) is not str
            or type(reason_code) is not str or type(observed_pin) is not str
            or source_id not in SOURCE_IDS or claim_code not in ALLOWED_CLAIMS
            or reason_code not in ("FIRST_PARTY_COUNTEREXAMPLE",
                                   "SOURCE_REVALIDATION_NEEDED", "UNCHANGED_PIN")
            or observed_pin != _baseline()["source_pins"][source_id]):
        raise EvolutionError("unverified or unapproved observation")
    if reason_code == "FIRST_PARTY_COUNTEREXAMPLE" and (
            claim_code == "BOUNDED_INPUT_AND_EXPLICIT_SCOPE"):
        raise EvolutionError("not a counterexample")
    if any((e["source_id"], e["claim_code"], e["reason_code"]) ==
           (source_id, claim_code, reason_code) for e in state["events"]):
        return state
    if len(state["events"]) >= MAX_EVENTS:
        raise EvolutionError("event capacity reached; never prune silently")
    decision = {
        "FIRST_PARTY_COUNTEREXAMPLE": "COUNTEREXAMPLE_RETAINED",
        "SOURCE_REVALIDATION_NEEDED": "RETEST_PROPOSED",
        "UNCHANGED_PIN": "NO_CHANGE",
    }[reason_code]
    payload = {
        "sequence": len(state["events"]) + 1,
        "previous_event_hash": state["latest_event_hash"],
        "source_id": source_id,
        "observed_pin": observed_pin,
        "claim_code": claim_code,
        "decision": decision,
        "reason_code": reason_code,
        "affected_concepts": ([] if reason_code == "UNCHANGED_PIN"
                              else [claim_code]),
        "retest_proposed": reason_code == "SOURCE_REVALIDATION_NEEDED",
        "historical_evidence_preserved": True,
        "actual_upstream_change_verified": False,
        "test_executed": False,
    }
    state["events"].append({**payload, "event_hash": _digest(payload)})
    state["event_count"] = len(state["events"])
    state["latest_event_hash"] = state["events"][-1]["event_hash"]
    state["content_sha256"] = _digest(_core(state))
    return validate_knowledge_index(state)


def build_fixed_evolution_demo() -> dict:
    """Demonstrate a fixed positive, two negatives and unchanged control."""
    state = build_knowledge_index()
    pins = _baseline()["source_pins"]
    for claim in ("ALL_OUTPUTS_ANONYMIZED", "UNIVERSAL_SDK_COMPATIBILITY"):
        state = record_review_observation(
            state, source_id="repo:modelcontextprotocol/python-sdk",
            claim_code=claim, reason_code="FIRST_PARTY_COUNTEREXAMPLE",
            observed_pin=pins["repo:modelcontextprotocol/python-sdk"])
    state = record_review_observation(
        state, source_id="repo:modelcontextprotocol/python-sdk",
        claim_code="BOUNDED_INPUT_AND_EXPLICIT_SCOPE",
        reason_code="SOURCE_REVALIDATION_NEEDED",
        observed_pin=pins["repo:modelcontextprotocol/python-sdk"])
    return record_review_observation(
        state, source_id="doc:git/git",
        claim_code="BOUNDED_INPUT_AND_EXPLICIT_SCOPE",
        reason_code="UNCHANGED_PIN", observed_pin=pins["doc:git/git"])
