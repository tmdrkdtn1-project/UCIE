"""UCIE V0.9: one-pass explicit public-source verification and safe-rule preview.

This workflow reads UCIE's validated Stage10/12/15 handoff once, reads
V0.5 receipts once, then only on --check-public does bounded anonymous
external metadata/official-doc lookup. No scheduled monitoring, persistence,
external patch execution, auto-import or auto-promotion.
"""
from __future__ import annotations

from collections import Counter
from hashlib import sha256
import json
from pathlib import Path

from .library_explore import _candidate_rows, _balanced
from .library_audit_v07 import audit_handoff_receipts, CONFLICT
from .library_public_probe_v08 import (
    ProbeError, _identity_preflight, inspect_public_source_revision,
    inspect_claimed_official_document, GATES_NOT_VERIFIED,
)
from .library_review_records_v05 import (
    _location, _read_all, _root, PUBLIC_DOC_HOSTS,
)
from .public_discovery import SOURCE_SKILL
from .skill_profiles import PROFILE
from .verification_handoff import prepare_verification_handoff
from urllib.parse import urlsplit

SCHEMA = "UCIE_PUBLIC_EVIDENCE_OPT_IN_BATCH_V09"
MAX_ITEMS = 5
MAX_DOCS_PER_ITEM = 2


class BatchError(ValueError):
    pass


def _canonical(value: dict) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=True).encode("ascii")


def perform_public_probe_batch(
        root: Path, *, item_id: str | None = None, top: int = 5,
        fetch_json=None, fetch_bytes=None, handoff_factory=None,
        receipt_reader=None) -> dict:
    """Owner-triggered one-pass exact-public-source checks, no proof promotion."""
    if type(top) is not int or not 1 <= top <= MAX_ITEMS:
        raise BatchError("public probe count exceeds owner limit")
    root = _root(root)
    prepare = (prepare_verification_handoff if handoff_factory is None
               else handoff_factory)
    receipts_reader = _read_all if receipt_reader is None else receipt_reader
    handoff = prepare(root)
    complete, rows = _candidate_rows(handoff)
    if not complete:
        raise BatchError("current public source handoff incomplete")
    receipts = receipts_reader(_location(root))
    # This audit rejects forged approvals and flags orphan/stale/conflicted
    # V0.5 submission data. Never treat it as independent fix evidence.
    audit = audit_handoff_receipts(handoff, receipts)
    if audit["status"] == CONFLICT:
        raise BatchError("conflicting or stale public claim receipts require review")
    if item_id is not None:
        if (type(item_id) is not str or len(item_id) != 64
                or any(x not in "0123456789abcdef" for x in item_id)):
            raise BatchError("invalid bounded public candidate identity")
        selected = [r for r in rows if r["library_item_id"] == item_id]
        if len(selected) != 1:
            raise BatchError("requested public candidate absent")
    else:
        # First eligible source-linked candidates per approved repository.
        # Selected PR/commit metadata is verified ONLY at runtime, not by
        # repository-sourced statements.
        eligible = []
        for row in rows:
            try:
                _identity_preflight(row)
            except ProbeError:
                continue
            eligible.append(row)
        selected = _balanced(eligible)[:top]
    if not selected:
        raise BatchError("no eligible pinned public candidate")
    if len(selected) > top:
        raise BatchError("requested candidate exceeds owner-selected bound")
    outcomes = []
    observed = 0
    matching = 0
    doc_checks = 0
    doc_matches = 0
    for row in selected:
        try:
            metadata = inspect_public_source_revision(row, fetch_json=fetch_json)
        except ProbeError:
            # An unsupported candidate can be reviewed, not probed.
            metadata = {
                "status": "UNSUPPORTED_PUBLIC_IDENTITY_NO_GO",
                "identity_matched": False,
                "metadata_observed": False,
                "fix_verified": False,
            }
        observed += int(metadata["metadata_observed"])
        matching += int(metadata["identity_matched"])
        item_claims = [
            receipt for receipt in receipts
            if receipt["item_id"] == row["library_item_id"]
        ]
        doc_results = []
        for receipt in item_claims:
            if len(doc_results) == MAX_DOCS_PER_ITEM:
                break
            if urlsplit(receipt["public_evidence_url"]).hostname not in PUBLIC_DOC_HOSTS:
                continue
            result = inspect_claimed_official_document(
                receipt, row, fetch_bytes=fetch_bytes)
            doc_results.append(result)
            doc_checks += int(result["public_content_checked"])
            doc_matches += int(result["claimed_sha_matched"])
        skill = SOURCE_SKILL[row["source_id"].removeprefix("repo:")]
        profile = PROFILE[skill]
        outcomes.append({
            "item_id": row["library_item_id"],
            "source_id": row["source_id"],
            "purpose_code": row["purpose_code"],
            "public_url": row["public_url"],
            "kind": row["kind"],
            "source_revision_metadata": metadata,
            "official_document_checks": doc_results,
            "inert_rule_review_draft": {
                "type": "REVIEW_ONLY_INERT_PREVENTION_OUTLINE",
                "question": profile["review_question"],
                "next_review": profile["recommended_action"],
                "safe_review": profile["safe_call"],
                "candidate_rule_eligible_for_approval": False,
                "executable_command": None,
                "code_generated": False,
                "version_scope": "UNDETERMINED",
                "signed": False,
            },
            "required_proof_gates": dict(GATES_NOT_VERIFIED),
            "source_metadata_is_fix_verification": False,
        })
    report = {
        "schema": SCHEMA,
        "status": "PUBLIC_SOURCE_OBSERVATION_REVIEW_REQUIRED_NO_GO",
        "source_linked_candidate_count": len(rows),
        "v05_receipts_reviewed": len(receipts),
        "observed_candidate_count": len(selected),
        "public_source_metadata_responses": observed,
        "public_revision_identity_matches": matching,
        "official_document_http_bodies_checked": doc_checks,
        "submitted_document_digests_matching_response": doc_matches,
        "max_external_public_requests": len(selected) * (1 + MAX_DOCS_PER_ITEM),
        "source_audit_status": audit["status"],
        "source_audit_conflict_count": audit["conflicting_claim_groups"],
        "results": outcomes,
        "tested_candidate_fixes": 0,
        "verified_release_version_coverage": 0,
        "independent_regression_passes": 0,
        "legal_license_approvals": 0,
        "owner_signed_rules": 0,
        "approved_rule_count": 0,
        "deployed_rule_count": 0,
        "auto_promoted": False,
        "external_source_code_executed": False,
        "operating_database_writes": 0,
        "review_receipt_writes": 0,
        "scheduler_changes": 0,
    }
    report["audit_report_sha256"] = sha256(_canonical(report)).hexdigest()
    return report


def main() -> int:
    import argparse
    parser = argparse.ArgumentParser(
        description="EXPLICIT opt-in public source observation; NO rule approval")
    parser.add_argument("--check-public", required=True, action="store_true")
    parser.add_argument("--item-id")
    parser.add_argument("--top", type=int, default=5)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    try:
        report = perform_public_probe_batch(
            root, item_id=args.item_id, top=args.top)
    except (BatchError, ProbeError, ValueError, OSError) as exc:
        # Never log raw upstream strings, URLs, secrets or path data.
        print(json.dumps({"schema": SCHEMA, "status": "PUBLIC_PROBE_NO_GO",
                          "error_type": type(exc).__name__}))
        return 2
    print(json.dumps(report, sort_keys=True, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
