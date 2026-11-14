"""UCIE P9: close ACL candidate search, preserve owner host NO-GO.

Accepts a *supplied* bounded P8 read-only observation, not an OS AccessCheck
or independently attested owner/host identity. Never selects a new directory
or grants a permission. This gate intentionally refuses both previous
candidates and routes to a separately approved service-private trust root.
No filesystem, network, host process, scheduler or rulepack operations.
"""
from __future__ import annotations

import json
from .policy import PolicyError

SCHEMA = "UCIE_OWNER_LOCALAPPDATA_ACE_SCOPE_READONLY_V2"
DECISION = "UCIE_PROTECTED_HOST_ROOT_DESIGN_GATE_V1"
SOURCE = "CURRENT_OWNER_LOCALAPPDATA_UCIE_UNATTENDED_STATE"
EXPECTED_FIELDS = frozenset({
    "schema", "project_id", "status", "target_identifier",
    "parent_exists", "parent_reparse_free", "parent_acl_readable",
    "parent_owned_by_current_user", "parent_acl_inheritance_enabled",
    "foreign_mutating_allow_count",
    "foreign_mutating_inherit_only_count",
    "foreign_mutating_effective_on_parent_count",
    "foreign_mutating_inherited_count",
    "foreign_mutating_can_inherit_to_children_count",
    "foreign_effective_parent_delete_child",
    "foreign_effective_parent_delete",
    "foreign_effective_parent_change_dacl_or_owner",
    "foreign_effective_parent_create_child",
    "foreign_effective_parent_write",
    "foreign_broad_effective_modify",
    "unresolved_allow_ace_identity", "target_already_exists",
    "os_accesscheck_executed", "security_grant_authorized",
    "new_directory_created", "existing_acl_changed",
    "service_restarted", "git_pushed", "automatic_rule_promotion",
})
COUNTS = (
    "foreign_mutating_allow_count",
    "foreign_mutating_inherit_only_count",
    "foreign_mutating_effective_on_parent_count",
    "foreign_mutating_inherited_count",
    "foreign_mutating_can_inherit_to_children_count",
)
BOOL_FIELDS = EXPECTED_FIELDS - frozenset(COUNTS) - frozenset({
    "schema", "project_id", "status", "target_identifier",
})
FORBIDDEN_SUCCESS = (
    "os_accesscheck_executed", "security_grant_authorized",
    "new_directory_created", "existing_acl_changed", "service_restarted",
    "git_pushed", "automatic_rule_promotion",
)
MAX_BYTES = 8192
PREVIOUS_PARENT = "UCIE_D_DATA_PARENT_REJECTED"
ALTERNATIVE_PARENT = "OWNER_LOCALAPPDATA_PARENT_REJECTED"
ROOT_PROPOSAL = "SERVICE_OWNED_PROTECTED_ROOT_DESIGN_ONLY"


def classify_owner_p8_candidate(report: dict) -> dict:
    """Evidence classification only. Source observation does not grant GO."""
    if (type(report) is not dict or set(report) != EXPECTED_FIELDS or
            report.get("schema") != SCHEMA or report.get("project_id") != "UCIE" or
            report.get("target_identifier") != SOURCE or
            report.get("status") not in {
                "UCIE_OWNER_LOCALAPPDATA_SCOPE_PRECONDITION_NO_GO",
                "UCIE_FOREIGN_EFFECTIVE_DESTRUCTIVE_PARENT_RIGHTS_NO_GO",
                "UCIE_FOREIGN_ACE_INHERIT_ONLY_CHILD_DACL_REVIEW_REQUIRED",
                "UCIE_FOREIGN_NONDESTRUCTIVE_PARENT_RIGHTS_REVIEW_REQUIRED",
                "UCIE_FOREIGN_ACE_APPLICABILITY_UNRESOLVED_NO_INSTALL",
            } or any(type(report[k]) is not bool for k in BOOL_FIELDS) or
            any(type(report[k]) is not int or report[k] < 0 or
                report[k] > 256 for k in COUNTS) or
            any(report[k] is not False for k in FORBIDDEN_SUCCESS)):
        raise PolicyError("UCIE P8 owner observation shape, provenance or scope invalid")
    total = report["foreign_mutating_allow_count"]
    effective = report["foreign_mutating_effective_on_parent_count"]
    inherit_only = report["foreign_mutating_inherit_only_count"]
    inherited = report["foreign_mutating_inherited_count"]
    child_inherit = report["foreign_mutating_can_inherit_to_children_count"]
    if (effective + inherit_only != total or inherited > total or
            child_inherit > total or
            any(report[k] for k in (
                "foreign_effective_parent_delete_child",
                "foreign_effective_parent_delete",
                "foreign_effective_parent_change_dacl_or_owner",
                "foreign_effective_parent_create_child",
                "foreign_effective_parent_write",
                "foreign_broad_effective_modify",
            )) and effective == 0):
        raise PolicyError("UCIE P8 ACE counters or access assertions inconsistent")
    # Parent DELETE is not equivalent to DELETE_CHILD. Neither implies an
    # actual successful Windows AccessCheck for an unknown foreign token.
    parent_delete_ace = report["foreign_effective_parent_delete"]
    parent_delete_child_ace = report["foreign_effective_parent_delete_child"]
    high_risk = parent_delete_ace or parent_delete_child_ace or report[
        "foreign_effective_parent_change_dacl_or_owner"
    ]
    return {
        "schema": DECISION,
        "project_id": "UCIE",
        "status": (
            "UCIE_EXISTING_CANDIDATE_REJECTED_PROTECTED_ROOT_DESIGN_REQUIRED"
            if high_risk or effective > 0
            else "UCIE_ALTERNATIVE_CANDIDATE_STILL_UNATTESTED_NO_GO"
        ),
        "previous_data_parent": PREVIOUS_PARENT,
        "alternative_parent": ALTERNATIVE_PARENT,
        "next_track": ROOT_PROPOSAL,
        "foreign_ace_count_observed": total,
        "foreign_effective_parent_ace_count_observed": effective,
        "foreign_parent_delete_allow_ace_observed": parent_delete_ace,
        "foreign_parent_delete_child_allow_ace_observed": parent_delete_child_ace,
        "parent_delete_is_not_delete_child": True,
        "foreign_effective_access_proven": False,
        "current_windows_host_independently_attested": False,
        "private_service_identity_provisioned": False,
        "protected_root_installed": False,
        "external_antirollback_anchor_verified": False,
        "owner_release_grant_obtained": False,
        "existing_bridge_acl_changed": False,
        "existing_miner_task_changed": False,
        "c40_restarted": False,
        "git_automation_activated": False,
        "rule_auto_promotion_activated": False,
        "install_authorized": False,
        "additional_random_parent_probing_required": False,
    }


def parse_owner_p8_candidate(raw: bytes) -> dict:
    """Bounded, strict JSON parser with duplicate-field rejection."""
    if type(raw) is not bytes or not 1 <= len(raw) <= MAX_BYTES:
        raise PolicyError("UCIE P8 JSON envelope size invalid")
    def unique_pairs(pairs):
        result = {}
        for name, value in pairs:
            if name in result:
                raise ValueError("duplicate P8 field")
            result[name] = value
        return result
    try:
        value = json.loads(raw.decode("utf-8"), object_pairs_hook=unique_pairs)
    except (ValueError, UnicodeError) as exc:
        raise PolicyError("UCIE P8 report JSON invalid") from exc
    return classify_owner_p8_candidate(value)
