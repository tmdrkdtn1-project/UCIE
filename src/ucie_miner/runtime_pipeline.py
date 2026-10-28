"""P10 UCIE-only 1-minute nonblocking dispatcher with independent workers.

A tick claims and SPAWNS at most three separate worker supervisors, then
returns immediately. A supervisor runs one approved read-only UCIE handler in
a bounded child process, periodically heartbeats and fences timed-out/stale
results. One blocked job changes only its own row to PENDING with backoff.
No outbound public API GET, model training, new signature, rule promotion,
project code access, arbitrary command, or mutation of the existing miner.

No Windows task or queue is registered/initialized by import or --tick.
--initialize is explicit; Windows installer separately requires -Install.
"""
from __future__ import annotations

import argparse
from contextlib import contextmanager, closing
from datetime import datetime, timedelta, timezone
import errno
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
from time import monotonic

from . import pending_queue as queue

SCHEMA = "UCIE_P10_INDEPENDENT_NONBLOCKING_DISPATCH_V1"
TASK_NAME = "UCIE-Internal-Minute"
MAX_ACTIVE = 3
MAX_NEW_PER_TICK = 3
WORKER_LEASE_SECONDS = 120
WORKER_BUDGET_SECONDS = 180
HEARTBEAT_SECONDS = 15
KIND_INTERVALS_MINUTES = (
    ("UCIE_LIBRARY_INDEX_CHECK", 1),
    ("PUBLIC_METADATA_REVIEW", 5),
    ("UCIE_QA_REVIEW", 5),
    ("UCIE_FIRST_PARTY_EXPERIMENT", 15),
    ("UCIE_REPORT_PREPARATION", 60),
)
PERIODS = dict(KIND_INTERVALS_MINUTES)
DEDUPES = {kind: "UCIE:P10:" + kind for kind in PERIODS}
MAX_REARM_HISTORY = 10000
# No catch-all actions, user strings or program-supplied shell commands.
CHILD_ARGS = ("-B", "-m", "ucie_miner.runtime_pipeline")


class RuntimePipelineError(ValueError):
    pass


def _ensure(root: Path) -> Path:
    p = queue._root(root)
    if not p.exists():
        raise RuntimePipelineError("queue not initialized; explicit --initialize required")
    return p


@contextmanager
def _tick_lock(root: Path):
    """Process-level lock; tick A can't race tick B into claiming excess jobs."""
    directory = _ensure(root).parent
    lock = directory / "ucie_internal_minute_dispatch.lock"
    if lock.is_symlink():
        raise RuntimePipelineError("unsafe dispatcher lock")
    with lock.open("a+b") as handle:
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
            if isinstance(exc, BlockingIOError) or exc.errno in (
                    errno.EACCES, errno.EAGAIN):
                yield False
                return
            raise
        try:
            yield True
        finally:
            handle.seek(0)
            if os.name == "nt":
                import msvcrt
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def initialize(root: Path) -> dict:
    """Explicit, bounded local queue plus a separate schema for run receipts."""
    queue.initialize_queue(root)
    with closing(queue._conn(root)) as db:
        db.execute("""CREATE TABLE IF NOT EXISTS p10_completed (
            event_id INTEGER PRIMARY KEY,
            kind TEXT NOT NULL,
            job_id INTEGER NOT NULL,
            finished_at TEXT NOT NULL,
            final_status TEXT NOT NULL CHECK(
                final_status IN ('SUCCEEDED','REVIEW_REQUIRED'))
        )""")
        db.execute("CREATE INDEX IF NOT EXISTS p10_completed_by_kind "
                   "ON p10_completed(kind,finished_at)")
    return {
        "schema": SCHEMA, "status": "P10_QUEUE_INITIALIZED_NO_TASK_REGISTERED",
        "separate_ucie_queue": "runtime/" + queue.DB_NAME,
        "task_registered": False, "public_miner_task_modified": False,
        "production_handlers_first_party_read_only": True,
        "public_api_gets": 0, "auto_promoted": False,
    }


