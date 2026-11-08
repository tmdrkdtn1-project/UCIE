"""UCIE V1.2: truthful read-only proof of recent hourly miner activity.

No local scheduled-task claim from filesystem receipts alone. Owner must
combine this output with the existing task_status.ps1 -Evidence Windows
TaskScheduler event proof. Distinguishes Stage10 collection, Stage12
unverified review "learning", Stage16 safe public QA and V1.2 quality
monitor. None prove LLM training or auto-approval.
"""
from __future__ import annotations
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import re

from .public_hourly_staging import OPT_IN_FILENAME as STAGE10_MARKER
from .public_candidate_learning import OPT_IN_FILENAME as STAGE12_MARKER
from .public_safe_qa_cycle import OPT_IN as STAGE16_MARKER

SCHEMA = "UCIE_HOURLY_PUBLIC_LIBRARY_PROOF_V12"
MAX_RECEIPT = 4096
MAX_TAIL = 12288
ACCEPTED = ("COLLECTED_UNVERIFIED", "COLLECTED_UNVERIFIED_PARTIAL_NO_GO")
T10 = ("STAGE10_HOURLY_DISABLED", "STAGE10_UNVERIFIED_STAGED_NO_GO",
       "STAGE10_HOURLY_PARTIAL_NO_GO", "STAGE10_HOURLY_FAILED_NO_GO")
T12 = ("STAGE12_REVIEW_DISABLED", "STAGE12_UNVERIFIED_REVIEW_UPDATED_NO_GO")
T16 = ("STAGE16_SAFE_QA_DISABLED", "STAGE16_SAFE_QA_RATE_PAUSED_NO_GO",
       "STAGE16_SAFE_QA_ALREADY_ATTEMPTED_NO_GO",
       "STAGE16_SAFE_QA_24H_BUDGET_PAUSED_NO_GO",
       "STAGE16_SAFE_QA_OBSERVED_REVIEW_REQUIRED",
       "STAGE16_SAFE_QA_LEDGER_INCOMPLETE_NO_GO",
       "STAGE16_SAFE_QA_FAILED_NO_GO")
T17 = ("STAGE17_QUALITY_DISABLED", "STAGE17_QUALITY_OBSERVED_UNVERIFIED_NO_GO",
       "STAGE17_QUALITY_REVIEW_REQUIRED_NO_GO")
T13 = ("STAGE13_EXTERNAL_HISTORY_DISABLED", "EXTERNAL_HISTORY_BACKFILL_OK_NO_GO",
       "EXTERNAL_HISTORY_RATE_BUDGET_PAUSED_NO_GO",
       "EXTERNAL_HISTORY_UPSTREAM_OR_METADATA_FAILED_NO_GO")
T15 = ("STAGE15_FIX_EVIDENCE_DISABLED", "STAGE15_STRUCTURED_FIX_EVIDENCE_STAGED_NO_GO",
       "STAGE15_PUBLIC_EVIDENCE_REJECTED_PARTIAL_NO_GO")


class HourlyProofError(ValueError):
    pass


def _root(root: Path) -> Path:
    path = Path(root)
    if (path.name.casefold() != "ucie" or not path.is_dir()
            or path.is_symlink() or (path / "runtime").is_symlink()):
        raise HourlyProofError("UCIE-only runtime required")
    runtime = path / "runtime"
    if not runtime.is_dir():
        raise HourlyProofError("missing UCIE runtime")
    return runtime


def _file(path: Path, *, max_bytes: int) -> bytes:
    if path.is_symlink() or not path.is_file() or path.stat().st_size > max_bytes:
        raise HourlyProofError("unavailable/oversized runtime receipt")
    return path.read_bytes()


