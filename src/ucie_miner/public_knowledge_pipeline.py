"""Stage 9.4-9.6: public code/doc/release/advisory -> reviewable skill knowledge.

All four evidence sources are inspected in memory. Code text, external HTML,
security descriptions, and upstream commands are NEVER retained or executed.
Failures are explicit and do not become PASS. No operating DB, schedule,
Rulepack promotion, external-project access or ChatGPT skill install.
"""
from __future__ import annotations

import hashlib
import json
import re

from .public_discovery import SOURCES, SOURCE_SKILL, DiscoveryError
from .public_evidence_routes import (
    PublicEvidenceError, DOC_ENDPOINTS, fetch_public_evidence,
    github_evidence_url, inspect_pr_changes, inspect_official_document,
    inspect_public_releases, inspect_public_advisories,
)
from .skill_profiles import PROFILE

SHA40 = re.compile(r"[0-9a-f]{40}")
MAX_DOCUMENTS = 4


def _hash(value):
    return hashlib.sha256(json.dumps(
        value, sort_keys=True, separators=(",", ":"),
        ensure_ascii=True, allow_nan=False
    ).encode("ascii")).hexdigest()


def collect_public_knowledge_candidate(source: str, number: int,
                                       *, merge_sha: str, fetch=fetch_public_evidence,
                                       include_doc=True,
                                       include_advisory=True) -> dict:
    """Explicit one-PR public collection; <=4 GETs, no persistence.

    Security feed may legitimately be unavailable (e.g. 404) or empty. We
    preserve that uncertainty rather than inventing an advisory PASS.
    PR files and release metadata are required to return a complete
    *candidate*, never independently verified behavior.
    """
    if (source not in SOURCES or type(number) is not int
            or not 1 <= number <= 999999999
            or not isinstance(merge_sha, str)
            or not SHA40.fullmatch(merge_sha)
            or type(include_doc) is not bool
            or type(include_advisory) is not bool):
        raise PublicEvidenceError("unapproved or unpinned source candidate")
    routes = {
        "patch": github_evidence_url(source, "files", number),
        "release": github_evidence_url(source, "releases"),
    }
    if include_doc:
        routes["document"] = DOC_ENDPOINTS[source][0]
    if include_advisory:
        routes["advisory"] = github_evidence_url(source, "advisories")
    skipped = ([ "document" ] if not include_doc else []) + (
        [ "advisory" ] if not include_advisory else [])
    receipts, missing = {}, []
    for kind, url in routes.items():
        try:
            data = fetch(url)
            if kind == "patch":
                receipts[kind] = inspect_pr_changes(
                    source, number, data, merge_sha=merge_sha)
            elif kind == "release":
                receipts[kind] = inspect_public_releases(source, data)
            elif kind == "document":
                receipts[kind] = inspect_official_document(source, data)
            elif kind == "advisory":
                receipts[kind] = inspect_public_advisories(source, data)
        except (PublicEvidenceError, OSError, ValueError):
            # Unsupported/404 public routes stay explicit. Do not retain
            # network error bodies or report successful verification.
            missing.append(kind)
    # Fail closed for any missing code or release source. An advisory 404
    # or redirecting documentation is not silently treated as evidence.
    status = ("INCOMPLETE_PUBLIC_EVIDENCE" if missing or skipped
              else "UNVERIFIED_PUBLIC_KNOWLEDGE_CANDIDATE")
    patch = receipts.get("patch")
    tags = [] if patch is None else patch["tags"]
    skills = PROFILE[SOURCE_SKILL[source]]
    proposal = {
        "source": source, "pr_number": number,
        "public_url": f"https://github.com/{source}/pull/{number}",
        "pinned_merge_commit_sha": merge_sha,
        "skill_id": SOURCE_SKILL[source],
        "skill_domain": skills["domain"],
        "error_pattern_tags": tags,
        "safe_correction_question": skills["review_question"],
        "safe_call_guidance": skills["safe_call"],
        "regression_plan": skills["recommended_action"],
        "regression_independently_reproduced": False,
        "affected_released_versions": "UNDETERMINED",
        "candidate_rule_status": "UNVERIFIED_CANDIDATE_ONLY",
        "human_reviewer_status": "NOT_RECEIVED",
        "rulepack_signature": None,
        "automatic_learning_applied": False,
        "approved_for_deployment": False,
    }
    candidate_key = {
        "source": source, "number": number, "sha": merge_sha,
        "patch_digest": (patch["file_features"] if patch is not None else None),
        "document_digest": (receipts.get("document") or {}).get("sha256"),
        "releases": (receipts.get("release") or {}).get("releases"),
        "advisories": (receipts.get("advisory") or {}).get("advisories"),
    }
    return {
        "schema": "UCIE_PUBLIC_CODE_DOC_RELEASE_SECURITY_PIPELINE_V1",
        "status": status,
        "source": source,
        "pr_number": number,
        "public_reads_max": len(routes),
        "evidence_types_attempted": list(routes),
        "evidence_types_collected": sorted(receipts),
        "missing_evidence_types": sorted(missing + skipped),
        "explicitly_skipped_evidence_types": sorted(skipped),
        "patch_features": receipts.get("patch"),
        "official_doc_fingerprint": receipts.get("document"),
        "release_fingerprints": receipts.get("release"),
        "security_advisories": receipts.get("advisory"),
        "skill_knowledge_candidate": proposal,
        "candidate_evidence_sha256": _hash(candidate_key),
        "evidence_sha256_is_signature": False,
        "new_rule_status": "AWAITING_INDEPENDENT_REVIEW",
        "human_review_pass": False,
        "license_approved": False,
        "version_inclusion_verified": False,
        "upstream_patch_executed": False,
        "source_code_retained": False,
        "persistence": "NONE",
        "automatic_training": False,
        "rulepacks_auto_promoted": 0,
        "scheduler_registered": False,
        "production_approved": False,
    }


