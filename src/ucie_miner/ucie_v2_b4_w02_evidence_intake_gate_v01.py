"""B4 review-only intake bridge for existing W01/W02 public candidates.

Accepts bounded W02 input, never derives a technical mechanism from PR titles
or a registry allowlist. Produces a deterministic source-bound triage queue.
Only existing separately curated B4 records may enter hypothesis comparison.
"""
from __future__ import annotations

from hashlib import sha256
import json

from .local_v1_priority_v01 import require_local_work
from .library_entry import build_library_entry, LibraryEntryError
from .source_registry import get_source, SourceRegistryError, ACTIVE

SCHEMA = "UCIE_V2_B4_PUBLIC_EVIDENCE_HOLD_GATE_V01"
MAX_ITEMS = 24


class IntakeGateError(ValueError):
    """Reject conflicting, unauthorized or potentially promotive records."""


def _digest(value: object) -> str:
    return sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
                             separators=(",", ":"), allow_nan=False
                             ).encode("utf-8")).hexdigest()


def triage_w02_evidence(records: list[dict]) -> dict:
    """Normalize approved-source metadata but hold *all* semantic assertions."""
    require_local_work("VIRTUAL_LIBRARY")
    if type(records) is not list or not 1 <= len(records) <= MAX_ITEMS:
        raise IntakeGateError("bounded nonempty public candidate list required")
    indexed = {}
    references = {}
    for record in records:
        try:
            entry = build_library_entry(record)
            source = get_source(entry["source_id"])
        except (LibraryEntryError, SourceRegistryError, ValueError,
                TypeError, KeyError) as exc:
            raise IntakeGateError("unsupported public evidence candidate") from exc
        if (source["status"] != ACTIVE
                or source["fetch_authorized_by_this_registry"] is not False
                or entry["entry_status"] != "UNVERIFIED_CANDIDATE_ONLY"
                or entry["approval_status"] != "NOT_APPROVED"
                or entry["human_approved"] is not False
                or entry["owner_signed"] is not False
                or entry["export_allowed"] is not False
                or entry["version_applicability_verified"] is not False
                or entry["independent_qa_status"] != "NOT_PERFORMED"
                or entry["source_executed"] is not False
                or entry["source_text_retained"] is not False):
            raise IntakeGateError("W01/W02 status or rights escalation")
        key = (entry["source_id"], entry["evidence_reference"])
        previous = references.get(key)
        if previous is not None and previous != entry["evidence_sha256"]:
            raise IntakeGateError("conflicting digest for exact source revision")
        references[key] = entry["evidence_sha256"]
        identity = entry["library_item_id"]
        if identity in indexed:
            if indexed[identity]["purpose_code"] != entry["purpose_code"]:
                raise IntakeGateError("inconsistent duplicate evidence identity")
            continue
        indexed[identity] = {
            "library_item_id": identity,
            "source_id": entry["source_id"],
            "public_url": entry["public_url"],
            "evidence_reference": entry["evidence_reference"],
            "evidence_sha256": entry["evidence_sha256"],
            "revision_hint": entry["revision_hint"],
            "purpose_code": entry["purpose_code"],
            "kind": entry["kind"],
            "version_scope_claim": entry["version_scope_claim"],
            "triage_status": "HOLD_MECHANISM_NOT_REVIEWED",
            "missing_gates": [
                "MECHANISM_ANNOTATION_AND_COUNTEREXAMPLE",
                "SOURCE_REVISION_AUTHENTICATION",
                "FIRST_PARTY_TEST",
                "INDEPENDENT_QA",
                "RIGHTS_AND_OWNER_RELEASE",
            ],
            "hypothesis_created": False,
            "independent_qa_verified": False,
            "rights_approved": False,
            "export_allowed": False,
        }
    queue = [indexed[k] for k in sorted(indexed)]
    groups = {}
    for row in queue:
        groups.setdefault(row["purpose_code"], set()).add(row["source_id"])
    cross_source = [
        {"purpose_code": purpose, "distinct_sources": len(sources),
         "candidate_status": "SAME_PURPOSE_NOT_MECHANISM_PROOF"}
        for purpose, sources in sorted(groups.items())
        if len(sources) >= 2
    ]
    result = {
        "schema": SCHEMA,
        "submitted_count": len(records),
        "unique_count": len(queue),
        "duplicate_count": len(records) - len(queue),
        "review_queue": queue,
        "cross_source_purpose_matches": cross_source,
        "source_registry_approval_is_not_semantic_approval": True,
        "hypothesis_count": 0,
        "source_fetch_performed": False,
        "source_code_executed": False,
        "independent_qa_verified": False,
        "rights_approved": False,
        "customer_release_authorized": False,
        "auto_promoted": False,
        "network_requests": 0,
        "operating_database_writes": 0,
    }
    return {**result, "content_sha256": _digest(result)}


def combined_curated_and_unreviewed(candidate_records: list[dict]) -> dict:
    """Keep unreviewed W02 intake separate from independently curated B4."""
    from .ucie_v2_b4_fourth_technology_bridge_v01 import (
        build_four_technology_review,
    )
    pending = triage_w02_evidence(candidate_records)
    curated = build_four_technology_review()
    if (curated["approved_for_export"] is not False
            or curated["independent_qa_verified"] is not False
            or pending["hypothesis_count"] != 0):
        raise IntakeGateError("review boundary bypass")
    return {
        "schema": "UCIE_V2_B4_SEPARATED_INTAKE_AND_CURATED_REVIEW_V01",
        "pending_intake": pending,
        "curated_review": curated,
        "unreviewed_evidence_used_as_hypothesis_proof": False,
        "customer_release_authorized": False,
        "network_requests": 0,
        "operating_database_writes": 0,
    }
