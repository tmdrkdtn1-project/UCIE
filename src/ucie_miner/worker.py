"""Bounded, single-instance local worker for public-source candidate collection.

The worker stores only local run receipts and an unverified candidate database.
It does not execute downloaded patches, use GitHub credentials, read projects,
publish knowledge, or register its own scheduler.
"""
from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timezone
import errno
import json
import os
from pathlib import Path
import tempfile
from time import perf_counter_ns
from typing import Callable, Iterator

from .core import mine_once, report
from .schedule_policy import next_cycle


def _utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _bounded_elapsed_ms(start_ns: int) -> int:
    # Local monotonic measurements only; no external text or identifiers.
    # Saturate to a bounded receipt field, never create another telemetry DB.
    return min(3_600_000, max(0, (perf_counter_ns() - start_ns) // 1_000_000))


def _runtime(repo_root: Path) -> Path:
    if repo_root.is_symlink():
        raise ValueError("UCIE repository directory must not be a symbolic link")
    runtime = repo_root / "runtime"
    if runtime.is_symlink():
        raise ValueError("runtime directory must not be a symbolic link")
    if runtime.exists() and not runtime.is_dir():
        raise ValueError("runtime is not a directory")
    runtime.mkdir(exist_ok=True)
    return runtime


@contextmanager
def _single_instance(runtime: Path) -> Iterator[bool]:
    """An OS-held byte lock, automatically released after crashes/termination."""
    lockfile = runtime / "public_miner.lock"
    if lockfile.is_symlink():
        raise ValueError("unsafe lockfile link")
    with open(lockfile, "a+b") as handle:
        if handle.seek(0, os.SEEK_END) == 0:
            handle.write(b"\0")
            handle.flush()
        handle.seek(0)
        try:
            if os.name == "nt":
                import msvcrt
                msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as exc:
            if isinstance(exc, BlockingIOError) or exc.errno in (errno.EAGAIN, errno.EACCES):
                yield False
                return
            raise
        try:
            yield True
        finally:
            handle.seek(0)
            if os.name == "nt":
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def _write_receipt(runtime: Path, result: dict) -> None:
    """Save a bounded, generic receipt; never print/store exception messages."""
    data = (json.dumps(result, sort_keys=True, ensure_ascii=True) + "\n").encode("utf-8")
    if len(data) > 4096:
        raise ValueError("oversized run receipt")
    last = runtime / "last_run.json"
    history = runtime / "run_history.jsonl"
    if last.is_symlink() or history.is_symlink():
        raise ValueError("unsafe run receipt path")
    fd, temporary = tempfile.mkstemp(prefix=".ucie_receipt_", suffix=".tmp", dir=runtime)
    try:
        with os.fdopen(fd, "wb") as fp:
            fp.write(data)
            fp.flush()
            os.fsync(fp.fileno())
        os.replace(temporary, last)
    finally:
        Path(temporary).unlink(missing_ok=True)
    with open(history, "ab") as fp:
        fp.write(data)
        fp.flush()
        os.fsync(fp.fileno())


def run_cycle(
    repo_root: Path,
    *,
    collect: Callable[..., dict] = mine_once,
    write_report: Callable[[Path], Path] = report,
    enforce_schedule: bool = False,
) -> dict:
    """One bounded mining+report cycle. No background threads or external auth."""
    start = _utc()
    runtime = _runtime(repo_root)
    with _single_instance(runtime) as acquired:
        if not acquired:
            return {
                "schema": "UCIE_MINER_CYCLE_V1",
                "status": "SKIPPED_ALREADY_RUNNING",
                "started_utc": start,
                "verification_pass": 0,
                "production_approved": False,
            }
        if enforce_schedule:
            last = runtime / "last_run.json"
            if last.is_symlink():
                raise ValueError("unsafe last-run receipt path")
            prior = None
            prior_started = None
            failures = 0
            if last.exists():
                try:
                    payload = json.loads(last.read_text(encoding="utf-8"))
                    if not isinstance(payload, dict) or payload.get("schema") != "UCIE_MINER_CYCLE_V1":
                        raise ValueError("untrusted prior receipt")
                    stamp = payload.get("finished_utc")
                    if not isinstance(stamp, str):
                        raise ValueError("missing completion time")
                    prior = datetime.fromisoformat(stamp.replace("Z", "+00:00"))
                    start_stamp = payload.get("started_utc")
                    if start_stamp is not None:
                        if not isinstance(start_stamp, str):
                            raise ValueError("invalid prior start time")
                        prior_started = datetime.fromisoformat(
                            start_stamp.replace("Z", "+00:00"))
                    failures = payload.get("consecutive_failures", 0)
                except (OSError, ValueError, TypeError, json.JSONDecodeError) as exc:
                    raise ValueError("invalid prior receipt") from exc
            decision = next_cycle(
                prior, now=datetime.now(timezone.utc),
                consecutive_failures=failures, last_started=prior_started)
            if decision["decision"] == "WAIT":
                return {"schema": "UCIE_MINER_CYCLE_V1", "status": "SKIPPED_NOT_DUE",
                        "retry_after_seconds": decision["retry_after_seconds"],
                        "verification_pass": 0, "production_approved": False}
        cycle_clock_ns = perf_counter_ns()
        receipt = {
            "schema": "UCIE_MINER_CYCLE_V1",
            "started_utc": start,
            "status": "COLLECTION_FAILED",
            "new_candidates": 0,
            "sources_checked": 0,
            "verification_pass": 0,
            "production_approved": False,
            "consecutive_failures": 0,
        }
        try:
            collect_clock_ns = perf_counter_ns()
            try:
                result = collect(repo_root)
            finally:
                receipt["collection_elapsed_ms"] = _bounded_elapsed_ms(collect_clock_ns)
            if not isinstance(result, dict) or result.get("status") != "COLLECTED_UNVERIFIED":
                raise ValueError("invalid collector completion status")
            new_count = result.get("new_candidates")
            source_count = result.get("sources_checked")
            if (type(new_count) is not int or not 0 <= new_count <= 10
                    or type(source_count) is not int or not 1 <= source_count <= 2
                    or result.get("verification_pass") != 0
                    or result.get("production_approved") is not False):
                raise ValueError("invalid source statistics")
            optional_stage = result.get("stage10")
            if optional_stage is not None:
                if type(optional_stage) is not dict or optional_stage.get("status") not in (
                        "STAGE10_HOURLY_DISABLED",
                        "STAGE10_UNVERIFIED_STAGED_NO_GO",
                        "STAGE10_HOURLY_PARTIAL_NO_GO",
                        "STAGE10_HOURLY_FAILED_NO_GO"):
                    raise ValueError("invalid optional public stage result")
                receipt["stage10_status"] = optional_stage["status"]
                history_status = optional_stage.get("stage13_history_status")
                if history_status is not None:
                    if history_status not in (
                            "STAGE13_EXTERNAL_HISTORY_DISABLED",
                            "EXTERNAL_HISTORY_BACKFILL_OK_NO_GO",
                            "EXTERNAL_HISTORY_RATE_BUDGET_PAUSED_NO_GO",
                            "EXTERNAL_HISTORY_UPSTREAM_OR_METADATA_FAILED_NO_GO"):
                        raise ValueError("unrecognized public history status")
                    receipt["stage13_history_status"] = history_status
                if optional_stage["status"] == "STAGE10_HOURLY_PARTIAL_NO_GO":
                    if history_status != "EXTERNAL_HISTORY_UPSTREAM_OR_METADATA_FAILED_NO_GO":
                        raise ValueError("partial status must identify Stage 13 failure")
                    from .public_discovery import SOURCES
                    failure_source = optional_stage.get("stage13_failure_source")
                    failure_category = optional_stage.get("stage13_failure_category")
                    if (failure_source not in SOURCES or failure_category not in (
                            "FETCH_OR_RESPONSE_REJECTED",
                            "PUBLIC_METADATA_REJECTED")):
                        raise ValueError("invalid Stage 13 failure identity")
                    receipt["stage13_failure_source"] = failure_source
                    receipt["stage13_failure_category"] = failure_category
                review_status = optional_stage.get("stage12_review_status")
                if review_status is not None:
                    if review_status not in (
                            "STAGE12_REVIEW_DISABLED",
                            "STAGE12_UNVERIFIED_REVIEW_UPDATED_NO_GO"):
                        raise ValueError("invalid Stage 12 review receipt")
                    receipt["stage12_review_status"] = review_status
                    proposals = optional_stage.get("stage12_review_proposals_added", 0)
                    if type(proposals) is not int or not 0 <= proposals <= 10000:
                        raise ValueError("unbounded Stage 12 review counter")
                    receipt["stage12_review_proposals_added"] = proposals
                # Stage16 is observational and unsigned. Only known safe
                # state/counters may be persisted, never a rule approval.
                stage16 = optional_stage.get("stage16_safe_qa_status")
                if stage16 is not None:
                    if stage16 not in {
                            "STAGE16_SAFE_QA_DISABLED",
                            "STAGE16_SAFE_QA_RATE_PAUSED_NO_GO",
                            "STAGE16_SAFE_QA_ALREADY_ATTEMPTED_NO_GO",
                            "STAGE16_SAFE_QA_24H_BUDGET_PAUSED_NO_GO",
                            "STAGE16_SAFE_QA_OBSERVED_REVIEW_REQUIRED",
                            "STAGE16_SAFE_QA_LEDGER_INCOMPLETE_NO_GO",
                            "STAGE16_SAFE_QA_FAILED_NO_GO"}:
                        raise ValueError("invalid Stage16 status")
                    templates = optional_stage.get("stage16_safe_qa_templates", 0)
                    gets = optional_stage.get("stage16_safe_qa_gets_upper_bound", 0)
                    if (type(templates) is not int or not 0 <= templates <= 4
                            or type(gets) is not int or gets not in (0, 9)
                            or (gets == 0 and templates != 0)
                            or (stage16 in (
                                "STAGE16_SAFE_QA_DISABLED",
                                "STAGE16_SAFE_QA_RATE_PAUSED_NO_GO",
                                "STAGE16_SAFE_QA_ALREADY_ATTEMPTED_NO_GO",
                                "STAGE16_SAFE_QA_24H_BUDGET_PAUSED_NO_GO")
                                and gets != 0)):
                        raise ValueError("invalid Stage16 read budget or templates")
                    receipt["stage16_safe_qa_status"] = stage16
                    receipt["stage16_safe_qa_templates"] = templates
                    receipt["stage16_safe_qa_gets_upper_bound"] = gets
                if optional_stage["status"] == "STAGE10_HOURLY_FAILED_NO_GO":
                    # Preserve error CLASS only, never exception text or data
                    # from public sources. No extra file or new observer.
                    error_name = optional_stage.get("error_type")
                    if (type(error_name) is not str or not error_name.isascii()
                            or not 1 <= len(error_name) <= 80
                            or not error_name.isidentifier()):
                        raise ValueError("invalid optional public stage error type")
                    receipt["stage10_error_type"] = error_name
                    # Older synthetic producers may omit the new category.
                    # If present it must be one of our literal safe codes.
                    category = optional_stage.get("error_category")
                    if category is not None:
                        if type(category) is not str or category not in {
                                "UPSTREAM_HTTP_429",
                                "UPSTREAM_HTTP_403",
                                "UPSTREAM_HTTP_OTHER",
                                "UPSTREAM_NETWORK_FAILURE",
                                "UPSTREAM_IO_OR_TIMEOUT",
                                "PUBLIC_JSON_INVALID",
                                "DISCOVERY_VALIDATION_OR_RESPONSE_REJECTED",
                                "OTHER_FAILURE"}:
                            raise ValueError("invalid optional public stage error category")
                        receipt["stage10_error_category"] = category
                    phase = optional_stage.get("error_phase")
                    if phase is not None:
                        from .public_discovery import STAGE10_FAILURE_PHASES
                        if type(phase) is not str or phase not in STAGE10_FAILURE_PHASES:
                            raise ValueError("invalid optional public stage failure phase")
                        receipt["stage10_error_phase"] = phase
            report_clock_ns = perf_counter_ns()
            try:
                path = write_report(repo_root)
            finally:
                receipt["report_elapsed_ms"] = _bounded_elapsed_ms(report_clock_ns)
            report_path = path.resolve(strict=True)
            report_root = (runtime / "reports").resolve(strict=True)
            if not report_path.is_relative_to(report_root):
                raise ValueError("report outside UCIE runtime area")
            receipt.update(
                status="COLLECTED_UNVERIFIED",
                new_candidates=new_count,
                sources_checked=source_count,
                report_path=report_path.relative_to(repo_root.resolve()).as_posix(),
            )
        except Exception as exc:
            # Exceptions can contain externally controlled text: store type ONLY.
            receipt["status"] = "COLLECTION_FAILED"
            receipt["error_type"] = type(exc).__name__
            if enforce_schedule:
                receipt["consecutive_failures"] = min(6, failures + 1)
        finally:
            receipt["cycle_elapsed_ms"] = _bounded_elapsed_ms(cycle_clock_ns)
            receipt["finished_utc"] = _utc()
            _write_receipt(runtime, receipt)
        return receipt
