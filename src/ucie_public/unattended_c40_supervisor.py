"""UCIE-only C40 watchdog policy engine: NO process-control side effects.

Two distinct bounded functional observations are mandatory before requesting
owner-signed recovery. Process absence alone does not prove a tunnel failure.
No OS operations, task registration, host restart or arbitrary command calls.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from .policy import PolicyError
from .unattended_ops import _timestamp, preview_c40_recovery

SCHEMA = "UCIE_C40_WATCHDOG_DECISION_V1"
OBS_FIELDS = frozenset({
    "observed_at", "c40_process_count", "client_binary_and_profile_match",
    "process_owner_verified", "mcp_initialize_ok", "tools_list_ok",
    "legacy_library_search_ok", "admin_capabilities_ok",
})
RESTART_FIELDS = frozenset({
    "restarts_last_hour", "last_restart_utc", "supervisor_lock_held",
    "scheduler_miner_idle", "external_rollback_anchor_ok",
})
WINDOW = timedelta(minutes=10)
COOLDOWN = timedelta(minutes=20)


def _observe(item: object) -> tuple[datetime, bool]:
    if type(item) is not dict or set(item) != OBS_FIELDS:
        raise PolicyError("invalid bounded C40 watchdog observation")
    seen = _timestamp(item["observed_at"])
    if (type(item["c40_process_count"]) is not int or
            not 0 <= item["c40_process_count"] <= 2 or
            any(type(item[k]) is not bool for k in OBS_FIELDS - {
                "observed_at", "c40_process_count"})):
        raise PolicyError("invalid C40 observation type")
    if item["c40_process_count"] > 1:
        raise PolicyError("duplicate C40 client NO_GO; do not restart")
    healthy = (item["c40_process_count"] == 1 and
               all(item[k] is True for k in (
                   "client_binary_and_profile_match", "process_owner_verified",
                   "mcp_initialize_ok", "tools_list_ok",
                   "legacy_library_search_ok", "admin_capabilities_ok")))
    return seen, healthy


def decide_c40_recovery_need(observations: list, history: dict, *,
                             at_time: datetime | None = None) -> dict:
    """Return a non-executing decision from two recent host observations.

    The observer/transport must be verified by the future trusted UCIE host
    supervisor. Caller-provided booleans alone are NOT host attestation.
    """
    if type(observations) is not list or len(observations) != 2:
        raise PolicyError("C40 watchdog requires exactly two independent probes")
    now = datetime.now(timezone.utc) if at_time is None else at_time
    if (not isinstance(now, datetime) or now.tzinfo is None or
            now.utcoffset() != timedelta(0)):
        raise PolicyError("C40 watchdog UTC time required")
    (old_at, old_healthy), (new_at, new_healthy) = map(_observe, observations)
    if (old_at >= new_at or new_at > now + timedelta(seconds=60) or
            new_at < now - WINDOW or new_at - old_at > WINDOW):
        raise PolicyError("stale or reordered C40 functional probe")
    if type(history) is not dict or set(history) != RESTART_FIELDS:
        raise PolicyError("invalid C40 supervisor attempt state")
    if (type(history["restarts_last_hour"]) is not int or
            not 0 <= history["restarts_last_hour"] <= 100 or
            any(type(history[k]) is not bool for k in (
                "supervisor_lock_held", "scheduler_miner_idle",
                "external_rollback_anchor_ok"))):
        raise PolicyError("invalid C40 supervisor history values")
    last = history["last_restart_utc"]
    last_at = _timestamp(last) if last is not None else None
    if last_at is not None and last_at > now:
        raise PolicyError("future C40 recovery attempt")
    if new_healthy:
        state = "UCIE_C40_HEALTHY_NO_RECOVERY"
    elif old_healthy:
        state = "UCIE_C40_SINGLE_PROBE_FAILURE_CONFIRM_FIRST"
    elif (history["restarts_last_hour"] >= 2 or
            last_at is not None and now - last_at < COOLDOWN):
        state = "UCIE_C40_RECOVERY_RATE_BLOCKED"
    elif not all(history[k] is True for k in (
            "supervisor_lock_held", "scheduler_miner_idle",
            "external_rollback_anchor_ok")):
        state = "UCIE_C40_RECOVERY_TRUST_GATE_BLOCKED"
    else:
        state = "UCIE_C40_OWNER_SIGNED_RECOVERY_REQUIRED"
    return {
        "schema": SCHEMA, "status": state,
        "two_recent_host_observations_provided": True,
        "host_functionality_authenticated": False,
        "latest_functional_probe_healthy": new_healthy,
        "supervisor_owner_grant_required": state == "UCIE_C40_OWNER_SIGNED_RECOVERY_REQUIRED",
        "restart_performed": False, "old_process_terminated": False,
        "new_c40_client_started": False,
        "automatic_restart_registered": False,
        "other_project_accesses": 0,
    }


def bind_owner_recovery_plan(decision: dict, verified_grant: dict,
                             host_shutdown_observed: dict) -> dict:
    """Owner-signed recovery still NEEDS an independent verified host adapter."""
    if (type(decision) is not dict or
            decision.get("schema") != SCHEMA or
            decision.get("status") != "UCIE_C40_OWNER_SIGNED_RECOVERY_REQUIRED" or
            decision.get("restart_performed") is not False):
        raise PolicyError("C40 owner recovery not requested by watchdog")
    preflight = preview_c40_recovery(verified_grant, host_shutdown_observed)
    return {
        "status": "UCIE_C40_OWNER_RECOVERY_PLAN_BOUND_NO_RESTART",
        "task_id": preflight["task_id"],
        "signed_grant_sha256": preflight["signed_grant_sha256"],
        "requires_trusted_windows_owner_and_external_checkpoint": True,
        "requires_real_mcp_post_restart_probe": True,
        "restart_performed": False, "production_approved": False,
    }