def _schedule(root: Path, *, now: datetime) -> dict:
    """Stable 5 job rows; success rearm logged before overwrite, no row growth."""
    due = queue._stamp(queue._now(now))
    history_added = 0
    rearmed = 0
    with closing(queue._conn(root)) as db:
        db.execute("BEGIN IMMEDIATE")
        recorded = db.execute("SELECT COUNT(*) FROM p10_completed").fetchone()[0]
        rows = db.execute(
            "SELECT job_id,dedupe_key,kind,status,completed_at FROM jobs "
            "WHERE dedupe_key LIKE 'UCIE:P10:%'").fetchall()
        known = {}
        for row in rows:
            if row["kind"] not in PERIODS or row["dedupe_key"] != DEDUPES[row["kind"]]:
                raise RuntimePipelineError("unsafe P10 source job identity")
            known[row["kind"]] = row
        for kind, minutes in KIND_INTERVALS_MINUTES:
            row = known.get(kind)
            if row is not None and row["status"] == "SUCCEEDED":
                completed = queue._parse(row["completed_at"])
                if completed + timedelta(minutes=minutes) <= now:
                    if recorded + history_added >= MAX_REARM_HISTORY:
                        raise RuntimePipelineError("P10 bounded history needs review")
                    db.execute(
                        "INSERT INTO p10_completed(kind,job_id,finished_at,final_status)"
                        " VALUES(?,?,?,'SUCCEEDED')",
                        (kind, row["job_id"], row["completed_at"]))
                    history_added += 1
                    db.execute(
                        "UPDATE jobs SET status='PENDING', due_at=?, attempts=0,"
                        "lease_token=NULL,lease_expires_at=NULL,"
                        "last_reason=NULL,completed_at=NULL WHERE job_id=? AND status='SUCCEEDED'",
                        (due, row["job_id"]))
                    rearmed += 1
            elif row is not None and row["status"] == "REVIEW_REQUIRED":
                # Never silently reset a permanently failing job.
                continue
        db.execute("COMMIT")
    new_rows = 0
    for kind, _interval in KIND_INTERVALS_MINUTES:
        if kind not in known:
            result = queue.enqueue(
                root, kind=kind, dedupe_key=DEDUPES[kind], due=now)
            new_rows += result["new_rows"]
    return {
        "new_jobs": new_rows, "rearmed_successful_jobs": rearmed,
        "completed_history_appended": history_added,
    }


def _running_count(root: Path) -> int:
    with closing(queue._conn(root)) as db:
        return db.execute(
            "SELECT COUNT(*) FROM jobs WHERE status='RUNNING'").fetchone()[0]


def _spawn(root: Path, claimed: dict) -> None:
    """Launch one supervisor process, never a shell or arbitrary callable."""
    cmd = [
        sys.executable, *CHILD_ARGS, "--worker",
        "--ucie-root", str(root),
        "--job-id", str(claimed["job_id"]),
        "--lease-token", claimed["lease_token"],
    ]
    subprocess.Popen(
        cmd, cwd=str(root), stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        close_fds=True, env={**os.environ, "PYTHONPATH": str(root / "src")})


def _expire_without_claim(root: Path, *, now: datetime) -> tuple[int, int]:
    """Reclaim stale leases even when all real worker slots were occupied."""
    with closing(queue._conn(root)) as db:
        db.execute("BEGIN IMMEDIATE")
        counts = queue._reclaim_stale(db, now)
        db.execute("COMMIT")
    return counts


