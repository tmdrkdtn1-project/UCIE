"""UCIE-only public miner TaskScheduler read-only result diagnosis.

This module accepts only a sanitized, fixed-task observation. It does not
inspect Windows, execute PowerShell, read files, or change TaskScheduler.
LastTaskResult is a run-time status, not always a failure exit code.
Official scheduler status codes: Microsoft Task Scheduler WinError.h.
"""
from __future__ import annotations

import json
import sys

SCHEMA = "UCIE_PUBLIC_MINER_SCHEDULER_DIAGNOSTIC_V01"
SOURCE_SCHEMA = "UCIE_PUBLIC_MINER_SCHEDULER_SOURCE_FIXED_V01"
PROOF_SCHEMA = "UCIE_HOURLY_LOCAL_OPERATIONS_READONLY_V1"
NO_GO = "PUBLIC_MINER_SCHEDULER_NOT_ATTESTED_NO_GO"
GO = "PUBLIC_MINER_TWO_CYCLE_SCHEDULED_EVIDENCE_OBSERVED"
MAX_BYTES = 16000
MAX_COUNTER = 64
RESULTS = {
    0: "LAST_TASK_RESULT_ZERO",
    0x00041300: "SCHED_S_TASK_READY",
    0x00041301: "SCHED_S_TASK_RUNNING",
    0x00041302: "SCHED_S_TASK_DISABLED",
    0x00041303: "SCHED_S_TASK_HAS_NOT_RUN",
    0x00041304: "SCHED_S_TASK_NO_MORE_RUNS",
    0x00041305: "SCHED_S_TASK_NOT_SCHEDULED",
    0x00041306: "SCHED_S_TASK_TERMINATED",
    0x00041307: "SCHED_S_TASK_NO_VALID_TRIGGERS",
    0x80041320: "SCHED_E_USER_NOT_LOGGED_ON",
    0x80041323: "SCHED_E_SERVICE_TOO_BUSY",
}
OBSERVED_STATUSES = frozenset((
    "TWO_CYCLE_BASE_COLLECTOR_OBSERVED",
    "TWO_CYCLE_BASE_COLLECTOR_OBSERVED_STAGE13_RESUMED",
    "TWO_CYCLE_BASE_COLLECTOR_OBSERVED_STAGE13_RATE_PAUSED",
))
KNOWN_STATUSES = OBSERVED_STATUSES | frozenset((
    "NOT_REGISTERED_NO_GO",
    "TASK_IDENTITY_OR_CADENCE_NO_GO",
    "LAST_TASK_RESULT_NO_GO",
    "TWO_RECENT_HOURLY_CYCLES_NOT_PROVEN_NO_GO",
    "TASK_SCHEDULER_EVENT_LOG_UNAVAILABLE_NO_GO",
    "LAST_SCHEDULED_RUN_RECEIPT_MISMATCH_NO_GO",
))


class SchedulerEvidenceError(ValueError):
    """Untrusted or inconsistent exact-UCIE-task status."""


def _flag(d: dict, key: str) -> bool:
    value = d.get(key)
    if type(value) is not bool:
        raise SchedulerEvidenceError("missing or nonboolean scheduler evidence")
    return value