def _one(raw: bytes) -> dict:
    if len(raw) > MAX_RECEIPT:
        raise HourlyProofError("oversized bounded hourly receipt")
    try:
        result = json.loads(raw.decode("utf-8"))
    except (ValueError, UnicodeError) as exc:
        raise HourlyProofError("invalid hourly JSON") from exc
    if (type(result) is not dict
            or result.get("schema") != "UCIE_MINER_CYCLE_V1"
            or result.get("status") not in (*ACCEPTED, "COLLECTION_FAILED")
            or result.get("production_approved") is not False
            or result.get("verification_pass") != 0
            or type(result.get("new_candidates")) is not int
            or not 0 <= result["new_candidates"] <= 10
            or type(result.get("sources_checked")) is not int
            or not 0 <= result["sources_checked"] <= 2
            or type(result.get("consecutive_failures")) is not int
            or not 0 <= result["consecutive_failures"] <= 6):
        raise HourlyProofError("invalid public-only hourly receipt")
    for field, values in (
        ("stage10_status", T10), ("stage12_review_status", T12),
        ("stage13_history_status", T13),
        ("stage15_fix_evidence_status", T15),
        ("stage16_safe_qa_status", T16), ("stage17_quality_status", T17),
    ):
        if field in result and result[field] not in values:
            raise HourlyProofError("unrecognized optional-stage status")
    for field in ("started_utc", "finished_utc"):
        stamp = result.get(field)
        if type(stamp) is not str:
            raise HourlyProofError("missing UTC run timestamp")
        try:
            timestamp = datetime.fromisoformat(stamp.replace("Z", "+00:00"))
        except ValueError as exc:
            raise HourlyProofError("invalid UTC run timestamp") from exc
        if timestamp.tzinfo is None or timestamp.utcoffset() != timedelta(0):
            raise HourlyProofError("non-UTC hourly run timestamp")
    if datetime.fromisoformat(result["started_utc"]) > datetime.fromisoformat(
            result["finished_utc"]):
        raise HourlyProofError("hourly run clock inverted")
    return result


def _tail_two(history: Path) -> list[dict]:
    if history.is_symlink() or not history.is_file():
        raise HourlyProofError("missing safe hourly history")
    with history.open("rb") as stream:
        size = stream.seek(0, 2)
        if size <= 0:
            raise HourlyProofError("empty hourly history")
        stream.seek(max(0, size - MAX_TAIL))
        raw = stream.read(MAX_TAIL)
    # Discard potentially truncated first line; keep the two most recent.
    if size > MAX_TAIL:
        cut = raw.find(b"\n")
        if cut < 0:
            raise HourlyProofError("history line unbounded")
        raw = raw[cut+1:]
    if not raw.endswith(b"\n"):
        raise HourlyProofError("unterminated hourly receipt")
    lines = raw.splitlines()
    if len(lines) < 2:
        raise HourlyProofError("at least two completed hourly receipts required")
    return [_one(line) for line in lines[-2:]]


def _marker(runtime: Path, filename: str) -> str:
    path = runtime / filename
    if path.is_symlink():
        return "UNSAFE_MARKER_NO_GO"
    if not path.exists():
        return "NOT_ENABLED"
    if not path.is_file() or path.stat().st_size > 4096:
        return "INVALID_MARKER_NO_GO"
    return "MARKER_PRESENT_CONTENT_NOT_VERIFIED"