def dispatch_tick(root: Path, *, now: datetime | None = None,
                  spawn=None) -> dict:
    """Return promptly; no wait for A, B, C, HTTP, P8 or source scanning."""
    root = Path(root)
    current = queue._now(now)
    _ensure(root)
    launched = errors = 0
    with _tick_lock(root) as acquired:
        if not acquired:
            return {
                "schema": SCHEMA, "status": "DISPATCH_TICK_ALREADY_ACTIVE_SKIP",
                "workers_launched": 0, "no_overlap": True,
                "scheduler_modified": False, "operating_db_writes": 0,
            }
        scheduled = _schedule(root, now=current)
        reclaimed, review = _expire_without_claim(root, now=current)
        active = _running_count(root)
        free = max(0, MAX_ACTIVE - active)
        if free:
            claims = queue.claim_ready(
                root, now=current, limit=min(MAX_NEW_PER_TICK, free),
                lease_seconds=WORKER_LEASE_SECONDS)
        else:
            claims = {
                "claimed": [], "stale_requeued_count": 0,
                "stale_review_required_count": 0,
            }
        for leased in claims["claimed"]:
            try:
                (spawn or _spawn)(root, leased)
                launched += 1
            except (OSError, ValueError, RuntimeError):
                errors += 1
                queue.finish_job(
                    root, job_id=leased["job_id"],
                    lease_token=leased["lease_token"], outcome="BLOCKED",
                    reason="RETRYABLE_ERROR", now=current)
    return {
        "schema": SCHEMA, "status": "P10_NONBLOCKING_TICK_DISPATCHED",
        **scheduled,
        "workers_launched": launched, "launch_failures_pending": errors,
        "running_before": active, "max_concurrent": MAX_ACTIVE,
        "expired_worker_jobs_requeued": reclaimed + claims["stale_requeued_count"],
        "expired_worker_jobs_review_required": review + claims["stale_review_required_count"],
        "jobs_executed_in_dispatcher": 0,
        "waited_for_running_jobs": False,
        "public_api_gets_in_dispatcher": 0,
        "existing_public_miner_modified": False,
        "scheduler_modified": False, "auto_promoted": False,
    }


def _safe_handler(root: Path, kind: str) -> bool:
    """Strict read-only first-party work, no public GET or dataset training."""
    if kind not in PERIODS:
        raise RuntimePipelineError("unauthorized task kind")
    if kind == "PUBLIC_METADATA_REVIEW":
        from .library_search import search_existing_public_library
        out = search_existing_public_library(
            root, query="", limit=1, group_revisions=True)
        return out["status"] == "READ_ONLY_UNVERIFIED_LIBRARY_SEARCH_NO_GO"
    if kind == "UCIE_LIBRARY_INDEX_CHECK":
        from .library_shelves import search_official_metadata_shelf
        out = search_official_metadata_shelf(root, limit=1)
        return out["status"] == "STAGE14_OFFICIAL_METADATA_READ_ONLY_UNVERIFIED_NO_GO"
    if kind == "UCIE_FIRST_PARTY_EXPERIMENT":
        from .capability_trials import evaluate_ucie_owned_recipe
        out = evaluate_ucie_owned_recipe(
            "ENGINE_INCREMENTAL_BUILD", rows=128, queries=24, repeats=1)
        return (out["exact_result_equivalence_observed"] is True
                and out["mismatched_queries_across_repetitions"] == 0)
    if kind == "UCIE_QA_REVIEW":
        from .product_v1 import portable_consumer_check
        out = portable_consumer_check()
        return out["all_queries_equivalent"] is True
    if kind == "UCIE_REPORT_PREPARATION":
        from .product_v1 import integrated_product_preview
        out = integrated_product_preview(root, query="", limit=1)
        return (out["schema"] == "UCIE_P9_PRODUCT_INTEGRATION_PREVIEW_V1"
                and out["v1_accepted"] is False
                and out["operating_database_writes"] == 0)
    raise RuntimePipelineError("unhandled task kind")


