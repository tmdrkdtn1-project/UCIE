"""UCIE V2 append-only, unsigned review history for hypothesis revisions.

An audit record of proposals is not a training database, owner signature,
independent test or license grant. No mutation of canonical SkillBooks.
"""
from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
import json

from .ucie_v2_hypothesis_revision_retest_v01 import (
    SCHEMA as REVISION_SCHEMA, OPTIONS,
)
from .ucie_v2_library_revision_ledger_v01 import validate_review_history

SCHEMA = "UCIE_V2_REVIEWED_REVISION_HISTORY_V01"
MAX_EVENTS = 32


class RevisionHistoryError(ValueError):
    """Forbid silently rewriting or adopting a first-party hypothesis."""


def _digest(data: object) -> str:
    return sha256(json.dumps(data, sort_keys=True, ensure_ascii=False,
                             separators=(",", ":"), allow_nan=False
                             ).encode("utf-8")).hexdigest()


def new_revision_history(history: dict) -> dict:
    pinned = validate_review_history(history)
    data = {"schema": SCHEMA,
            "source_library_history_sha256": pinned["content_sha256"],
            "events": [], "count": 0, "last_event_hash": None,
            "independent_qa_verified": False,
            "owner_adoption_approved": False, "persisted": False}
    return {**data, "content_sha256": _digest(data)}


def _check_revision_report(history: dict, report: dict) -> None:
    pinned = validate_review_history(history)
    if (type(report) is not dict
            or report.get("schema") != REVISION_SCHEMA
            or report.get("history_head_sha256") != pinned["content_sha256"]
            or report.get("content_sha256") != _digest({
                k:v for k,v in report.items() if k != "content_sha256"})
            or report.get("original_history_mutated") is not False
            or report.get("feedback_registry_mutated") is not False
            or report.get("source_revision_authenticated") is not False
            or report.get("real_sdk_rerun_verified") is not False
            or report.get("independent_qa_verified") is not False
            or report.get("rights_approved") is not False
            or report.get("customer_release_authorized") is not False
            or report.get("automatic_rule_promotion") is not False
            or report.get("automatic_model_training") is not False
            or report.get("test_jobs_scheduled") is not False
            or report.get("operating_database_writes") != 0
            or report.get("network_requests") != 0):
        raise RevisionHistoryError("wrong source or review-only boundary")
    drafts = report.get("revision_drafts")
    if (type(drafts) is not list or len(drafts) not in (0, 2)
            or report.get("draft_count") != len(drafts)
            or len({x.get("candidate_id") for x in drafts
                    if type(x) is dict}) != len(drafts)):
        raise RevisionHistoryError("invalid revision collection")
    for item in drafts:
        if (type(item) is not dict
                or item.get("review_option") not in OPTIONS
                or item.get("revision_sha256") != _digest({
                    k:v for k,v in item.items()
                    if k not in ("revision_id", "revision_sha256",
                                 "original_skillbook_replaced",
                                 "engine_contract_activated", "rule_approved",
                                 "independent_qa_verified",
                                 "real_customer_effect_verified",
                                 "automatic_learning_or_training")})
                or item.get("revision_id") != "UCIE-VLIB-REV-" +
                    item["revision_sha256"][:24]
                or any(item.get(key) is not False for key in (
                    "original_skillbook_replaced", "engine_contract_activated",
                    "rule_approved", "independent_qa_verified",
                    "real_customer_effect_verified",
                    "automatic_learning_or_training"))):
            raise RevisionHistoryError("revision record rights or hash drift")


def validate_revision_history(history: dict, review: dict) -> dict:
    pinned = validate_review_history(history)
    if (type(review) is not dict or set(review) != {
                "schema", "source_library_history_sha256", "events", "count",
                "last_event_hash", "independent_qa_verified",
                "owner_adoption_approved", "persisted", "content_sha256"}
            or review["schema"] != SCHEMA
            or review["source_library_history_sha256"] != pinned["content_sha256"]
            or review["independent_qa_verified"] is not False
            or review["owner_adoption_approved"] is not False
            or review["persisted"] is not False
            or type(review["events"]) is not list
            or len(review["events"]) > MAX_EVENTS):
        raise RevisionHistoryError("unknown review history or claimed approval")
    previous = None
    seen = set()
    for i, event in enumerate(review["events"], 1):
        if (type(event) is not dict or set(event) != {
                    "sequence", "previous_event_hash", "report", "event_hash"}
                or type(event["sequence"]) is not int
                or event["sequence"] != i
                or event["previous_event_hash"] != previous):
            raise RevisionHistoryError("reordered or rewritten revision")
        _check_revision_report(pinned, event["report"])
        if (event["report"]["content_sha256"] in seen
                or event["event_hash"] != _digest({
                    k:v for k,v in event.items() if k != "event_hash"})):
            raise RevisionHistoryError("duplicate or modified revision")
        seen.add(event["report"]["content_sha256"])
        previous = event["event_hash"]
    if (review["count"] != len(review["events"])
            or review["last_event_hash"] != previous
            or review["content_sha256"] != _digest({
                k:v for k,v in review.items() if k != "content_sha256"})):
        raise RevisionHistoryError("review ledger digest mismatch")
    return deepcopy(review)


def append_revision_review(history: dict, review: dict,
                           report: dict) -> dict:
    current = validate_revision_history(history, review)
    _check_revision_report(history, report)
    if any(e["report"]["content_sha256"] == report["content_sha256"]
           for e in current["events"]):
        return current
    if current["count"] >= MAX_EVENTS:
        raise RevisionHistoryError("bounded revision record full")
    event = {"sequence": current["count"] + 1,
             "previous_event_hash": current["last_event_hash"],
             "report": deepcopy(report)}
    event["event_hash"] = _digest(event)
    data = {k:v for k,v in current.items() if k != "content_sha256"}
    data["events"].append(event)
    data["count"] += 1
    data["last_event_hash"] = event["event_hash"]
    return validate_revision_history(history, {
        **data, "content_sha256": _digest(data)
    })


def review_revision_lessons(history: dict, review: dict) -> dict:
    """Feed prior failures back as bounded read-only constraints, not rules."""
    current = validate_revision_history(history, review)
    findings = []
    for event in current["events"]:
        for d in event["report"]["revision_drafts"]:
            findings.append({
                "revision_id": d["revision_id"],
                "candidate_id": d["candidate_id"],
                "review_option": d["review_option"],
                "retest_regressed": d["retest_regressed"],
                "counterexample": d["counterexample_preserved"],
                "original_skillbook_replaced": False,
                "adopt_as_verified_principle": False,
            })
    return {
        "schema": "UCIE_V2_REVISION_LESSONS_REVIEW_ONLY_V01",
        "source_history_sha256": current["source_library_history_sha256"],
        "review_history_sha256": current["content_sha256"],
        "candidate_review_lessons": findings,
        "lessons_count": len(findings),
        "external_source_authenticated": False,
        "independent_qa_verified": False,
        "automatic_learning": False,
        "automatic_promotion": False,
    }