def preview_public_knowledge_receipt(receipt: object) -> dict:
    """Bounded offline post-processing of candidate-only pipeline output."""
    if (not isinstance(receipt, dict)
            or receipt.get("schema") != "UCIE_PUBLIC_CODE_DOC_RELEASE_SECURITY_PIPELINE_V1"
            or receipt.get("source") not in SOURCES
            or type(receipt.get("pr_number")) is not int
            or receipt.get("status") not in (
                "INCOMPLETE_PUBLIC_EVIDENCE",
                "UNVERIFIED_PUBLIC_KNOWLEDGE_CANDIDATE")
            or receipt.get("production_approved") is not False
            or receipt.get("automatic_training") is not False
            or receipt.get("rulepacks_auto_promoted") != 0
            or receipt.get("upstream_patch_executed") is not False
            or receipt.get("source_code_retained") is not False
            or receipt.get("human_review_pass") is not False
            or receipt.get("license_approved") is not False
            or receipt.get("scheduler_registered") is not False
            or receipt.get("version_inclusion_verified") is not False
            or receipt.get("evidence_sha256_is_signature") is not False
            or receipt.get("persistence") != "NONE"
            or not isinstance(receipt.get("candidate_evidence_sha256"), str)
            or not re.fullmatch(r"[a-f0-9]{64}", receipt["candidate_evidence_sha256"])):
        raise PublicEvidenceError("invalid untrusted candidate receipt")
    candidate = receipt.get("skill_knowledge_candidate")
    if (not isinstance(candidate, dict)
            or candidate.get("source") != receipt["source"]
            or candidate.get("pr_number") != receipt["pr_number"]
            or candidate.get("public_url") !=
            f"https://github.com/{receipt['source']}/pull/{receipt['pr_number']}"
            or candidate.get("skill_id") != SOURCE_SKILL[receipt["source"]]
            or candidate.get("candidate_rule_status") != "UNVERIFIED_CANDIDATE_ONLY"
            or candidate.get("automatic_learning_applied") is not False
            or candidate.get("approved_for_deployment") is not False
            or candidate.get("human_reviewer_status") != "NOT_RECEIVED"
            or candidate.get("rulepack_signature") is not None):
        raise PublicEvidenceError("forged or inconsistent review candidate")
    return {
        "schema": "UCIE_PUBLIC_SKILL_LEARNING_REVIEW_V1",
        "status": "MANUAL_REVIEW_ONLY_NO_GO",
        "public_pr": candidate["public_url"],
        "skill_id": candidate["skill_id"],
        "tags": candidate["error_pattern_tags"],
        "missing_public_evidence_types": receipt["missing_evidence_types"],
        "code_diff_not_persisted": True,
        "reproduction_and_release_applicability": "NOT_VERIFIED",
        "license_and_security_review": "NOT_COMPLETED",
        "independent_review": "NOT_RECEIVED",
        "candidate_fingerprint": receipt["candidate_evidence_sha256"],
        "fingerprint_is_signature": False,
        "learned_into_running_knowledge_db": False,
        "approved_rulepack": False,
        "production_approved": False,
    }
