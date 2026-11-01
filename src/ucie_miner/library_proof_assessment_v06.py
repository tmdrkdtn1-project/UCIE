"""UCIE V0.6: evidence-shape checks only; never promote submitted claims.

These checks distinguish plausible citation *forms* from verified versions,
licenses or regression outcomes. No HTTP GET and no execution of upstream PRs.
"""
from __future__ import annotations

from collections import Counter
from urllib.parse import urlsplit

from .library_review_records_v05 import (
    CLAIM_ONLY, GATES, ClaimError, _public_evidence_url,
)

SCHEMA = "UCIE_PUBLIC_CLAIM_EVIDENCE_SHAPE_V06"
STATES = frozenset((
    "OFFICIAL_DOCUMENT_CITATION_UNPINNED",
    "PUBLIC_REPOSITORY_PR_CITATION_ONLY",
    "PINNED_PUBLIC_COMMIT_CITATION_ONLY",
    "PINNED_LICENSE_FILE_CITATION_NOT_LEGAL_SIGNOFF",
    "PUBLIC_CI_RUN_CITATION_RESULTS_NOT_CHECKED",
    "LICENSE_REFERENCE_NOT_SPECIFIC",
    "REGRESSION_RESULTS_NOT_INDEPENDENTLY_CHECKED",
    "VERSION_SCOPE_NOT_INDEPENDENTLY_CHECKED",
    "SECURITY_EFFECT_NOT_INDEPENDENTLY_CHECKED",
))


class EvidenceShapeError(ValueError):
    pass


def inspect_public_claim_shape(receipt: dict, *, source_id: str,
                               source_sha256: str) -> dict:
    if (type(receipt) is not dict
            or receipt.get("status") != CLAIM_ONLY
            or receipt.get("independent_verification") is not False
            or receipt.get("source_id") != source_id
            or receipt.get("source_sha256") != source_sha256
            or receipt.get("gate") not in GATES):
        raise EvidenceShapeError("source-anchored unverified claim required")
    try:
        url = _public_evidence_url(receipt.get("public_evidence_url"),
                                   source_id=source_id)
    except ClaimError as exc:
        raise EvidenceShapeError("public claim route validation rejected") from exc
    path = urlsplit(url).path
    host = urlsplit(url).hostname
    if host != "github.com":
        shape = "OFFICIAL_DOCUMENT_CITATION_UNPINNED"
    elif "/actions/runs/" in path:
        shape = "PUBLIC_CI_RUN_CITATION_RESULTS_NOT_CHECKED"
    elif "/blob/" in path and (
            "/LICENSE" in path or "/COPYING" in path):
        shape = "PINNED_LICENSE_FILE_CITATION_NOT_LEGAL_SIGNOFF"
    elif "/commit/" in path:
        shape = "PINNED_PUBLIC_COMMIT_CITATION_ONLY"
    else:
        shape = "PUBLIC_REPOSITORY_PR_CITATION_ONLY"
    gate = receipt["gate"]
    if gate == "LICENSE" and shape != "PINNED_LICENSE_FILE_CITATION_NOT_LEGAL_SIGNOFF":
        next_status = "LICENSE_REFERENCE_NOT_SPECIFIC"
    elif gate == "INDEPENDENT_REGRESSION" and shape != "PUBLIC_CI_RUN_CITATION_RESULTS_NOT_CHECKED":
        next_status = "REGRESSION_RESULTS_NOT_INDEPENDENTLY_CHECKED"
    elif gate == "VERSION_APPLICABILITY":
        next_status = "VERSION_SCOPE_NOT_INDEPENDENTLY_CHECKED"
    elif gate == "SECURITY_REVIEW":
        next_status = "SECURITY_EFFECT_NOT_INDEPENDENTLY_CHECKED"
    else:
        next_status = shape
    if shape not in STATES or next_status not in STATES:
        raise EvidenceShapeError("unrecognized public evidence classification")
    return {
        "schema": SCHEMA, "gate": gate,
        "citation_shape": shape,
        "review_classification": next_status,
        "claimed_document_sha_recomputed": False,
        "public_content_fetched": False,
        "independent_ci_job_checked": False,
        "exact_release_verified": False,
        "legal_license_signoff": False,
        "regression_passed": False,
        "security_review_passed": False,
        "owner_approved": False,
        "automated_rule_available": False,
    }


def summarize_claim_shapes(receipts: list[dict], *,
                           source_id: str, source_sha256: str) -> dict:
    if type(receipts) is not list or len(receipts) > 500:
        raise EvidenceShapeError("bounded public receipts required")
    codes = Counter()
    review_codes = Counter()
    for claim in receipts:
        result = inspect_public_claim_shape(
            claim, source_id=source_id, source_sha256=source_sha256)
        codes[result["citation_shape"]] += 1
        review_codes[result["review_classification"]] += 1
    return {
        "schema": SCHEMA,
        "submitted_citation_forms": dict(sorted(codes.items())),
        "review_blocker_categories": dict(sorted(review_codes.items())),
        "all_claims_remain_unverified": True,
        "external_checks_performed": 0,
        "production_approved": False,
    }
