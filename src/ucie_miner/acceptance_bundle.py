"""Stage 8 in-memory UCIE-only acceptance preview: no external side effects.

Combine existing candidate, provenance, pinned-license marker, regression
plan and read-only host observations. It has *no approval operation*.
"""
from __future__ import annotations

from .host_preflight import inspect_ucie_host
from .evidence_binding import bind_candidate_receipts
from .merge_snapshot import compare_merge_snapshot, load_merge_snapshot
from .regression_receipts import inspect_regression_claims
from .review_docket import prepare_independent_review_docket
from .integration import preview_knowledge_rules
from .license_review import inspect_pinned_licenses
from .patterns import PatternError
from .preapproval import preapproval_readiness
from .provenance_review import inspect_public_prs
from .regression_plans import create_regression_matrix
from .review import _read_candidates, load_manifest


def build_readonly_acceptance_preview(root, *, is_windows, python_version,
                                      external_regression_claims=None,
                                      static_preview=None):
    chain = preview_knowledge_rules(root)
    provenance = inspect_public_prs(_read_candidates(root))
    license_markers = inspect_pinned_licenses(root)
    regressions = create_regression_matrix(chain["rulepack_preview"])
    external_review = inspect_regression_claims(
        regressions, load_merge_snapshot(root), external_regression_claims)
    docket = (prepare_independent_review_docket(static_preview, external_review)
              if static_preview is not None else None)
    host = inspect_ucie_host(root, is_windows=is_windows,
                             python_version=python_version)
    readiness = preapproval_readiness(chain, provenance)
    binding = bind_candidate_receipts(
        _read_candidates(root), load_manifest(root), chain,
        provenance, license_markers, regressions)
    merge_snapshot = compare_merge_snapshot(
        root, _read_candidates(root), provenance, load_manifest(root))
    if (regressions["candidate_count"] !=
            chain["pattern_preview"]["family_count"]):
        raise PatternError("incomplete regression candidate coverage")
    if (readiness["status"] != "NO_GO"
            or readiness["candidate_count"] != chain["miner_count"]
            or readiness["production_approved"] is not False
            or license_markers["production_approved"] is not False
            or host["production_approved"] is not False):
        raise PatternError("untrusted approval or mismatched evidence")
    return {
        "schema": "UCIE_STAGE8_READONLY_ACCEPTANCE_BUNDLE_V1",
        "candidate_binding_status": binding["status"],
        "candidate_binding_sha256": binding["receipt_sha256"],
        "candidate_binding_is_signature": False,
        "pinned_merge_snapshot_sha256": merge_snapshot["snapshot_sha256"],
        "pinned_merge_pr_count": merge_snapshot["local_pinned_pr_count"],
        "release_version_inclusion_verified": False,
        "status": "NO_GO",
        "miner_candidate_count": chain["miner_count"],
        "knowledge_evidence_count": chain["knowledge_count"],
        "pattern_families": chain["pattern_preview"]["family_count"],
        "synthetic_regression_plans": regressions["candidate_count"],
        "external_regression_claims": external_review["claimed_cases"],
        "external_regression_claims_missing": external_review["missing_claims"],
        "external_regression_claim_set_sha256": external_review["claim_set_sha256"],
        "external_regression_claims_are_attested": False,
        "static_review_docket_sha256": (
            docket["docket_sha256"] if docket is not None else None),
        "static_review_candidate_count": (
            docket["candidate_findings"] if docket is not None else 0),
        "static_review_approved": False,
        "regression_execution_state": "NOT_EXECUTED",
        "public_pr_metadata_state": "NOT_CHECKED",
        "license_document_state": "NOT_CHECKED",
        "license_document_count": license_markers["count"],
        "host_readonly_precheck": host["status"],
        "operational_host_attested": False,
        "independent_license_approval": False,
        "independent_regression_signoff": False,
        "rulepack_signed": False,
        "package_deployed": False,
        "scheduler_registered": False,
        "persistent_writes": 0,
        "production_approved": False,
    }