def _worker(root: Path, job_id: int, token: str) -> dict:
    """Supervisor fences completion and terminates an over-budget child."""
    root = Path(root)
    _ensure(root)
    with closing(queue._conn(root)) as db:
        row = db.execute(
            "SELECT kind FROM jobs WHERE job_id=? AND status='RUNNING' "
            "AND lease_token=?", (job_id, token)).fetchone()
    if row is None or row["kind"] not in PERIODS:
        raise RuntimePipelineError("unauthorized or stale worker")
    kind = row["kind"]
    # One fixed first-party handler. No shell, untrusted command, raw PR code.
    cmd = [sys.executable, *CHILD_ARGS, "--execute", "--ucie-root",
           str(root), "--kind", kind]
    process = subprocess.Popen(
        cmd, cwd=str(root), stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        close_fds=True, env={**os.environ, "PYTHONPATH": str(root / "src")})
    started = monotonic()
    timed_out = False
    try:
        while process.poll() is None:
            left = WORKER_BUDGET_SECONDS - (monotonic() - started)
            if left <= 0:
                timed_out = True
                break
            try:
                process.wait(timeout=min(HEARTBEAT_SECONDS, left))
            except subprocess.TimeoutExpired:
                # The child is still working, but the other independent
                # worker slots remain available.
                try:
                    queue.heartbeat(
                        root, job_id=job_id, lease_token=token,
                        extension_seconds=WORKER_LEASE_SECONDS)
                except queue.PendingQueueError:
                    # Another dispatcher has fenced this lease; do not commit
                    # a late outcome. Terminate the orphan child.
                    timed_out = True
                    break
    finally:
        if process.poll() is None:
            process.kill()
            process.wait(timeout=10)
    success = (not timed_out and process.returncode == 0)
    outcome = queue.finish_job(
        root, job_id=job_id, lease_token=token,
        outcome="SUCCEEDED" if success else "BLOCKED",
        reason=None if success else
            ("WORKER_TIMEOUT" if timed_out else "RETRYABLE_ERROR"))
    return {
        "schema": SCHEMA, "status": outcome["status"],
        "job_id": job_id, "kind": kind,
        "child_timed_out": timed_out,
        "other_jobs_blocked": False,
        "operating_db_writes": 0, "auto_promoted": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="UCIE P10 independent worker runtime")
    parser.add_argument("--ucie-root", required=True, type=Path)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--initialize", action="store_true")
    mode.add_argument("--tick", action="store_true")
    mode.add_argument("--worker", action="store_true")
    mode.add_argument("--execute", action="store_true")
    parser.add_argument("--job-id", type=int)
    parser.add_argument("--lease-token")
    parser.add_argument("--kind", choices=sorted(PERIODS))
    args = parser.parse_args()
    try:
        if args.initialize:
            if args.job_id or args.lease_token or args.kind:
                raise RuntimePipelineError("invalid initialize options")
            out = initialize(args.ucie_root)
        elif args.tick:
            if args.job_id or args.lease_token or args.kind:
                raise RuntimePipelineError("invalid tick options")
            out = dispatch_tick(args.ucie_root)
        elif args.worker:
            if args.job_id is None or args.lease_token is None or args.kind:
                raise RuntimePipelineError("worker requires only job lease")
            out = _worker(args.ucie_root, args.job_id, args.lease_token)
        else:
            if args.kind is None or args.job_id or args.lease_token:
                raise RuntimePipelineError("execute requires only approved kind")
            out = {
                "schema": SCHEMA,
                "status": ("HANDLER_READ_ONLY_SUCCESS" if
                           _safe_handler(args.ucie_root, args.kind) else
                           "HANDLER_DEPENDENCY_NOT_READY"),
                "kind": args.kind, "network_requests": 0,
                "operating_db_writes": 0, "auto_promoted": False,
            }
    except (RuntimePipelineError, queue.PendingQueueError,
            sqlite3.Error, OSError, ValueError) as exc:
        print(json.dumps({
            "schema": SCHEMA, "status": "P10_FAIL_CLOSED",
            "error_type": type(exc).__name__, "auto_promoted": False,
            "existing_public_miner_modified": False,
        }, sort_keys=True))
        return 2
    print(json.dumps(out, sort_keys=True))
    return 0 if out["status"] not in ("HANDLER_DEPENDENCY_NOT_READY",) else 2


if __name__ == "__main__":
    raise SystemExit(main())
