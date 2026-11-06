"""UCIE public miner: exact instance event timeline vs two run receipts.

Pure bounded analyzer. No Windows task calls, source execution, DB reads,
network requests, authorization, mutations or model training.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json
import sys

SCHEMA = "UCIE_PUBLIC_MINER_POST_RECEIPT_EXIT_TIMELINE_V01"
INPUT_SCHEMA = "UCIE_PUBLIC_MINER_EXACT_TASK_TIMELINE_INPUT_V01"
FAIL = "EXACT_TASK_POST_RECEIPT_EXIT_NOT_PROVEN_NO_GO"
NONZERO = "EXACT_TASK_ACTION_NONZERO_AFTER_RECEIPT_NO_GO"
OBSERVED = "EXACT_TASK_ZERO_EXIT_AFTER_RECEIPT_OBSERVED_NOT_SCHEDULER_GO"
MAX_BYTES = 24000
MAX_INSTANCES = 16
RECEIPT_KEYS = frozenset((
    "schema", "status", "started_utc", "finished_utc",
    "verification_pass", "production_approved"))
INSTANCE_KEYS = frozenset((
    "event_100_utc", "event_200_utc", "event_201_utc", "event_102_utc",
    "action_is_exact_python", "result_code_201", "event_duplicated"))


class ExitTimelineError(ValueError):
    """Fail closed for untrusted receipts/event source shape."""


def _utc(value: str) -> datetime:
    if type(value) is not str or not 12 <= len(value) <= 48:
        raise ExitTimelineError("bad event or receipt timestamp")
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ExitTimelineError("invalid event or receipt UTC") from exc
    if dt.tzinfo is None or dt.utcoffset() != timedelta(0):
        raise ExitTimelineError("UTC offset required")
    return dt


def _receipt(item: dict) -> tuple[datetime, datetime]:
    if (type(item) is not dict or set(item) != RECEIPT_KEYS
            or item["schema"] != "UCIE_MINER_CYCLE_V1"
            or item["status"] != "COLLECTED_UNVERIFIED"
            or item["verification_pass"] != 0
            or type(item["verification_pass"]) is not int
            or item["production_approved"] is not False):
        raise ExitTimelineError("unknown/unsafe public receipt")
    start = _utc(item["started_utc"])
    finish = _utc(item["finished_utc"])
    if start > finish or finish - start > timedelta(minutes=30):
        raise ExitTimelineError("impossible public cycle duration")
    return start, finish


def _instance(item: dict) -> dict:
    if type(item) is not dict or set(item) != INSTANCE_KEYS:
        raise ExitTimelineError("invalid exact-task event shape")
    for key in ("action_is_exact_python", "event_duplicated"):
        if type(item[key]) is not bool:
            raise ExitTimelineError("invalid task event validation flag")
    times = [_utc(item[key]) for key in (
        "event_100_utc", "event_200_utc",
        "event_201_utc", "event_102_utc")]
    code = item["result_code_201"]
    if type(code) is not int or not 0 <= code <= 0xFFFFFFFF:
        raise ExitTimelineError("invalid action 201 result code")
    valid_order = (
        times[0] <= times[1] <= times[2] <= times[3]
        and times[1] - times[0] <= timedelta(seconds=10)
        and times[3] - times[2] <= timedelta(seconds=10)
        and times[3] - times[0] <= timedelta(minutes=30))
    return {
        "times": times, "code": code,
        "valid_order": valid_order,
        "action_match": item["action_is_exact_python"],
        "not_duplicate": not item["event_duplicated"],
    }


def compare_post_receipt_exit(data: dict) -> dict:
    """Only exact matched event instances can witness action exit.

    Even a success is NOT proof of production root-cause or future scheduler
    health. Completed W08 style receipts are never process-exit receipts.
    """
    if (type(data) is not dict or set(data) != {
            "schema", "source", "receipts", "instances", "task_writes"}
            or data["schema"] != INPUT_SCHEMA
            or data["source"] != "OWNER_EXACT_TASK_XPATH_READONLY"
            or data["task_writes"] is not False
            or type(data["receipts"]) is not list
            or len(data["receipts"]) != 2
            or type(data["instances"]) is not list
            or len(data["instances"]) > MAX_INSTANCES):
        raise ExitTimelineError("unknown bounded task timeline input")
    receipts = [_receipt(item) for item in data["receipts"]]
    if receipts[0][1] >= receipts[1][0]:
        raise ExitTimelineError("overlapping or reversed receipts")
    instances = [_instance(item) for item in data["instances"]]
    matches = []
    used = set()
    for started, finished in receipts:
        options = []
        for i, instance in enumerate(instances):
            ts = instance["times"]
            # Match exact task EVENT start to miner recorded start, including
            # original worker's one-second timestamp resolution.
            if (instance["valid_order"] and instance["action_match"]
                    and instance["not_duplicate"]
                    and ts[0] - timedelta(seconds=2) <= started
                    <= ts[1] + timedelta(seconds=10)
                    and ts[1] - timedelta(seconds=2) <= finished
                    <= ts[2] + timedelta(seconds=2)):
                options.append(i)
        if len(options) != 1 or options[0] in used:
            matches.append({
                "status": "TASK_INSTANCE_OR_RECEIPT_NOT_UNIQUELY_LINKED_NO_GO",
                "action_result": None,
                "post_receipt_exit_lag_seconds": None,
                "clean_action_exit_observed": False,
            })
            continue
        index = options[0]
        used.add(index)
        instance = instances[index]
        exit_utc = instance["times"][2]
        elapsed = (exit_utc - finished).total_seconds()
        matches.append({
            "status": ("ZERO_ACTION_EXIT_AFTER_RECEIPT" if instance["code"] == 0
                       else "NONZERO_ACTION_EXIT_AFTER_RECEIPT_NO_GO"),
            "action_result": instance["code"],
            "action_result_hex": f"0x{instance['code']:08X}",
            "post_receipt_exit_lag_seconds": round(elapsed, 3),
            "action_elapsed_seconds": round(
                (exit_utc - instance["times"][1]).total_seconds(), 3),
            "clean_action_exit_observed": instance["code"] == 0,
        })
    complete = all(m["action_result"] is not None for m in matches)
    zero = complete and all(m["clean_action_exit_observed"] for m in matches)
    result_status = (OBSERVED if zero else
                     NONZERO if complete else FAIL)
    return {
        "schema": SCHEMA,
        "status": result_status,
        "matched_receipt_count": sum(
            m["action_result"] is not None for m in matches),
        "required_receipts": 2,
        "receipts": matches,
        "observed_nonzero_action_events": sum(
            m["action_result"] is not None and m["action_result"] != 0
            for m in matches),
        "exact_windows_task_healthy_attested": False,
        "zero_action_exit_code_observed_for_both": zero,
        "real_scheduled_python_natural_exit_proven": False,
        "production_termination_root_cause_proven": False,
        "termination_at_task_time_limit_confirmed": False,
        "event_instance_guid_disclosed": False,
        "task_scheduler_mutated": False,
        "operating_database_writes": 0,
        "public_network_requests": 0,
        "other_project_access": False,
        "model_training_performed": False,
    }


def main() -> int:
    raw = sys.stdin.buffer.read(MAX_BYTES + 1)
    if not raw or len(raw) > MAX_BYTES:
        print(json.dumps({"schema": SCHEMA, "status": FAIL}))
        return 2
    try:
        data = json.loads(raw.decode("utf-8"))
        out = compare_post_receipt_exit(data)
    except (ExitTimelineError, ValueError, TypeError, KeyError, UnicodeError):
        print(json.dumps({"schema": SCHEMA, "status": FAIL}))
        return 2
    print(json.dumps(out, sort_keys=True, ensure_ascii=True))
    return 0 if out["matched_receipt_count"] == 2 else 2


if __name__ == "__main__":
    raise SystemExit(main())
