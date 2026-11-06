"""Strict UCIE-only Windows readiness report interpretation, no host execution.

The inspector report is an unauthenticated observation. Passing this evaluator
never grants installation, GitHub write or C40 restart authority. Report must
be obtained from the exact owner PC and independently attested before use.
"""
from __future__ import annotations

import json

from .policy import PolicyError
from .unattended_ops import SHA64

SCHEMA = "UCIE_WINDOWS_HOST_READONLY_PREFLIGHT_V1"
EXPECTED = frozenset({
    "schema", "project_id", "status",
    "current_user_sid_present", "root_exact_exists_and_not_linked",
    "git_checkout_exists", "git_origin_exact_ucie_https",
    "git_tracked_worktree_clean", "public_miner_file_present",
    "python_executable_present", "existing_hourly_miner_task_present",
    "existing_hourly_miner_principal_matches_current_user",
    "existing_hourly_miner_action_matches",
    "existing_hourly_miner_state",
    "c40_exact_ucie_profile_client_pair_unique", "c40_matched_pairs_count",
    "c40_profile_regular_file_present", "c40_client_regular_file_present",
    "c40_profile_sha256", "c40_client_sha256",
    "future_supervisor_task_name_is_already_occupied",
    "ucie_journal_dir_regular_and_not_linked",
    "ucie_journal_owner_sid_matches_current_user",
    "ucie_journal_acl_inheritance_disabled",
    "ucie_journal_broad_write_ace_denied",
    "owner_acl_independently_verified", "monotonic_external_anchor_verified",
    "short_lived_github_credential_verified", "c40_live_functional_probe_verified",
    "actual_host_service_installed", "service_restarted",
    "git_pushed", "task_registered", "automatic_rule_promotions",
})
BOOLEAN_FIELDS = frozenset({
    "current_user_sid_present", "root_exact_exists_and_not_linked",
    "git_checkout_exists", "git_origin_exact_ucie_https",
    "git_tracked_worktree_clean", "public_miner_file_present",
    "python_executable_present", "existing_hourly_miner_task_present",
    "existing_hourly_miner_principal_matches_current_user",
    "existing_hourly_miner_action_matches",
    "c40_exact_ucie_profile_client_pair_unique",
    "c40_profile_regular_file_present", "c40_client_regular_file_present",
    "future_supervisor_task_name_is_already_occupied",
    "ucie_journal_dir_regular_and_not_linked",
    "ucie_journal_owner_sid_matches_current_user",
    "ucie_journal_acl_inheritance_disabled",
    "ucie_journal_broad_write_ace_denied",
    "owner_acl_independently_verified", "monotonic_external_anchor_verified",
    "short_lived_github_credential_verified", "c40_live_functional_probe_verified",
    "actual_host_service_installed", "service_restarted",
    "git_pushed", "task_registered",
})
REQUIRED_TRUE = (
    "current_user_sid_present", "root_exact_exists_and_not_linked",
    "git_checkout_exists", "git_origin_exact_ucie_https",
    "git_tracked_worktree_clean", "public_miner_file_present",
    "python_executable_present", "existing_hourly_miner_task_present",
    "existing_hourly_miner_principal_matches_current_user",
    "existing_hourly_miner_action_matches",
    "c40_exact_ucie_profile_client_pair_unique",
    "c40_profile_regular_file_present", "c40_client_regular_file_present",
)
JOURNAL_REQUIRED = (
    "ucie_journal_dir_regular_and_not_linked",
    "ucie_journal_owner_sid_matches_current_user",
    "ucie_journal_acl_inheritance_disabled",
    "ucie_journal_broad_write_ace_denied",
)
BANNED_TRUE = (
    "future_supervisor_task_name_is_already_occupied",
    "actual_host_service_installed", "service_restarted",
    "git_pushed", "task_registered",
)
EXPECTED_FALSE = (
    "owner_acl_independently_verified", "monotonic_external_anchor_verified",
    "short_lived_github_credential_verified", "c40_live_functional_probe_verified",
)
MAX_REPORT_BYTES = 12000


