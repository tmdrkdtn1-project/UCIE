"""UCIE V0.3: source-linked, review-only comparison of 2 or 3 candidates.

This is not a merit ranking or release authorization. Every comparison
re-reads the existing Stage10/12/15 source-bound handoff and performs the
original admission checks. The only advice shown is authored in UCIE's
fixed, reviewed skill profiles; no untrusted PR text is rendered as advice.
"""
from __future__ import annotations

import re
from pathlib import Path

from .library_explore import _candidate_rows, describe_purpose
from .skill_profiles import PROFILE
from .public_discovery import SOURCE_SKILL
from .verification_handoff import prepare_verification_handoff

SCHEMA = "UCIE_W04_PUBLIC_CANDIDATE_COMPARE_V03"
READY = "READ_ONLY_UNVERIFIED_CANDIDATE_COMPARISON_NO_GO"
INCOMPLETE = "SOURCE_LINKAGE_INCOMPLETE_NO_GO"
NOT_FOUND = "UNKNOWN_OR_AMBIGUOUS_CANDIDATE_NO_GO"
HEX = re.compile(r"[0-9a-f]{64}\Z")
MAX_COMPARE = 3


class CompareError(ValueError):
    pass


def validate_ids(ids: object) -> tuple[str, ...]:
    if (type(ids) is not tuple or not 2 <= len(ids) <= MAX_COMPARE
            or any(type(x) is not str or HEX.fullmatch(x) is None for x in ids)
            or len(set(ids)) != len(ids)):
        raise CompareError("exactly two or three distinct SHA-256 item identities required")
    return ids


def compare_linked_public_candidates(handoff: object, *,
                                     item_ids: tuple[str, ...]) -> dict:
    """Return only metadata and review questions from known pinned public sources."""
    ids = validate_ids(item_ids)
    complete, rows = _candidate_rows(handoff)
    base = {
        "schema": SCHEMA, "status": INCOMPLETE,
        "requested_count": len(ids), "returned_count": 0, "items": [],
        "network_requests": 0, "operating_database_writes": 0,
        "scheduler_changes": 0, "private_project_reads": 0,
        "new_approvals": 0, "approved_or_exportable_items": 0,
        "auto_promoted": False, "production_approved": False,
    }
    if not complete:
        return base
    by_id = {}
    for row in rows:
        item_id = row["library_item_id"]
        if item_id in ids:
            if item_id in by_id:
                return dict(base, status=NOT_FOUND)
            by_id[item_id] = row
    if len(by_id) != len(ids):
        return dict(base, status=NOT_FOUND)
    comparison = []
    for item_id in ids:
        row = by_id[item_id]
        repo = row["source_id"].removeprefix("repo:")
        skill_id = SOURCE_SKILL.get(repo)
        profile = PROFILE.get(skill_id)
        if (profile is None or profile["domain"] != row["domain"]):
            raise CompareError("unrecognized source-specific review guide")
        label, description = describe_purpose(row["purpose_code"])
        comparison.append({
            "library_item_id": row["library_item_id"],
            "source_id": row["source_id"],
            "public_url": row["public_url"],
            "domain": row["domain"],
            "kind": row["kind"],
            "purpose_code": row["purpose_code"],
            "purpose_label": label,
            "purpose_description": description,
            "revision_hint": row["revision_hint"],
            "evidence_sha256": row["evidence_sha256"],
            "evidence_revision_count": row["evidence_revision_count"],
            "license_status": row["license_status"],
            "version_scope_claim": "UNDETERMINED",
            "review_question": profile["review_question"],
            "next_review_action": profile["recommended_action"],
            "safe_review_guidance": profile["safe_call"],
            "verification_gaps": (
                "EXACT_PUBLIC_VERSION_AND_LICENSE_SIGNOFF",
                "INDEPENDENT_REGRESSION_AND_SECURITY_RETEST",
                "EXPLICIT_OWNER_REVIEW_AND_SIGNED_RELEASE",
            ),
            "status": "UNVERIFIED_CANDIDATE_ONLY",
            "human_approved": False,
            "export_allowed": False,
        })
    return dict(base, status=READY, items=comparison,
                returned_count=len(comparison))


def compare_existing_public_candidates(root: Path, *,
                                       item_ids: tuple[str, ...]) -> dict:
    validate_ids(item_ids)
    root = Path(root)
    if (root.is_symlink() or root.name.casefold() != "ucie"
            or not root.is_dir()):
        raise CompareError("dedicated UCIE checkout required")
    # One immutable-view handoff per request. Never bypass fingerprint checks.
    handoff = prepare_verification_handoff(root)
    return compare_linked_public_candidates(handoff, item_ids=item_ids)
