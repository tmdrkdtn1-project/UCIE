"""UCIE B4 source-revision impact planner (review only, no source retrieval).

Uses the exact current two-source B4 hypothesis. A proposed revision is
untrusted input; matching its declared SHA does not authenticate upstream.
No mutations, scheduling, test execution, promotion or export.
"""
from __future__ import annotations

from hashlib import sha256
import json
import re

from .b4_transfer_boundary_v01 import build_transfer_hypothesis

SCHEMA = "UCIE_B4_AFFECTED_ONLY_RETEST_PROPOSAL_V01"
DIGEST = re.compile(r"[0-9a-f]{64}\Z")


class RevisionImpactError(ValueError):
    pass


def propose_affected_retests(changes: list[dict]) -> dict:
    """Compare bounded declared revisions to pinned parents, fail closed."""
    if type(changes) is not list or not 1 <= len(changes) <= 8:
        raise RevisionImpactError("INVALID_CHANGES")
    hypothesis = build_transfer_hypothesis()
    baseline = {row["source_id"]: row for row in hypothesis["parent_source_refs"]}
    seen = set()
    affected = []
    unchanged = []
    for change in changes:
        if type(change) is not dict or set(change) != {
                "source_id", "expected_sha256", "observed_sha256",
                "observed_tag", "independently_verified"}:
            raise RevisionImpactError("INVALID_CHANGE_SHAPE")
        source_id = change["source_id"]
        if type(source_id) is not str or source_id not in baseline or source_id in seen:
            raise RevisionImpactError("UNKNOWN_OR_DUPLICATE_SOURCE")
        seen.add(source_id)
        parent = baseline[source_id]
        if (type(change["expected_sha256"]) is not str
                or change["expected_sha256"] != parent["sha256"]):
            raise RevisionImpactError("PARENT_SHA_MISMATCH")
        if (type(change["observed_sha256"]) is not str
                or DIGEST.fullmatch(change["observed_sha256"]) is None):
            raise RevisionImpactError("BAD_OBSERVED_SHA")
        tag = change["observed_tag"]
        if (type(tag) is not str or not 1 <= len(tag) <= 64
                or any(c not in "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789._-" for c in tag)):
            raise RevisionImpactError("BAD_OBSERVED_TAG")
        if type(change["independently_verified"]) is not bool:
            raise RevisionImpactError("INVALID_VERIFICATION_FLAG")
        # An unchanged digest but a changed declared tag still demands review.
        changed = (change["observed_sha256"] != parent["sha256"]
                   or tag != parent["tag"])
        if changed:
            affected.append({
                "source_id": source_id,
                "before_sha256": parent["sha256"],
                "proposed_sha256": change["observed_sha256"],
                "before_tag": parent["tag"], "proposed_tag": tag,
                "independently_verified": change["independently_verified"],
                "action": "REVIEW_AND_RETEST_DEPENDENTS",
                "dependent_ids": [hypothesis["hypothesis_id"],
                                  hypothesis["parent_principle_id"]],
                "candidate_status": "UNVERIFIED_REVIEW_ONLY",
            })
        else:
            unchanged.append(source_id)

    affected.sort(key=lambda row: row["source_id"])
    unchanged.sort()
    result = {
        "schema": SCHEMA,
        "status": "REVIEW_ONLY_UNVERIFIED",
        "hypothesis_id": hypothesis["hypothesis_id"],
        "hypothesis_sha256": hypothesis["content_sha256"],
        "affected_sources": affected,
        "unchanged_sources": unchanged,
        "retests_proposed": len(affected),
        "affected_only": True,
        "test_execution": "NOT_RUN",
        "source_fetches": 0,
        "revision_claims_authenticated": False,
        "owner_approved": False,
        "rights_approved": False,
        "export_allowed": False,
        "auto_promoted": False,
        "operating_database_writes": 0,
    }
    result["proposal_sha256"] = sha256(json.dumps(
        result, ensure_ascii=True, sort_keys=True,
        separators=(",", ":")).encode("ascii")).hexdigest()
    return result