def evaluate_ucie_host_preflight(report: dict) -> dict:
    """Fail closed on foreign, incomplete or overclaiming host observations."""
    if (type(report) is not dict or set(report) != EXPECTED or
            report["schema"] != SCHEMA or report["project_id"] != "UCIE" or
            report["status"] != "READONLY_OBSERVATION_HOST_ACTIVATION_NOT_AUTHORIZED"
            or any(type(report[k]) is not bool for k in BOOLEAN_FIELDS)
            or type(report["automatic_rule_promotions"]) is not int or
            report["automatic_rule_promotions"] != 0 or
            type(report["c40_matched_pairs_count"]) is not int or
            not 0 <= report["c40_matched_pairs_count"] <= 2 or
            type(report["existing_hourly_miner_state"]) is not str or
            report["existing_hourly_miner_state"] not in (
                "Ready", "Running", "Disabled", "Queued", "Unknown", "NOT_FOUND",
            )):
        raise PolicyError("UCIE host observation malformed or falsely claims execution")
    pairs = report["c40_matched_pairs_count"]
    if report["c40_exact_ucie_profile_client_pair_unique"] != (pairs == 1):
        raise PolicyError("UCIE host C40 paired-path count contradicted")
    for key in ("c40_profile_sha256", "c40_client_sha256"):
        value = report[key]
        if report["c40_exact_ucie_profile_client_pair_unique"]:
            if type(value) is not str or SHA64.fullmatch(value) is None:
                raise PolicyError("UCIE pinned C40 file hash missing")
        elif value is not None:
            raise PolicyError("UCIE ambiguous C40 match must not publish a hash")
    if any(report[k] is not False for k in EXPECTED_FALSE):
        raise PolicyError("UCIE preflight falsely states OS/credential/health attestation")
    if any(report[k] is not False for k in (
            "actual_host_service_installed", "service_restarted",
            "git_pushed", "task_registered")):
        raise PolicyError("UCIE read-only preflight falsely claims host mutation")
    failed = sorted(k for k in REQUIRED_TRUE if report[k] is not True)
    failed += sorted(k for k in BANNED_TRUE if report[k] is True)
    if report["existing_hourly_miner_state"] not in ("Ready", "Running"):
        failed.append("existing_hourly_miner_state")
    if failed:
        status = "UCIE_OWNER_HOST_OBSERVATION_BLOCKED_NO_INSTALL"
    else:
        status = "UCIE_OWNER_HOST_OBSERVATION_CANDIDATE_BOOTSTRAP_PENDING"
    bootstrap = sorted(k for k in JOURNAL_REQUIRED if report[k] is not True)
    bootstrap += [
        "owner_acl_independently_verified",
        "monotonic_external_anchor_verified",
        "short_lived_github_credential_verified",
        "c40_live_functional_probe_verified",
    ]
    return {
        "schema": "UCIE_OWNER_HOST_READINESS_DECISION_V1",
        "status": status,
        "observation_blockers": failed,
        "bootstrap_or_independent_acceptance_remaining": bootstrap,
        "source_script_executed_by_this_evaluator": False,
        "os_observation_independently_attested": False,
        "owner_approval_obtained": False,
        "task_registration_permitted": False,
        "service_restart_permitted": False,
        "automatic_git_push_permitted": False,
        "automatic_rule_promotion_permitted": False,
    }


def parse_ucie_host_preflight(raw: bytes) -> dict:
    if type(raw) is not bytes or not 1 <= len(raw) <= MAX_REPORT_BYTES:
        raise PolicyError("UCIE host preflight bounded JSON bytes required")
    def no_duplicates(pairs):
        obj = {}
        for k, v in pairs:
            if k in obj:
                raise ValueError("duplicate UCIE host preflight field")
            obj[k] = v
        return obj
    try:
        report = json.loads(raw.decode("utf-8"), object_pairs_hook=no_duplicates)
    except (UnicodeError, ValueError) as exc:
        raise PolicyError("invalid UCIE host preflight JSON") from exc
    return evaluate_ucie_host_preflight(report)
