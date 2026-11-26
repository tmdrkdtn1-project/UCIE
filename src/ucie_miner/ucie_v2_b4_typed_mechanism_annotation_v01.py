"""Review-only typed mechanism annotations for normalized UCIE W02 evidence.

This bridge intentionally accepts *draft* UCIE-authored interpretations, never
source-verified facts. It cannot grant approval, infer a mechanism from PR text,
or execute public code. Cross-technology overlap is a RETEST PROPOSAL only.
"""
from __future__ import annotations

from hashlib import sha256
import json

from .local_v1_priority_v01 import require_local_work
from .ucie_v2_b4_w02_evidence_intake_gate_v01 import triage_w02_evidence
from .ucie_v2_b4_multisource_hypothesis_v01 import MECHANISMS, COUNTEREXAMPLES

SCHEMA = "UCIE_V2_B4_TYPED_MECHANISM_ANNOTATION_REVIEW_V01"
MAX_ANNOTATIONS = 16
PRECONDITIONS = frozenset((
    "EXACT_VERSION_REQUIRED", "CALLER_SCOPE_EXPLICIT",
    "POSITIVE_NEGATIVE_CONTROL_REQUIRED", "INPUT_SCHEMA_EXPLICIT",
))
ORIGIN = "UCIE_FIRST_PARTY_UNVERIFIED_ANNOTATION"


class AnnotationError(ValueError):
    """Source or review uncertainty must not become an accepted fact."""


def _hash(x: object) -> str:
    return sha256(json.dumps(x, sort_keys=True, ensure_ascii=False,
                             separators=(",", ":"), allow_nan=False
                             ).encode("utf-8")).hexdigest()


def _codes(items: object, choices: frozenset, *, allow_empty: bool = False) -> list[str]:
    if (type(items) is not list or (not items and not allow_empty)
            or len(items) > len(choices)
            or any(type(x) is not str for x in items)
            or len(set(items)) != len(items)
            or not set(items) <= choices):
        raise AnnotationError("invalid bounded annotation code list")
    return sorted(items)


def compare_draft_annotations(records: list[dict], annotations: list[dict]) -> dict:
    """Propose only review experiments from exact W02-linked typed drafts."""
    require_local_work("VIRTUAL_LIBRARY")
    intake = triage_w02_evidence(records)
    if (type(annotations) is not list
            or not 1 <= len(annotations) <= MAX_ANNOTATIONS):
        raise AnnotationError("bounded nonempty annotation list required")
    by_id = {r["library_item_id"]: r for r in intake["review_queue"]}
    seen = set()
    normalized = []
    for row in annotations:
        if type(row) is not dict or set(row) != {
                "library_item_id", "evidence_sha256", "mechanisms",
                "preconditions", "counterexamples", "origin", "status"}:
            raise AnnotationError("unknown annotation fields")
        identity = row["library_item_id"]
        digest = row["evidence_sha256"]
        if (type(identity) is not str or type(digest) is not str
                or identity not in by_id or identity in seen
                or digest != by_id[identity]["evidence_sha256"]
                or type(row["origin"]) is not str or row["origin"] != ORIGIN
                or type(row["status"]) is not str
                or row["status"] != "REVIEW_ONLY_UNVERIFIED"):
            raise AnnotationError("unlinked, duplicate, or forged reviewed evidence")
        mechanisms = _codes(row["mechanisms"], MECHANISMS)
        prerequisites = _codes(row["preconditions"], PRECONDITIONS)
        negatives = _codes(row["counterexamples"], COUNTEREXAMPLES)
        seen.add(identity)
        original = by_id[identity]
        normalized.append({
            "library_item_id": identity,
            "source_id": original["source_id"],
            "source_digest": digest,
            "version_scope_claim": original["version_scope_claim"],
            "mechanisms": mechanisms,
            "preconditions": prerequisites,
            "counterexamples": negatives,
            "status": "REVIEW_ONLY_UNVERIFIED_SOURCE_NOT_AUTHENTICATED",
            "independent_qa_verified": False,
            "rights_approved": False,
        })
    normalized.sort(key=lambda r: r["library_item_id"])
    # A source family is not independent corroboration of itself: W01 names
    # doc:repo and repo:repo as different IDs but the same technology owner.
    groups = {}
    for row in normalized:
        technology = row["source_id"].split(":", 1)[1]
        for mechanism in row["mechanisms"]:
            groups.setdefault(mechanism, {}).setdefault(technology, []).append(row)
    proposals = []
    held = []
    for mechanism, by_technology in sorted(groups.items()):
        supporting = sorted({
            r["library_item_id"] for tech in by_technology
            for r in by_technology[tech]
        })
        if len(by_technology) < 2:
            held.append({
                "mechanism": mechanism,
                "status": "HOLD_SINGLE_TECHNOLOGY",
                "supporting_item_ids": supporting,
            })
            continue
        exclusions = sorted({
            code for rows in by_technology.values()
            for row in rows for code in row["counterexamples"]
        })
        if not exclusions:
            raise AnnotationError("cross-technology proposal without counterexample")
        hypotheses = {
            "mechanism": mechanism,
            "supporting_item_ids": supporting,
            "distinct_technology_count": len(by_technology),
            "explicit_counterexamples": exclusions,
            "status": "REVIEW_ONLY_TEST_PROPOSAL_NOT_TECHNICAL_FACT",
            "test_contract": {
                "positive_fixture_required": True,
                "negative_fixture_required": True,
                "unchanged_control_required": True,
                "actual_test_executed": False,
            },
            "independent_qa_verified": False,
            "export_allowed": False,
        }
        proposals.append({
            **hypotheses,
            "hypothesis_id": "UCIE-ANNOTATED-HYP-" + _hash(hypotheses)[:20],
        })
    result = {
        "schema": SCHEMA,
        "intake_sha256": intake["content_sha256"],
        "reviewed_draft_count": len(normalized),
        "unreviewed_queue_count": intake["unique_count"] - len(normalized),
        "reviewed_annotations": normalized,
        "test_proposals": proposals,
        "held_mechanisms": held,
        "mechanism_extraction_performed": False,
        "source_revision_authenticated": False,
        "actual_first_party_trials_executed": False,
        "independent_qa_verified": False,
        "rights_approved": False,
        "customer_release_authorized": False,
        "network_requests": 0,
        "operating_database_writes": 0,
    }
    return {**result, "content_sha256": _hash(result)}