def inspect_hourly_public_library(root: Path, *, now: datetime | None = None) -> dict:
    runtime = _root(root)
    stamp = datetime.now(timezone.utc) if now is None else now
    if stamp.tzinfo is None or stamp.utcoffset() != timedelta(0):
        raise HourlyProofError("UTC aware clock required")
    last = _one(_file(runtime / "last_run.json", max_bytes=MAX_RECEIPT))
    prev, recent = _tail_two(runtime / "run_history.jsonl")
    if last != recent:
        raise HourlyProofError("last-run and history receipts disagree")
    started = datetime.fromisoformat(recent["started_utc"])
    prior_started = datetime.fromisoformat(prev["started_utc"])
    finished = datetime.fromisoformat(recent["finished_utc"])
    if started > stamp + timedelta(minutes=5) or finished > stamp + timedelta(minutes=5):
        raise HourlyProofError("hourly receipt in the future")
    delta_minutes = round((started-prior_started).total_seconds()/60, 2)
    age_minutes = round((stamp-finished).total_seconds()/60, 2)
    two_collected = prev["status"] == recent["status"] == "COLLECTED_UNVERIFIED"
    fresh = 0 <= age_minutes <= 90
    cadence = 50 <= delta_minutes <= 90
    # The base legacy collector may succeed even when the optional Stage10
    # action fails and the scheduled Python action returns nonzero. Preserve
    # the receipt as evidence, but do not report two healthy hourly cycles.
    stage10_outcomes = tuple(item.get("stage10_status", "UNOBSERVED")
                             for item in (prev, recent))
    stage10_problem = any(state in (
        "STAGE10_HOURLY_PARTIAL_NO_GO",
        "STAGE10_HOURLY_FAILED_NO_GO",
    ) for state in stage10_outcomes)
    healthy = (two_collected and fresh and cadence
               and recent["consecutive_failures"] == 0
               and not stage10_problem)
    # Snapshot alone is NOT TaskScheduler event/process proof. Existing
    # task_status.ps1 -Evidence must verify the scheduled task's real events.
    stage = {
        "stage10_public_candidate_collection": recent.get("stage10_status", "UNOBSERVED"),
        "stage12_unverified_review_learning": recent.get("stage12_review_status", "UNOBSERVED"),
        "stage13_public_history": recent.get("stage13_history_status", "UNOBSERVED"),
        "stage15_structured_fix_hints": recent.get("stage15_fix_evidence_status", "UNOBSERVED"),
        "stage16_safe_candidate_qa": recent.get("stage16_safe_qa_status", "UNOBSERVED"),
        "stage17_hourly_quality_audit": recent.get("stage17_quality_status", "UNOBSERVED"),
    }
    from .library_quality_loop_v12 import OPT_IN_FILENAME as STAGE17_MARKER
    markers = {
        "stage10": _marker(runtime, STAGE10_MARKER),
        "stage12": _marker(runtime, STAGE12_MARKER),
        "stage16": _marker(runtime, STAGE16_MARKER),
        "stage17": _marker(runtime, STAGE17_MARKER),
    }
    if any(x.endswith("NO_GO") for x in markers.values()):
        healthy = False
    report = {
        "schema": SCHEMA,
        "status": ("TWO_FRESH_CYCLE_RECEIPTS_OBSERVED_SCHEDULER_NOT_ATTESTED"
                   if healthy else "HOURLY_CYCLE_ACTIVITY_NOT_PROVEN_NO_GO"),
        "runtime_receipts_integrity_readable": True,
        "two_successful_collection_receipts": two_collected,
        "last_two_stage10_statuses": list(stage10_outcomes),
        "stage10_failure_or_partial_in_last_two": stage10_problem,
        "started_cadence_minutes": delta_minutes,
        "last_completed_age_minutes": age_minutes,
        "latest_started_utc": recent["started_utc"],
        "latest_finished_utc": recent["finished_utc"],
        "latest_collector_status": recent["status"],
        "latest_new_unverified_candidates": recent["new_candidates"],
        "stage_statuses": stage,
        "operator_marker_presence": markers,
        "task_scheduler_event_proof_checked": False,
        "task_scheduler_event_proof_command": "D:\\UCIE\\scripts\\task_status.ps1 -Evidence",
        "model_weights_trained": False,
        "candidate_fixes_independently_verified": 0,
        "automatically_approved_rules": 0,
        "code_self_modified": False,
        "operating_db_writes": 0,
        "scheduler_modified": False,
    }
    return report


def main() -> int:
    import argparse
    p = argparse.ArgumentParser(description="UCIE read-only hourly collection and library-stage evidence proof")
    p.add_argument("--root", default=None)
    a = p.parse_args()
    root = Path(__file__).resolve().parents[2] if a.root is None else Path(a.root)
    if a.root is not None and root.resolve() != Path(__file__).resolve().parents[2].resolve():
        print(json.dumps({"schema": SCHEMA, "status": "ROOT_NOT_ALLOWED_NO_GO"}))
        return 2
    try:
        result = inspect_hourly_public_library(root)
    except (HourlyProofError, OSError):
        print(json.dumps({"schema": SCHEMA, "status": "HOURLY_EVIDENCE_UNAVAILABLE_NO_GO"}))
        return 2
    print(json.dumps(result, ensure_ascii=True, sort_keys=True))
    return 0 if result["status"].startswith("TWO_FRESH_") else 2


if __name__ == "__main__":
    raise SystemExit(main())
