"""UCIE P5: strict interpretation of owner-local Windows SID and ACL V2 facts.

Never confuses existing Bridge backup/audit state with the new unattended
operations journal. No filesystem, shell, scheduling, identity discovery,
secret retrieval, network calls, rule release, or permissions changes.
A user-provided JSON report is *not* independent host attestation.
"""
from __future__ import annotations

import json

from .policy import PolicyError

REPORT_SCHEMA = "UCIE_WINDOWS_IDENTITY_ACL_READONLY_DIAGNOSTIC_V2"
RESULT_SCHEMA = "UCIE_UNATTENDED_OWNER_IDENTITY_RECONCILIATION_V1"
BRIDGE_PATH = r"D:\UCIE\.ucie_bridge_state"
OPS_PATH = r"D:\UCIE_DATA\ucie_unattended_state"
ACL_FIELDS = frozenset({
    "exists_unlinked", "acl_readable", "owned_by_current_user",
    "owner_is_builtin_administrators", "owner_is_local_system",
    "inheritance_disabled", "broad_allow_write_ace_found",
    "acl_requires_owner_review",
})
FIELDS = frozenset({
    "schema", "project_id", "status", "root_exists_and_no_reparse_ancestors",
    "miner_task_present", "miner_task_account_sid_resolvable",
    "miner_task_sid_matches_current_user", "miner_task_logon_type",
    "miner_task_run_level", "miner_task_state", "supervisor_task_name_occupied",
    "existing_bridge_directory", "proposed_independent_operations_directory",
    "private_owner_key_provisioned_or_read", "windows_acl_modified",
    "existing_bridge_files_modified", "scheduled_task_modified",
    "service_restarted", "github_push_performed", "production_rule_promoted",
    "operator_install_authorized",
})
ROOT_BOOLEAN = frozenset({
    "root_exists_and_no_reparse_ancestors", "miner_task_present",
    "miner_task_account_sid_resolvable", "miner_task_sid_matches_current_user",
    "supervisor_task_name_occupied", "private_owner_key_provisioned_or_read",
    "windows_acl_modified", "existing_bridge_files_modified",
    "scheduled_task_modified", "service_restarted", "github_push_performed",
    "production_rule_promoted", "operator_install_authorized",
})
NO_CHANGES = (
    "private_owner_key_provisioned_or_read", "windows_acl_modified",
    "existing_bridge_files_modified", "scheduled_task_modified",
    "service_restarted", "github_push_performed", "production_rule_promoted",
    "operator_install_authorized",
)
MAX_BYTES = 8192


def _check_acl(value: object) -> None:
    if type(value) is not dict or set(value) != ACL_FIELDS or any(
        type(v) is not bool for v in value.values()
    ):
        raise PolicyError("UCIE host ACL summary malformed")
    if not value["exists_unlinked"] and any(
        value[field] for field in (
            "acl_readable", "owned_by_current_user", "owner_is_builtin_administrators",
            "owner_is_local_system", "inheritance_disabled",
            "broad_allow_write_ace_found",
        )
    ):
        raise PolicyError("missing UCIE directory cannot have measured owner/ACL")