def analyze_scheduler_observation(data: dict) -> dict:
    """Derive a diagnostic from fixed UCIE-scheduler fields, never repair."""
    if type(data) is not dict or set(data) != {
            "schema", "task_found", "task_state", "last_task_result",
            "evidence"} or data.get("schema") != SOURCE_SCHEMA:
        raise SchedulerEvidenceError("unknown scheduler observation contract")
    found = _flag(data, "task_found")
    state = data["task_state"]
    code = data["last_task_result"]
    if (type(state) is not str or state not in (
            "Absent", "Ready", "Running", "Disabled", "Queued", "Unknown")
            or (not found and (state != "Absent" or code is not None))
            or (found and (state == "Absent" or type(code) is not int
                           or not 0 <= code <= 0xFFFFFFFF))):
        raise SchedulerEvidenceError("invalid fixed task state or result code")
    evidence = data["evidence"]
    if type(evidence) is not dict or set(evidence) != {
            "schema", "status", "scheduled_task_registered",
            "action_matches_ucie_only", "owner_least_privilege_verified",
            "hourly_no_overlap_configured", "last_task_result_zero",
            "scheduler_event_log_readable",
            "scheduler_event_instance_receipts_verified",
            "last_scheduled_run_matches_receipt",
            "two_recent_hourly_successes", "scheduler_changed",
            "database_modified"} or evidence.get("schema") != PROOF_SCHEMA:
        raise SchedulerEvidenceError("invalid bounded original task proof")
    status = evidence.get("status")
    if type(status) is not str or status not in KNOWN_STATUSES:
        raise SchedulerEvidenceError("unrecognized TaskScheduler proof status")
    count = evidence["scheduler_event_instance_receipts_verified"]
    if type(count) is not int or not 0 <= count <= MAX_COUNTER:
        raise SchedulerEvidenceError("untrusted task event count")
    for key in (set(evidence) - {
            "schema", "status", "scheduler_event_instance_receipts_verified"}):
        _flag(evidence, key)
    if (evidence["scheduled_task_registered"] is not found
            or (found and evidence["last_task_result_zero"] is not (code == 0))
            or evidence["scheduler_changed"]
            or evidence["database_modified"]):
        raise SchedulerEvidenceError("task identity / code / side-effect drift")
    reason = RESULTS.get(code, "NONZERO_RESULT_UNKNOWN_EXACT_CODE_REQUIRED")
    if not found:
        reason = "UCIE_PUBLIC_MINER_TASK_NOT_REGISTERED"
    blockers = []
    if not found:
        blockers.append("EXACT_UCIE_TASK_MISSING")
    if found and code != 0:
        blockers.append("LAST_TASK_RESULT_NONZERO_NOT_COMPLETED_PASS")
    if found and code == 0 and state not in ("Ready",):
        blockers.append("TASK_STATE_NOT_READY_FOR_NEXT_CYCLE")
    if not evidence["action_matches_ucie_only"]:
        blockers.append("TASK_ACTION_IDENTITY_NOT_PROVEN")
    if not evidence["owner_least_privilege_verified"]:
        blockers.append("TASK_PRINCIPAL_NOT_PROVEN")
    if not evidence["hourly_no_overlap_configured"]:
        blockers.append("HOURLY_NO_OVERLAP_NOT_PROVEN")
    if not evidence["scheduler_event_log_readable"]:
        blockers.append("SCHEDULER_EVENT_LOG_UNAVAILABLE")
    if count != 2:
        blockers.append("TWO_EXACT_INSTANCE_EVENT_RECEIPTS_NOT_PROVEN")
    if not evidence["last_scheduled_run_matches_receipt"]:
        blockers.append("LATEST_RUN_NOT_BOUND_TO_EXACT_TASK_INSTANCE")
    if not evidence["two_recent_hourly_successes"]:
        blockers.append("TWO_RECENT_SCHEDULED_CYCLES_NOT_ATTESTED")
    if status not in OBSERVED_STATUSES:
        blockers.append("ORIGINAL_OWNER_EVIDENCE_NO_GO")
    if (code == 0x00041301 and state == "Running"):
        blockers.append("RUNNING_TASK_WAIT_FOR_COMPLETED_EVENT_BEFORE_GO")
    if code == 0x00041301 and state != "Running":
        blockers.append("LAST_RUNNING_CODE_AND_CURRENT_STATE_DIFFER")
    if code == 0x00041306:
        blockers.append("SCHEDULER_REPORTED_LAST_RUN_TERMINATED")
    if code not in RESULTS and code is not None:
        blockers.append("UNKNOWN_RESULT_REQUIRES_EXACT_EVENT_TRIAGE")
    good = found and state == "Ready" and code == 0 and count == 2 and (
        all(evidence[x] for x in (
            "action_matches_ucie_only", "owner_least_privilege_verified",
            "hourly_no_overlap_configured", "scheduler_event_log_readable",
            "last_scheduled_run_matches_receipt",
            "two_recent_hourly_successes"))
        and status in OBSERVED_STATUSES and not blockers)
    return {
        "schema": SCHEMA,
        "status": GO if good else NO_GO,
        "fixed_task": r"\UCIE-PublicMiner-Hourly",
        "task_state": state,
        "last_task_result_decimal": code,
        "last_task_result_hex": None if code is None else f"0x{code:08X}",
        "last_task_result_interpretation": reason,
        "task_evidence_status": status,
        "matched_event_instances": count,
        "required_event_instances": 2,
        "scheduler_event_log_readable":
            evidence["scheduler_event_log_readable"],
        "blocker_codes": blockers,
        "classification_is_not_new_event_or_process_proof": True,
        "actual_task_mutation": False,
        "operating_database_writes": 0,
        "public_network_requests": 0,
        "other_project_access": False,
        "remediation_executed": False,
        "code_auto_promotion": False,
    }


def main() -> int:
    raw = sys.stdin.buffer.read(MAX_BYTES + 1)
    if not raw or len(raw) > MAX_BYTES:
        print(json.dumps({"schema": SCHEMA, "status": NO_GO,
                          "reason": "MISSING_OR_OVERSIZED_BOUNDED_INPUT"}))
        return 2
    try:
        observation = json.loads(raw.decode("utf-8"))
        result = analyze_scheduler_observation(observation)
    except (UnicodeError, ValueError, TypeError, KeyError):
        print(json.dumps({"schema": SCHEMA, "status": NO_GO,
                          "reason": "UNTRUSTED_FIXED_TASK_EVIDENCE"}))
        return 2
    print(json.dumps(result, sort_keys=True, ensure_ascii=True))
    # Return 0 when a valid NO_GO diagnosis was produced. It is not GO.
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
