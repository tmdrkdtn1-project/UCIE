"""Bounded UCIE C40 recovery orchestration contract.

Injectable *synthetic* host adapter only. The privileged Windows adapter
must be separately reviewed and owner-installed with a genuine process
identity and OS-protected policy gate. This module never spawns, kills or
registers a service. Never interprets public source as a command.
"""
from __future__ import annotations

from .policy import PolicyError
from .unattended_c40_supervisor import SCHEMA as DECISION_SCHEMA

HEALTH_FIELDS = frozenset({
    "c40_client_count", "pinned_binary_sha256_matched",
    "pinned_profile_sha256_matched", "owner_sid_matched",
    "single_owner_lock_held", "public_miner_idle",
})
PROBE_FIELDS = frozenset({
    "initialize", "tools_list", "public_search",
    "admin_capabilities",
})


def _validate_health(value: dict, expected_count: int) -> None:
    if (type(value) is not dict or set(value) != HEALTH_FIELDS
            or type(value["c40_client_count"]) is not int
            or value["c40_client_count"] != expected_count
            or any(type(value[k]) is not bool or value[k] is not True
                   for k in HEALTH_FIELDS - {"c40_client_count"})):
        raise PolicyError("UCIE C40 process/owner identity not independently verified")


def _validate_probe(value: dict) -> bool:
    if type(value) is not dict or set(value) != PROBE_FIELDS or any(
            type(value[k]) is not bool for k in PROBE_FIELDS):
        raise PolicyError("untrusted UCIE C40 functional MCP probe shape")
    return all(value.values())


def synthetic_one_c40_recovery(decision: dict, plan: dict, adapter) -> dict:
    """Test fixed recovery order. NO concrete Windows process operations.

    Adapter must be a deliberately marked synthetic fixture. Requiring this
    marker is not a security boundary for untrusted Python, only an assertion
    that this function is not wired to a privileged host backend.
    """
    if (type(decision) is not dict or decision.get("schema") != DECISION_SCHEMA
            or decision.get("status") != "UCIE_C40_OWNER_SIGNED_RECOVERY_REQUIRED"
            or type(plan) is not dict
            or plan.get("status") != "UCIE_C40_OWNER_RECOVERY_PLAN_BOUND_NO_RESTART"
            or plan.get("restart_performed") is not False
            or getattr(adapter, "ucie_synthetic_only", None) is not True):
        raise PolicyError("UCIE C40 recovery execution not authorized")
    events = []
    first = adapter.observe()
    _validate_health(first, 1)
    events.append("ONE_IDENTIFIED_OWNER_C40")
    if _validate_probe(adapter.probe()):
        raise PolicyError("UCIE C40 unexpectedly healthy; must not restart")
    events.append("FUNCTIONAL_PROBE_FAILED")
    if adapter.stop_one_pinned() is not True:
        raise PolicyError("UCIE verified old C40 did not stop")
    events.append("OLD_C40_STOP_REQUEST_OBSERVED")
    # A second independent observation prevents two overlapping C40 clients.
    after_stop = adapter.observe()
    if after_stop.get("c40_client_count") != 0 or any(
            after_stop.get(k) is not True for k in HEALTH_FIELDS - {"c40_client_count"}):
        raise PolicyError("UCIE C40 old instance remains; refuse new client")
    events.append("OLD_C40_EXIT_CONFIRMED")
    if adapter.start_one_pinned() is not True:
        raise PolicyError("UCIE C40 new launch refused")
    events.append("PINNED_C40_RESTART_REQUEST_OBSERVED")
    post = adapter.observe()
    _validate_health(post, 1)
    if not _validate_probe(adapter.probe()):
        # No infinite retries; caller must require independent owner recovery.
        return {
            "status": "UCIE_SYNTHETIC_C40_POSTPROBE_FAILURE_HOLD",
            "events": events, "retry_allowed_without_new_grant": False,
            "requires_human_reconciliation": True,
            "actual_windows_process_touched": False,
            "real_live_mcp_verified": False,
            "production_approved": False,
        }
    events.append("MCP_FUNCTIONAL_POSTPROBE_PASS_SYNTHETIC")
    return {
        "status": "UCIE_SYNTHETIC_C40_RECOVERY_SEQUENCE_PASS",
        "events": events, "retry_allowed_without_new_grant": False,
        "requires_human_reconciliation": False,
        "actual_windows_process_touched": False,
        "real_live_mcp_verified": False,
        "production_approved": False,
    }