def assess_owner_identity_acl_v2(report: dict) -> dict:
    """Bounded advisory; NEVER produces a deploy/permission authorization."""
    if (type(report) is not dict or set(report) != FIELDS or
            report["schema"] != REPORT_SCHEMA or
            report["project_id"] != "UCIE" or
            report["status"] != "DIAGNOSTIC_OBSERVATION_ONLY_NOT_HOST_APPROVAL" or
            any(type(report[k]) is not bool for k in ROOT_BOOLEAN) or
            type(report["miner_task_logon_type"]) is not str or
            report["miner_task_logon_type"] not in (
                "Interactive", "Password", "S4U", "ServiceAccount", "Group", "None",
                "InteractiveOrPassword", "UNKNOWN",
            ) or
            type(report["miner_task_run_level"]) is not str or
            report["miner_task_run_level"] not in ("Limited", "Highest", "UNKNOWN") or
            type(report["miner_task_state"]) is not str or
            report["miner_task_state"] not in (
                "Ready", "Running", "Disabled", "Queued", "Unknown", "NOT_FOUND",
            ) or any(report[key] for key in NO_CHANGES)):
        raise PolicyError("UCIE owner identity observation untrusted or mis-scoped")
    bridge = report["existing_bridge_directory"]
    ops = report["proposed_independent_operations_directory"]
    _check_acl(bridge)
    _check_acl(ops)
    task_ready = all(report[k] is True for k in (
        "root_exists_and_no_reparse_ancestors", "miner_task_present",
        "miner_task_account_sid_resolvable", "miner_task_sid_matches_current_user",
    )) and (report["miner_task_logon_type"] == "Interactive" and
            report["miner_task_run_level"] == "Limited" and
            report["miner_task_state"] == "Ready")
    bridge_exposure = (bridge["exists_unlinked"] and
                       bridge["acl_readable"] and
                       (bridge["broad_allow_write_ace_found"] or
                        not bridge["inheritance_disabled"] or
                        bridge["acl_requires_owner_review"]))
    ops_new = not ops["exists_unlinked"]
    ops_acceptable_observation = all((
        ops["exists_unlinked"], ops["acl_readable"],
        ops["owned_by_current_user"], ops["inheritance_disabled"],
        not ops["broad_allow_write_ace_found"],
        not ops["acl_requires_owner_review"],
        not ops["owner_is_builtin_administrators"],
        not ops["owner_is_local_system"],
    ))
    if not task_ready:
        state = "UCIE_OWNER_IDENTITY_OR_MINER_TASK_HOLD_NO_INSTALL"
    elif report["supervisor_task_name_occupied"]:
        state = "UCIE_SUPERVISOR_NAME_OCCUPIED_NO_INSTALL"
    elif not bridge["exists_unlinked"] or not bridge["acl_readable"]:
        state = "UCIE_EXISTING_BRIDGE_ACL_UNOBSERVED_REVIEW_REQUIRED"
    elif ops_new:
        state = "UCIE_OWNER_IDENTITY_CONFIRMED_SEPARATE_JOURNAL_SETUP_PENDING"
    elif not ops_acceptable_observation:
        state = "UCIE_SEPARATE_JOURNAL_ACL_UNTRUSTED_NO_INSTALL"
    else:
        state = "UCIE_JOURNAL_ACL_OBSERVED_INDEPENDENT_SECURITY_GATES_PENDING"
    return {
        "schema": RESULT_SCHEMA,
        "status": state,
        "existing_miner_task_sid_matches_current_user": report[
            "miner_task_sid_matches_current_user"
        ],
        "existing_miner_task_retained_unchanged": True,
        "existing_admin_bridge_state": (
            "OWNER_REVIEW_REQUIRED_POTENTIALLY_BROAD_WRITE"
            if bridge_exposure else "NO_BROAD_WRITE_OBSERVED_IN_V2"
        ),
        "existing_admin_bridge_acl_modified": False,
        "operations_journal_path": OPS_PATH,
        "operations_journal_present": ops["exists_unlinked"],
        "operations_journal_install_proposed": ops_new,
        "operations_journal_created": False,
        "host_report_independently_attested": False,
        "windows_host_install_approved": False,
        "external_antirollback_anchor_verified": False,
        "github_credentials_verified": False,
        "c40_restart_capability_activated": False,
        "automatic_git_push_activated": False,
        "automatic_rule_promotion_activated": False,
    }


def parse_owner_identity_acl_v2(raw: bytes) -> dict:
    if type(raw) is not bytes or not 1 <= len(raw) <= MAX_BYTES:
        raise PolicyError("UCIE host report payload size invalid")
    def reject_duplicates(pairs):
        seen = {}
        for k, v in pairs:
            if k in seen:
                raise ValueError("duplicate UCIE identity report field")
            seen[k] = v
        return seen
    try:
        data = json.loads(raw.decode("utf-8"), object_pairs_hook=reject_duplicates)
    except (UnicodeError, ValueError) as exc:
        raise PolicyError("UCIE host report JSON malformed") from exc
    return assess_owner_identity_acl_v2(data)
