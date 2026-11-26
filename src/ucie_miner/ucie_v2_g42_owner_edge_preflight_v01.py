"""G4.2 owner V2 Edge acceptance preflight, read-only decision guard.

This module NEVER inspects owner host by itself and NEVER grants installation,
Edge UAT, ownership, rights, release or runtime activation. Inputs are a
small redacted snapshot explicitly retrieved from a UCIE-only read-only
bridge, not user files, process scans or a synthetic proof of authorization.
Even a caller asserting all booleans true cannot self-authorize owner UAT.
"""
from __future__ import annotations

SCHEMA = "UCIE_V2_G42_OWNER_EDGE_READONLY_PREFLIGHT_V01"
STATUS = "OWNER_EDGE_V2_DEPLOYMENT_AND_UAT_HOLD"
BASE_MAIN = "f5fbaca6c94f50130941570090c2c555cf92d816"
ISOLATED_G41_HEAD = "b1640cf8a14e984515b08a64b63036069f8edac4"
ALLOWED_KEYS = frozenset({
    "main_sha", "g41_head_sha", "isolated_edge_ci_passed",
    "cross_os_source_ci_passed", "owner_worktree_dirty",
    "readonly_bridge_responded", "owner_v2_runtime_implemented_verified",
    "owner_edge_screen_acceptance_verified",
    "backup_rollback_for_v2_verified",
    "specific_owner_v2_activation_approval_authenticated",
})
PROTECTED_GATES = (
    "OWNER_LIVE_SOURCE_AND_INSTALLED_HANDLER_SHA",
    "OWNER_LOCAL_HEALTH_AND_PORT_IDENTITY",
    "OWNER_FROZEN_V04_CSP_AND_POST_CONTRACT",
    "OWNER_DIRTY_TREE_PRESERVATION_AND_BACKUP_ROLLBACK",
    "OWNER_V2_DRAFT_INSTALLATION_SPECIFIC_APPROVAL",
    "OWNER_REAL_WINDOWS_EDGE_BROWSING_AND_READABILITY",
    "INDEPENDENT_RIGHTS_SECURITY_AND_CUSTOMER_RELEASE_SEPARATE",
)


class OwnerEdgePreflightError(ValueError):
    """Never allow a caller-provided status or approval to become owner authority."""


def review_owner_edge_snapshot(snapshot: dict) -> dict:
    if type(snapshot) is not dict or set(snapshot) != ALLOWED_KEYS:
        raise OwnerEdgePreflightError("missing or unreviewed owner-observation fields")
    if (type(snapshot["main_sha"]) is not str or
            snapshot["main_sha"] != BASE_MAIN or
            type(snapshot["g41_head_sha"]) is not str or
            snapshot["g41_head_sha"] != ISOLATED_G41_HEAD or
            any(type(snapshot[key]) is not bool
                for key in ALLOWED_KEYS - {"main_sha", "g41_head_sha"})):
        raise OwnerEdgePreflightError("stale SHA or untrusted types")
    if (snapshot["isolated_edge_ci_passed"] is not True or
            snapshot["cross_os_source_ci_passed"] is not True or
            snapshot["readonly_bridge_responded"] is not True):
        raise OwnerEdgePreflightError("the isolated prerequisite is unverified")
    # No source-only boolean may attest the owner's real browser, lease,
    # rollback or signed authority. Those belong to an independent owner
    # process, outside this module.
    if any(snapshot[key] is True for key in (
        "owner_v2_runtime_implemented_verified",
        "owner_edge_screen_acceptance_verified",
        "backup_rollback_for_v2_verified",
        "specific_owner_v2_activation_approval_authenticated",
    )):
        raise OwnerEdgePreflightError(
            "owner-host approval cannot be self-attested by source-only input"
        )
    return {
        "schema": SCHEMA, "status": STATUS,
        "main_sha": BASE_MAIN, "g41_head_sha": ISOLATED_G41_HEAD,
        "isolated_windows_edge_qa": "CI_PASS_ON_GITHUB_RUNNER_ONLY",
        "four_platform_offline_regressions": "CI_PASS_ON_GITHUB_RUNNERS_ONLY",
        "owner_bridge_observation": "READONLY_NO_GUI_OR_PROCESS_EXECUTION",
        "owner_worktree_dirty_observed": snapshot["owner_worktree_dirty"],
        "owner_v2_runtime_implemented_verified": False,
        "owner_actual_edge_uat_accepted": False,
        "owner_v2_installation_authorized": False,
        "manual_owner_gates": list(PROTECTED_GATES),
        "v04_frozen": True,
        "no_new_post_or_upload": True,
        "customer_distribution_authorized": False,
        "source_evidence_independent_qa_verified": False,
        "model_trained": False, "auto_promoted": False,
        "operating_database_writes": 0, "owner_files_modified": 0,
        "network_requests": 0,
    }
