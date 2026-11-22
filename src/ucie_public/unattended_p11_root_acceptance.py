"""UCIE P11 — strict P10 owner-reported protected-root installation acceptance.

This accepts a bounded, source-pinned Windows owner output as an observation;
it does not execute a host process or independently attest the Windows ACL.
It is intentionally NOT a production activation / publisher authorization.
"""
from __future__ import annotations

import json
from .policy import PolicyError

SOURCE_SCHEMA = "UCIE_ONE_OWNER_PROTECTED_ROOT_BOOTSTRAP_P10_V1"
SCHEMA = "UCIE_PROTECTED_ROOT_OWNER_INSTALL_ACCEPTANCE_V1"
TARGET_ID = "WINDOWS_PROGRAMFILES_UCIE_UNATTENDEDHOST_ONE_ROOT"
CREATED_STATUS = "UCIE_P10_ONE_PROTECTED_DIRECTORY_CREATED_ACL_RECHECK_ONLY"
MAX_BYTES = 8192

FIELDS = frozenset({
    "schema", "project_id", "status", "target_identifier",
    "parent_exists_unlinked", "parent_acl_readable",
    "parent_owner_well_known_system_or_administrators",
    "parent_dacl_canonical",
    "parent_foreign_mutating_allow_ace_present",
    "parent_foreign_inherit_only_allow_ace_present",
    "parent_unresolved_allow_identity",
    "parent_ace_identity_read_directly_as_sid",
    "protected_parent_preflight_passed",
    "caller_elevated_administrator", "target_preexisted",
    "target_created_this_invocation",
    "target_exact_admin_and_system_acl_verified",
    "existing_ucie_bridge_modified", "existing_ucie_miner_modified",
    "scheduled_task_registered", "c40_process_restarted",
    "github_credential_read", "git_pushed",
    "owner_host_signer_provisioned", "external_antireplay_anchor_provisioned",
    "service_writer_identity_provisioned", "rule_auto_promotion_enabled",
    "unattended_worker_activated",
})
BOOL_KEYS = FIELDS - {"schema", "project_id", "status", "target_identifier"}
REQUIRED_TRUE = frozenset({
    "parent_exists_unlinked", "parent_acl_readable",
    "parent_owner_well_known_system_or_administrators",
    "parent_dacl_canonical", "parent_ace_identity_read_directly_as_sid",
    "protected_parent_preflight_passed", "caller_elevated_administrator",
    "target_created_this_invocation", "target_exact_admin_and_system_acl_verified",
})
REQUIRED_FALSE = BOOL_KEYS - REQUIRED_TRUE
OWNER_OBSERVATION_STATUS = "UCIE_P10_ONE_DIRECTORY_OWNER_REPORTED_CREATED_ACL_MATCH"
REJECTION_STATUS = "UCIE_P10_PROTECTED_ROOT_NOT_ACCEPTED_NO_GO"


def assess_p10_owner_root(report: dict) -> dict:
    """Strict diagnostic acceptance, never grants OS mutation or automation."""
    if (type(report) is not dict or set(report) != FIELDS or
            report["schema"] != SOURCE_SCHEMA or
            report["project_id"] != "UCIE" or
            report["target_identifier"] != TARGET_ID or
            type(report["status"]) is not str or
            any(type(report[k]) is not bool for k in BOOL_KEYS)):
        raise PolicyError("UCIE P10 root report malformed or foreign")
    successful = (
        report["status"] == CREATED_STATUS and
        all(report[k] is True for k in REQUIRED_TRUE) and
        all(report[k] is False for k in REQUIRED_FALSE)
    )
    return {
        "schema": SCHEMA,
        "project_id": "UCIE",
        "status": (
            OWNER_OBSERVATION_STATUS if successful else REJECTION_STATUS
        ),
        "owner_reported_root_created": bool(successful),
        "owner_reported_acl_exact": bool(
            report["target_exact_admin_and_system_acl_verified"]
            and report["target_created_this_invocation"]
            and report["target_preexisted"] is False
        ),
        "same_owner_source_claim_independently_attested": False,
        "post_bootstrap_independent_host_recheck": False,
        "protected_root_service_writer_ready": False,
        "host_signer_provisioned": False,
        "owner_signer_host_private_key_present": False,
        "external_monotonic_revocation_anchor": False,
        "protected_operational_journal_installed": False,
        "github_app_credential_verified": False,
        "c40_supervisor_registered": False,
        "c40_live_functional_recovery_verified": False,
        "automatic_git_publication_authorized": False,
        "automatic_rulepack_promotion": False,
        "unattended_host_go": False,
    }


def parse_p10_owner_root(raw: bytes) -> dict:
    if type(raw) is not bytes or not 1 <= len(raw) <= MAX_BYTES:
        raise PolicyError("UCIE P10 report envelope size invalid")

    def reject_duplicates(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("duplicate field in owner report")
            result[key] = value
        return result

    try:
        report = json.loads(raw.decode("utf-8"), object_pairs_hook=reject_duplicates)
    except (UnicodeError, ValueError) as exc:
        raise PolicyError("UCIE P10 report JSON invalid") from exc
    return assess_p10_owner_root(report)
