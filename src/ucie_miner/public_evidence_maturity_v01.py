"""UCIE Stage12 source-linked evidence maturity gaps: READ-ONLY owner review.

Consumes the existing fail-closed Stage10/15 -> Stage12 handoff. Metadata
identity is NOT independent upstream verification, version clearance, rights
clearance, reproduced bug-fix evidence or a production rule. No network,
operating SQLite writes, scheduler changes, signing or automatic promotion.
"""
from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path

from .automated_candidate_qa import _checked_handoff
from .library_entry import build_library_entry
from .verification_handoff import prepare_verification_handoff

SCHEMA = "UCIE_PUBLIC_EVIDENCE_MATURITY_READONLY_V01"
GAPS = "SOURCE_LINKED_EVIDENCE_REQUIRES_INDEPENDENT_REVIEW_NO_GO"
INCOMPLETE = "SOURCE_LINKAGE_INCOMPLETE_NO_GO"
MAX_PREVIEW = 12


class EvidenceMaturityError(ValueError):
    """No evidence maturity decision can be made from this input."""


def assess_public_evidence_maturity(handoff: object, *, preview_limit: int = 8) -> dict:
    """Summarize already-validated public *candidate* metadata, not raw SQLite.

    A missing/pending source-linked queue produces no review targets or
    interpreted row statistics. Public revision identities can have several
    evidence revisions; these are NOT automatically duplicates or fixes.
    """
    if type(preview_limit) is not int or not 1 <= preview_limit <= MAX_PREVIEW:
        raise EvidenceMaturityError("invalid bounded review preview limit")
    linked, tasks = _checked_handoff(handoff)
    neutral = {
        "schema": SCHEMA,
        "status": INCOMPLETE,
        "source_linkage_complete": False,
        "evidence_revision_count": None,
        "distinct_public_identity_count": None,
        "by_source": None,
        "reference_types": None,
        "review_gaps_in_handoff": None,
        "review_targets": [],
        "production_approved": False,
        "independent_qa_verified": False,
        "customer_release_authorized": False,
        "auto_promoted": False,
        "network_requests": 0,
        "persistent_writes": 0,
    }
    if not linked:
        return neutral
    # _checked_handoff rejects approvals and hash forgery, but direct callers
    # must not be able to fabricate a complete count different from the rows.
    if (type(handoff.get("source_revisions")) is not int
            or handoff["source_revisions"] != len(tasks)
            or type(handoff.get("linked_revisions")) is not int
            or handoff["linked_revisions"] != len(tasks)):
        raise EvidenceMaturityError("source-linked handoff count mismatch")

    per_source = Counter()
    reference_types = Counter()
    by_identity: dict[tuple[str, str], dict] = {}
    template_count = 0
    for task in tasks:
        if (type(task.get("source")) is not str
                or type(task.get("reference")) is not str
                or type(task.get("pattern_code")) is not str
                or type(task.get("skill_id")) is not str):
            raise EvidenceMaturityError("incomplete public candidate identity")
        # Reuse the existing approved source registry and source-bound URL
        # validator; never interpolate arbitrary untrusted source URLs.
        entry = build_library_entry({
            "kind": ("PREVENTION_RULE" if task.get("stage6_candidate")
                     is not None else "PUBLIC_TECHNICAL_EVIDENCE"),
            "source_id": "repo:" + task["source"],
            "evidence_reference": task["reference"],
            "evidence_sha256": task["evidence_sha256"],
            "purpose_code": task["pattern_code"],
            "version_scope": "UNDETERMINED",
            "dependencies": [],
        })
        if (entry["skill_profile"] != task["skill_id"]
                or entry["source_license_status"] != "NOT_ATTESTED_PER_REVISION"
                or entry["version_applicability_verified"] is not False
                or entry["approval_status"] != "NOT_APPROVED"):
            raise EvidenceMaturityError("unattested candidate metadata changed")
        source = entry["source_id"]
        url = entry["public_url"]
        per_source[source] += 1
        kind = ("FIX_PR_METADATA" if task["reference"].startswith("fix-pr:")
                else "PR_METADATA" if task["reference"].startswith("pr:")
                else "GIT_COMMIT_METADATA")
        reference_types[kind] += 1
        template = task.get("stage6_candidate") is not None
        template_count += int(template)
        # Count all evidence *revisions* at a public identity; never equate
        # repeated PR URL with a duplicate, independent test or verified fix.
        key = (source, url)
        if key not in by_identity:
            by_identity[key] = {
                "source_id": source, "public_url": url,
                "example_revision_reference": task["reference"],
                "example_candidate_id_sha256": task["candidate_id_sha256"],
                "evidence_revision_count": 0,
                "stage6_template_candidate_revisions": 0,
            }
        group = by_identity[key]
        group["evidence_revision_count"] += 1
        group["stage6_template_candidate_revisions"] += int(template)
        if (task["reference"], task["candidate_id_sha256"]) < (
                group["example_revision_reference"],
                group["example_candidate_id_sha256"]):
            group["example_revision_reference"] = task["reference"]
            group["example_candidate_id_sha256"] = task["candidate_id_sha256"]

    groups = list(by_identity.values())
    groups.sort(key=lambda group: (
        -group["evidence_revision_count"],
        -group["stage6_template_candidate_revisions"],
        group["source_id"], group["public_url"],
    ))
    for group in groups:
        group["next_manual_gate"] = (
            "RECONCILE_MULTIPLE_EVIDENCE_REVISIONS"
            if group["evidence_revision_count"] > 1
            else "REVIEW_VERSION_RIGHTS_AND_REPRODUCTION"
        )
    count = len(tasks)
    return {
        **neutral,
        "status": GAPS,
        "source_linkage_complete": True,
        "evidence_revision_count": count,
        "distinct_public_identity_count": len(groups),
        "by_source": dict(sorted(per_source.items())),
        "reference_types": dict(sorted(reference_types.items())),
        "public_identities_with_multiple_evidence_revisions": sum(
            group["evidence_revision_count"] > 1 for group in groups
        ),
        "additional_evidence_revisions_at_shared_public_identity": sum(
            group["evidence_revision_count"] - 1 for group in groups
        ),
        "existing_stage6_template_candidate_revisions": template_count,
        "review_gaps_in_handoff": {
            "per_revision_license_not_attested_here": count,
            "affected_runtime_version_not_verified_here": count,
            "independent_regression_not_performed_here": count,
        },
        "review_targets": groups[:preview_limit],
    }


def inspect_public_evidence_maturity(root: Path, *, preview_limit: int = 8) -> dict:
    """Use source re-derivation and SQLite mode=ro/query_only via existing code."""
    return assess_public_evidence_maturity(
        prepare_verification_handoff(Path(root)), preview_limit=preview_limit,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="UCIE public evidence maturity, read-only")
    parser.add_argument("--root", required=True, type=Path)
    parser.add_argument("--limit", type=int, default=8)
    args = parser.parse_args(argv)
    result = inspect_public_evidence_maturity(args.root, preview_limit=args.limit)
    print(json.dumps(result, ensure_ascii=True, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
