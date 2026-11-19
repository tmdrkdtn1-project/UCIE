"""Deterministic UCIE GitHub Draft PR partial-publish recovery decision.

NO GitHub network, no writes and no automatic retry. A host-owned runner must
independently obtain authentic GitHub API evidence and original signed bundle;
caller assertions here cannot attest origin. Branch collision never authorizes
force-update, ref replacement, a new second PR or use of main.
"""
from __future__ import annotations

from .policy import PolicyError
from .unattended_ops import BRANCH, REPO, SHA40, SHA64

SCHEMA = "UCIE_GITHUB_PUBLISH_RECOVERY_INSPECTION_V1"
OBSERVED = frozenset({
    "repository", "base_sha", "branch", "main_ref_sha", "branch_ref_sha",
    "branch_commit_parent_shas", "expected_written_commit_sha",
    "pr_number", "pr_head_sha", "pr_head_ref", "pr_base_ref", "pr_draft",
    "pr_state", "expected_manifest_sha256",
})


def inspect_partial_github_publication(signed: dict, observed: dict) -> dict:
    """Explain whether a failed publish needs operator reconciliation.

    No positive result from this function is a live GitHub acceptance or
    approval to reuse a consumed grant. Recovery always requires a fresh,
    specifically signed owner transaction after independently verified facts.
    """
    if (type(signed) is not dict or
            signed.get("status") != "UCIE_SIGNED_GITHUB_BUNDLE_VERIFIED_NO_NETWORK" or
            signed.get("repository") != REPO or
            type(observed) is not dict or set(observed) != OBSERVED):
        raise PolicyError("UCIE publish recovery inputs not authenticated")
    for k in ("repository", "base_sha", "branch"):
        if observed[k] != signed[k]:
            raise PolicyError("UCIE publish recovery cross-repository or branch")
    if (type(signed.get("manifest_sha256")) is not str or
            SHA64.fullmatch(signed["manifest_sha256"]) is None or
            observed["expected_manifest_sha256"] != signed["manifest_sha256"] or
            type(observed["main_ref_sha"]) is not str or
            SHA40.fullmatch(observed["main_ref_sha"]) is None or
            type(observed["branch"]) is not str or
            BRANCH.fullmatch(observed["branch"]) is None):
        raise PolicyError("UCIE publish recovery manifest/base mismatch")

    head = observed["branch_ref_sha"]
    expected = observed["expected_written_commit_sha"]
    parents = observed["branch_commit_parent_shas"]
    number = observed["pr_number"]
    if head is not None and (type(head) is not str or SHA40.fullmatch(head) is None):
        raise PolicyError("malformed GitHub automation branch ref")
    if expected is not None and (type(expected) is not str or SHA40.fullmatch(expected) is None):
        raise PolicyError("malformed recorded published commit")
    if type(parents) is not list or len(parents) > 2 or any(
            type(p) is not str or SHA40.fullmatch(p) is None for p in parents):
        raise PolicyError("malformed GitHub parent commit evidence")
    if (number is not None and (type(number) is not int or number <= 0) or
            type(observed["pr_draft"]) is not bool and observed["pr_draft"] is not None or
            type(observed["pr_state"]) is not str or
            observed["pr_state"] not in ("absent", "open", "closed")):
        raise PolicyError("malformed UCIE Draft PR identity")

    absent_pr = (number is None and observed["pr_head_sha"] is None and
                 observed["pr_head_ref"] is None and
                 observed["pr_base_ref"] is None and
                 observed["pr_draft"] is None and observed["pr_state"] == "absent")
    if not absent_pr and (number is None or
            type(observed["pr_head_sha"]) is not str or
            SHA40.fullmatch(observed["pr_head_sha"]) is None or
            type(observed["pr_head_ref"]) is not str or
            type(observed["pr_base_ref"]) is not str or
            observed["pr_draft"] is None):
        raise PolicyError("incomplete UCIE GitHub PR metadata")

    # Explicitly block unexpected external branch mutations or missing
    # receipt. An attacker must not substitute one commit for another.
    if head is None:
        if expected is not None or parents or not absent_pr:
            status = "UCIE_PUBLISH_REMOTE_STATE_CONFLICT_NO_GO"
        elif observed["main_ref_sha"] != signed["base_sha"]:
            status = "UCIE_PUBLISH_MAIN_BASE_MOVED_NO_GO"
        else:
            status = "UCIE_PUBLISH_NO_BRANCH_PRESENT_NEW_APPROVAL_REQUIRED"
    elif (expected is None or head != expected or
            parents != [signed["base_sha"]] or
            observed["main_ref_sha"] != signed["base_sha"]):
        status = "UCIE_PUBLISH_REMOTE_STATE_CONFLICT_NO_GO"
    elif absent_pr:
        status = "UCIE_PUBLISH_BRANCH_WITHOUT_PR_MANUAL_RECONCILIATION_REQUIRED"
    elif (observed["pr_state"] != "open" or observed["pr_draft"] is not True or
          observed["pr_head_sha"] != head or
          observed["pr_head_ref"] != signed["branch"] or
          observed["pr_base_ref"] != "main"):
        status = "UCIE_PUBLISH_PR_MISMATCH_NO_GO"
    else:
        status = "UCIE_PUBLISH_DRAFT_PR_METADATA_MATCH_CI_PENDING"

    return {
        "schema": SCHEMA,
        "status": status,
        "repository": REPO,
        "branch": signed["branch"],
        "manifest_sha256": signed["manifest_sha256"],
        "pr_number": number if status == "UCIE_PUBLISH_DRAFT_PR_METADATA_MATCH_CI_PENDING" else None,
        "github_evidence_authentication_performed": False,
        "journal_external_rollback_anchor_verified": False,
        "replayed_old_owner_grant": False,
        "new_git_write_performed": False,
        "remote_main_modified": False,
        "rule_auto_promoted": False,
        "production_approved": False,
    }
