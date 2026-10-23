"""Read-only UCIE Library signed-history to exact public revision binding.

Reuses the existing Ed25519, monotonic serial, owner revocation and hash-chain
checks. This can authenticate a keyholder's recorded assertions ONLY, not
independently certify the quality of QA, release inclusion or real-world fixes.
An external expected hash-chain head is REQUIRED; no implicit 'trust latest'.
Nothing signs, installs, promotes, schedules, fetches, or changes a database.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from ucie_public.policy import PolicyError

from .public_discovery import DiscoveryError
from .public_evidence_chain_audit import audit_external_evidence_chain
from .public_library_assessment import preview_library_evidence_assessment
from .public_library_review_store import inspect_local_library_review_history
from .public_library_signed_review import SHA64

SCHEMA = "UCIE_LIBRARY_REVIEW_CLOSURE_BOUNDARY_V1"
STATUS = "SIGNED_CLAIMS_AND_PUBLIC_EVIDENCE_AUDITED_NO_RULE_APPROVAL"
_ALLOWED_STATES = frozenset({
    "SIGNED_REVIEW_CLAIM_NO_GO",
    "EXPIRED_REVIEW_CLAIM_NO_GO",
    "OWNER_REVOKED_NO_GO",
})
_CHAIN_STATES = frozenset({
    "STAGE16_INCOMPLETE_LOCAL_EVIDENCE_NO_GO",
    "STAGE16_LOCAL_EVIDENCE_MISMATCH_NO_GO",
    "STAGE16_LOCALLY_LINKED_BUT_UNVERIFIED_NO_GO",
})


def _digest(value):
    return hashlib.sha256(json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True,
        allow_nan=False).encode("ascii")).hexdigest()


def inspect_library_review_closure(
        root: Path, current: dict, *,
        owner_trust, qa_trust, expected_head_sha256: str,
        previous: dict | None = None, at_time=None) -> dict:
    """Link pinned public metadata to *existing* signed local review history.

    Only a caller-established external checkpoint is admissible. The ledger
    itself cannot prove this checkpoint was anchored independently, so the
    report never claims rollback-proof storage. Unknown, stale and revoked
    states are all NO_GO. Presence of two valid signatures is not actual QA.
    """
    if (type(expected_head_sha256) is not str
            or not SHA64.fullmatch(expected_head_sha256)):
        raise PolicyError("independent expected UCIE review head required")

    assessment = preview_library_evidence_assessment(current, previous)
    if (assessment["production_approved"] is not False
            or assessment["rules_auto_promoted"] != 0
            or assessment["network_requests"] != 0
            or assessment["files_or_databases_written"] != 0):
        raise DiscoveryError("unsafe Library assessment input")

    history = inspect_local_library_review_history(
        root, owner_trust=owner_trust, qa_trust=qa_trust,
        expected_head_sha256=expected_head_sha256, at_time=at_time)
    if (history["head_sha256"] != expected_head_sha256
            or history["caller_checkpoint_matched"] is not True
            or history["hash_chain_and_signatures_checked"] is not True
            or history["external_rollback_protection_proven"] is not False
            or history["production_approved"] is not False
            or history["distribution_authorized"] is not False
            or history["sqlite_writes"] != 0):
        raise PolicyError("uncertain signed UCIE review history")

    chain = audit_external_evidence_chain(root)
    if (chain.get("status") not in _CHAIN_STATES
            or chain.get("persistent_writes") != 0
            or chain.get("external_gets") != 0
            or chain.get("production_approved") is not False
            or chain.get("independent_regression_verified") is not False):
        raise DiscoveryError("unexpected public evidence audit contract")
    # This existing Stage13-15 chain has ONLY local SHA consistency.
    # It never upgrades individual review items or verifies public releases.

    latest = {}
    for record in history["latest_reference_states"]:
        url = record["public_url"]
        if (url in latest or record["state"] not in _ALLOWED_STATES
                or type(record["revoked"]) is not bool
                or type(record["serial"]) is not int
                or not 1 <= record["serial"] <= history["highest_serial"]
                or type(record["pinned_revision_sha"]) is not str
                or type(record["evidence_sha256"]) is not str):
            raise PolicyError("invalid signed review summary identity")
        latest[url] = record

    joined = []
    state_count = {}
    for card in assessment["cards"]:
        url = card["public_url"]
        item = latest.get(url)
        exact_revision = bool(
            item is not None
            and item["pinned_revision_sha"] == card["pinned_revision_sha"]
            and item["evidence_sha256"] == card["evidence_sha256"]
        )
        if item is None:
            verdict = "NO_SIGNED_REVIEW_HISTORY_NO_GO"
        elif item["revoked"]:
            if item["state"] != "OWNER_REVOKED_NO_GO":
                raise PolicyError("revoked entry state mismatch")
            verdict = "OWNER_REVOKED_BLOCKED_NO_GO"
        elif item["state"] == "OWNER_REVOKED_NO_GO":
            raise PolicyError("revocation flag missing")
        elif not exact_revision:
            verdict = "REVIEW_FOR_OLDER_PINNED_EVIDENCE_NO_GO"
        elif item["state"] == "EXPIRED_REVIEW_CLAIM_NO_GO":
            verdict = "SIGNED_CLAIMS_EXPIRED_NO_GO"
        elif item["state"] == "SIGNED_REVIEW_CLAIM_NO_GO":
            verdict = "KEYHOLDER_SIGNED_CLAIMS_AWAIT_INDEPENDENT_QA_NO_GO"
        else:
            raise PolicyError("unknown signed review history state")
        state_count[verdict] = state_count.get(verdict, 0) + 1
        joined.append({
            "review_id_sha256": card["review_id_sha256"],
            "public_url": url,
            "source": card["source"],
            "skill_id": card["skill_id"],
            "pinned_revision_sha": card["pinned_revision_sha"],
            "evidence_sha256": card["evidence_sha256"],
            "revision_change": card["dimensions"]["revision_change"],
            "ledger_event_serial": item["serial"] if item else None,
            "ledger_claim_revision_matches": exact_revision,
            "signed_keyholder_claim_version": (
                item["version_claim"] if item and exact_revision
                and not item["revoked"] else None),
            "review_state": verdict,
            "source_version_independently_verified": False,
            "source_license_independently_verified": False,
            "security_independently_verified": False,
            "regression_independently_reproduced": False,
            "human_qa_independently_confirmed": False,
            "owner_release_approval_granted": False,
            "rules_may_auto_promote": False,
            "can_publish_or_install": False,
            "next_action": (
                "KEEP_REVOKED_AND_REQUIRE_SEPARATE_RECOVERY_APPROVAL"
                if item is not None and item["revoked"] else
                "RECHECK_PINNED_REVISION_AND_REPEAT_INDEPENDENT_REVIEW"
                if item is not None and not exact_revision else
                "OBTAIN_SEPARATE_INDEPENDENT_QA_AND_PUBLIC_VERSION_EVIDENCE"
            ),
        })

    if len(joined) != assessment["current_reference_count"]:
        raise DiscoveryError("Library review join cardinality mismatch")

    report = {
        "schema": SCHEMA,
        "status": STATUS,
        "public_assessment_sha256": assessment["assessment_sha256"],
        "signed_history_head_sha256": history["head_sha256"],
        "caller_supplied_head_checkpoint_matched": True,
        "external_checkpoint_independently_anchored": False,
        "signed_history_event_count": history["event_count"],
        "signed_history_revoked_references": history["owner_revoked_reference_count"],
        "public_evidence_chain_status": chain["status"],
        "public_evidence_chain_candidate_specific_qa": False,
        "latest_reference_count": len(joined),
        "states": dict(sorted(state_count.items())),
        "review_records": joined,
        "next_manual_reviews": [
            {"review_id_sha256": x["review_id_sha256"],
             "public_url": x["public_url"],
             "state": x["review_state"], "next_action": x["next_action"]}
            for x in joined
            if x["revision_change"] != "UNCHANGED_WITHIN_BATCH_SCOPE"
            or x["review_state"] in (
                "OWNER_REVOKED_BLOCKED_NO_GO",
                "REVIEW_FOR_OLDER_PINNED_EVIDENCE_NO_GO")
        ],
        "previously_selected_not_seen": assessment["previously_selected_not_seen"],
        "bounded_nonselection_does_not_mean_deleted": True,
        "owner_and_qa_signatures_mean": "KEYHOLDER_ASSERTIONS_ONLY_NOT_ACTUAL_INDEPENDENT_QA",
        "rule_candidate_approval_gate": "BLOCKED_PENDING_ACTUAL_INDEPENDENT_QA",
        "source_code_or_external_patch_executed": False,
        "independent_candidate_behavior_tests_run": 0,
        "independently_approved_rule_count": 0,
        "automatic_rule_promotions": 0,
        "signed_rulepacks_generated": 0,
        "network_requests": 0,
        "operating_database_writes": 0,
        "other_project_accesses": 0,
        "distribution_authorized": False,
        "production_approved": False,
    }
    report["closure_sha256"] = _digest(report)
    report["closure_sha256_is_signature"] = False
    return report
