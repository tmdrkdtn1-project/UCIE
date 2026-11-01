"""UCIE V0.6 + V0.7: bundled offline public evidence claim audit.

This reads source-linked Stage10/12/15 and independently checks the *internal*
V0.5 receipt format, immutable receipt digests and current source binding.
It does NOT download public documents or establish that their user-provided
hashes, license claims, versions, fixes or regression behavior are true.

One handoff and one receipt-directory scan per report. No persistence or code
execution, Rulepack generation, owner approval, or project access beyond UCIE.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from hashlib import sha256
import json
from pathlib import Path

from .library_explore import _candidate_rows, describe_purpose
from .library_proof_assessment_v06 import inspect_public_claim_shape
from .library_review_records_v05 import (
    CLAIM_ONLY, GATES, _location, _read_all, _root,
)
from .public_discovery import SOURCE_SKILL
from .skill_profiles import PROFILE
from .verification_handoff import prepare_verification_handoff

SCHEMA = "UCIE_PUBLIC_SOURCE_LINKED_AUDIT_V07"
STATUS = "AUDIT_REVIEW_REQUIRED_NO_GO"
INCOMPLETE = "SOURCE_LINKAGE_INCOMPLETE_NO_GO"
CONFLICT = "RECEIPT_SOURCE_BINDING_CONFLICT_NO_GO"
MAX_ROWS = 1000
MAX_CLAIMS = 500
GATE_ORDER = (
    "SOURCE_PROVENANCE", "VERSION_APPLICABILITY", "LICENSE",
    "INDEPENDENT_REGRESSION", "SECURITY_REVIEW", "OWNER_SIGNOFF",
)
GATE_ACTION = {
    "SOURCE_PROVENANCE": "SOURCE_REVISION_SHA_LINK_CHECK_ONLY",
    "VERSION_APPLICABILITY": "CHECK_OFFICIAL_RELEASE_INCLUSION_AND_REPRODUCE",
    "LICENSE": "REVIEW_EXACT_LICENSE_FILE_AND_REUSE_TERMS",
    "INDEPENDENT_REGRESSION": "RUN_SEPARATELY_REVIEWED_SYNTHETIC_REGRESSION",
    "SECURITY_REVIEW": "DOCUMENT_SECURITY_IMPACT_AND_TEST_GUARDS",
    "OWNER_SIGNOFF": "EXPLICIT_OWNER_SIGNATURE_AND_RELEASE_REVIEW",
}


class AuditError(ValueError):
    pass


def _canonical(obj: dict) -> bytes:
    return json.dumps(obj, ensure_ascii=True, sort_keys=True,
                      separators=(",", ":")).encode("ascii")


def _report_root(complete: bool) -> dict:
    return {
        "schema": SCHEMA,
        "status": STATUS if complete else INCOMPLETE,
        "source_linkage_checked": complete,
        "source_linked_candidates": 0,
        "claim_receipts_integrity_checked": 0,
        "claims_assigned_to_current_sources": 0,
        "orphaned_claim_count": 0,
        "source_sha_conflicts": 0,
        "conflicted_candidate_count": 0,
        "conflicting_claim_groups": 0,
        "candidate_count_with_claims": 0,
        "candidate_count_without_claims": 0,
        "per_domain": {},
        "per_source": {},
        "per_gate_claim_counts": {gate: 0 for gate in sorted(GATES)},
        "citation_shape_counts": {},
        "evidence_review_class_counts": {},
        "candidates": [],
        "approved_candidates": 0,
        "independently_verified_fixes": 0,
        "independently_verified_versions": 0,
        "license_signoffs": 0,
        "regression_passed_candidates": 0,
        "owner_signatures": 0,
        "exportable_rules": 0,
        "auto_promoted": False,
        "operating_database_writes": 0,
        "review_receipt_writes": 0,
        "network_requests": 0,
        "scheduler_changes": 0,
        "review_guides_not_executable": True,
    }


def audit_handoff_receipts(handoff: object, receipts: object) -> dict:
    """Pure source-bound consistency and triage; no external verification.

    A structurally valid, source-linked V0.5 claim remains user-submitted and
    independently unverified, regardless of apparent digest/version matches.
    """
    complete, rows = _candidate_rows(handoff)
    out = _report_root(complete)
    if not complete:
        return out
    if (type(receipts) is not list or len(receipts) > MAX_CLAIMS):
        raise AuditError("invalid bounded receipt collection")
    if len(rows) > MAX_ROWS:
        raise AuditError("public candidate count exceeds bound")
    by_id = {}
    per_source = Counter()
    per_domain = Counter()
    for row in rows:
        identity = row["library_item_id"]
        if identity in by_id:
            raise AuditError("ambiguous current source identity")
        if (row["human_approved"] is not False or row["export_allowed"] is not False
                or row["lifecycle"] != "UNVERIFIED_CANDIDATE_ONLY"):
            raise AuditError("forged candidate approval state")
        skill = SOURCE_SKILL.get(row["source_id"].removeprefix("repo:"))
        profile = PROFILE.get(skill)
        if not profile or profile["domain"] != row["domain"]:
            raise AuditError("candidate source profile mismatch")
        if not row["evidence_revision_sha256s"]:
            raise AuditError("source evidence revision linkage absent")
        by_id[identity] = row
        per_source[row["source_id"]] += 1
        per_domain[row["domain"]] += 1
    assigned = defaultdict(list)
    orphan = 0
    source_conflict = 0
    seen = set()
    for receipt in receipts:
        # Production caller already performs the V0.5 receipt parser and
        # checksum verification. Recheck critical invariants in this pure path
        # as synthetic tests also call it directly.
        if (type(receipt) is not dict
                or receipt.get("status") != CLAIM_ONLY
                or receipt.get("independent_verification") is not False
                or type(receipt.get("receipt_id")) is not str
                or receipt["receipt_id"] in seen
                or receipt.get("gate") not in GATES
                or type(receipt.get("item_id")) is not str):
            raise AuditError("untrusted or duplicate V0.5 claim")
        seen.add(receipt["receipt_id"])
        row = by_id.get(receipt["item_id"])
        if row is None:
            orphan += 1
            continue
        if (receipt.get("source_id") != row["source_id"]
                or receipt.get("source_sha256") not in row["evidence_revision_sha256s"]):
            source_conflict += 1
            continue
        assigned[row["library_item_id"]].append(receipt)
    claims_by_gate = Counter()
    citation_shapes = Counter()
    review_classes = Counter()
    conflicts = 0
    candidate_conflicts = 0
    summaries = []
    with_claims = 0
    for identity in sorted(by_id):
        row = by_id[identity]
        linked = assigned[identity]
        if linked:
            with_claims += 1
        groups = defaultdict(set)
        version_by_gate = defaultdict(set)
        receipts_by_gate = Counter()
        per_item_review_classes = Counter()
        for claim in linked:
            gate = claim["gate"]
            claims_by_gate[gate] += 1
            receipts_by_gate[gate] += 1
            inspection = inspect_public_claim_shape(
                claim, source_id=row["source_id"],
                source_sha256=claim["source_sha256"])
            citation_shapes[inspection["citation_shape"]] += 1
            review_classes[inspection["review_classification"]] += 1
            per_item_review_classes[inspection["review_classification"]] += 1
            groups[(gate, claim["public_evidence_url"])].add(
                claim["claimed_document_sha256"])
            if claim["version_hint"] != "UNDETERMINED":
                version_by_gate[gate].add(claim["version_hint"])
        per_item_conflicts = sum(len(v) > 1 for v in groups.values())
        per_item_conflicts += sum(len(v) > 1 for v in version_by_gate.values())
        if per_item_conflicts:
            conflicts += per_item_conflicts
            candidate_conflicts += 1
        skill = SOURCE_SKILL[row["source_id"].removeprefix("repo:")]
        profile = PROFILE[skill]
        purpose_title, purpose_description = describe_purpose(
            row["purpose_code"])
        # We deliberately do not produce code, scripts or arbitrary commands.
        # This is a checklist-like *proposed review prompt* only.
        review_guide = {
            "type": "INERT_UCIE_REVIEW_GUIDE_NOT_RULE",
            "domain": row["domain"],
            "purpose_code": row["purpose_code"],
            "question": profile["review_question"],
            "safe_review": profile["safe_call"],
            "required_next_check": profile["recommended_action"],
            "generated_executable_rule": False,
            "applies_to_versions": "UNDETERMINED",
            "release_approved": False,
        }
        gates = []
        for gate in GATE_ORDER:
            count = receipts_by_gate.get(gate, 0)
            gates.append({
                "gate": gate,
                "status": ("SOURCE_LINKAGE_ONLY_NOT_FIX_VERIFIED"
                           if gate == "SOURCE_PROVENANCE" else "NOT_VERIFIED"),
                "received_unverified_claims": count,
                "next_check": GATE_ACTION[gate],
            })
        summaries.append({
            "item_id": identity,
            "source_id": row["source_id"],
            "domain": row["domain"],
            "kind": row["kind"],
            "purpose_code": row["purpose_code"],
            "purpose_title": purpose_title,
            "purpose_description": purpose_description,
            "public_url": row["public_url"],
            "source_sha256": row["evidence_sha256"],
            "evidence_revision_count": row["evidence_revision_count"],
            "claim_count": len(linked),
            "claim_conflicts": per_item_conflicts,
            "evidence_review_class_counts": dict(sorted(per_item_review_classes.items())),
            "status": ("RECEIPT_CONFLICT_REVIEW_REQUIRED_NO_GO"
                       if per_item_conflicts else "NOT_VERIFIED"),
            "gates": gates,
            "review_guide": review_guide,
            "executable_rule_available": False,
            "independently_verified": False,
            "license_approved": False,
            "owner_approved": False,
        })
    out.update({
        "source_linked_candidates": len(rows),
        "claim_receipts_integrity_checked": len(receipts),
        "claims_assigned_to_current_sources": sum(len(x) for x in assigned.values()),
        "orphaned_claim_count": orphan,
        "source_sha_conflicts": source_conflict,
        "conflicted_candidate_count": candidate_conflicts,
        "conflicting_claim_groups": conflicts,
        "candidate_count_with_claims": with_claims,
        "candidate_count_without_claims": len(rows) - with_claims,
        "per_domain": dict(sorted(per_domain.items())),
        "per_source": dict(sorted(per_source.items())),
        "per_gate_claim_counts": {key: claims_by_gate[key] for key in sorted(GATES)},
        "citation_shape_counts": dict(sorted(citation_shapes.items())),
        "evidence_review_class_counts": dict(sorted(review_classes.items())),
        "candidates": summaries,
        "status": CONFLICT if source_conflict or conflicts or orphan else STATUS,
    })
    return out


def audit_existing_public_library(root: Path) -> dict:
    root = _root(root)
    # Prepare current Stage10/12/15 source receipts exactly once and open
    # the dedicated V0.5 claim directory once. Both are read only here.
    handoff = prepare_verification_handoff(root)
    complete, _ = _candidate_rows(handoff)
    if not complete:
        return _report_root(False)
    receipts = _read_all(_location(root))
    return audit_handoff_receipts(handoff, receipts)


def summarize_audit(report: dict, *, limit: int = 10) -> dict:
    if (type(report) is not dict or report.get("schema") != SCHEMA
            or type(limit) is not int or not 1 <= limit <= 20
            or type(report.get("candidates")) is not list):
        raise AuditError("malformed source-bound audit report")
    fields = (
        "schema", "status", "source_linkage_checked",
        "source_linked_candidates", "claim_receipts_integrity_checked",
        "claims_assigned_to_current_sources", "orphaned_claim_count",
        "source_sha_conflicts", "conflicted_candidate_count",
        "conflicting_claim_groups", "candidate_count_with_claims",
        "candidate_count_without_claims", "per_source", "per_domain",
        "per_gate_claim_counts", "citation_shape_counts",
        "evidence_review_class_counts", "approved_candidates",
        "independently_verified_fixes", "license_signoffs",
        "regression_passed_candidates", "owner_signatures", "exportable_rules",
        "auto_promoted", "operating_database_writes",
        "review_receipt_writes", "network_requests", "scheduler_changes",
    )
    # Display conflict-bearing and recently claimed candidates first;
    # this is NOT a trust/quality ranking or newly learned rule selection.
    ordered = sorted(report["candidates"], key=lambda r: (
        -int(r["claim_conflicts"] > 0), -r["claim_count"],
        r["source_id"], r["item_id"]))
    out = {name: report[name] for name in fields}
    out["review_queue"] = [{
        "item_id": row["item_id"],
        "source_id": row["source_id"],
        "domain": row["domain"],
        "purpose_code": row["purpose_code"],
        "claim_count": row["claim_count"],
        "conflicting_claim_groups": row["claim_conflicts"],
        "next_review_action": row["review_guide"]["required_next_check"],
        "independently_verified": False,
        "rule_generated": False,
    } for row in ordered[:limit] if row["claim_count"] or row["claim_conflicts"]]
    out["report_sha256"] = sha256(_canonical(out)).hexdigest()
    return out


def main() -> int:
    import argparse
    parser = argparse.ArgumentParser(
        description="UCIE public evidence audit only; never signs or approves rules")
    parser.add_argument("--top", type=int, default=10)
    args = parser.parse_args()
    try:
        report = summarize_audit(
            audit_existing_public_library(Path(__file__).resolve().parents[2]),
            limit=args.top)
    except (AuditError, ValueError, OSError) as exc:
        print(json.dumps({"schema": SCHEMA, "status": "AUDIT_NO_GO",
                          "error_type": type(exc).__name__}))
        return 2
    print(json.dumps(report, sort_keys=True, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
