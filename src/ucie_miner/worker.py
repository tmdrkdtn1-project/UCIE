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
from typing import Callable, Iterator

from .core import mine_once, report
from .schedule_policy import next_cycle


def _utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


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
            result = collect(repo_root)
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
                        "STAGE10_HOURLY_FAILED_NO_GO"):
                    raise ValueError("invalid optional public stage result")
                receipt["stage10_status"] = optional_stage["status"]
                if optional_stage["status"] == "STAGE10_HOURLY_FAILED_NO_GO":
                    # Preserve error CLASS only, never exception text or data
                    # from public sources. No extra file or new observer.
                    error_name = optional_stage.get("error_type")
                    if (type(error_name) is not str or not error_name.isascii()
                            or not 1 <= len(error_name) <= 80
                            or not error_name.isidentifier()):
                        raise ValueError("invalid optional public stage error type")
                    receipt["stage10_error_type"] = error_name
            path = write_report(repo_root)
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
            receipt["finished_utc"] = _utc()
            _write_receipt(runtime, receipt)
        return receipt
