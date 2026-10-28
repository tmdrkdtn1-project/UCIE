"""UCIE-only durable queue: a blocked job becomes PENDING; other jobs continue.

NO task execution in this module. A 1-minute dispatcher merely leases due
jobs; separate workers may execute one allowlisted first-party operation per
lease. No command strings, source paths, third-party code, scheduler changes,
auto-approval or imports from any other project.

A still-running job is RUNNING, not incorrectly PENDING. Heartbeats extend
its lease. Expired leases retry only after delay and are fenced by opaque
tokens, so stale workers cannot commit success. Actual side effects still
require separately proven idempotent adapters before live activation.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from contextlib import closing
from pathlib import Path
from secrets import token_hex
import argparse
import json
import sqlite3
import tempfile

SCHEMA = "UCIE_INTERNAL_NONBLOCKING_PENDING_QUEUE_V1"
DB_NAME = "ucie_internal_pending_queue_v1.sqlite3"
MAX_ROWS = 1000
MAX_CLAIM = 8
MAX_ATTEMPTS = 5
MIN_RETRY_SECONDS = 60
MAX_RETRY_SECONDS = 3600
MIN_LEASE_SECONDS = 60
MAX_LEASE_SECONDS = 3600
KINDS = frozenset({
    "PUBLIC_METADATA_REVIEW",
    "UCIE_LIBRARY_INDEX_CHECK",
    "UCIE_FIRST_PARTY_EXPERIMENT",
    "UCIE_QA_REVIEW",
    "UCIE_REPORT_PREPARATION",
    # P11 is opt-in and uses separate source/experience store only.
    "PUBLIC_INCREMENTAL_MINING",
    "EXPERIENCE_CLOSED_LOOP",
})
REASONS = frozenset({
    "DEPENDENCY_NOT_READY",
    "UPSTREAM_RATE_LIMIT",
    "WORKER_BUSY",
    "WORKER_TIMEOUT",
    "RETRYABLE_ERROR",
    "LEASE_EXPIRED",
})
STATUSES = ("PENDING", "RUNNING", "SUCCEEDED", "REVIEW_REQUIRED")


class PendingQueueError(ValueError):
    pass


def _now(value: datetime | None = None) -> datetime:
    value = value if value is not None else datetime.now(timezone.utc)
    if not isinstance(value, datetime) or value.tzinfo is None:
        raise PendingQueueError("UTC-aware clock required")
    if value.utcoffset() != timedelta(0):
        raise PendingQueueError("UTC offset must be zero")
    return value


def _stamp(value: datetime) -> str:
    return _now(value).isoformat(timespec="microseconds")


def _parse(stamp: str) -> datetime:
    if type(stamp) is not str:
        raise PendingQueueError("invalid due-time")
    value = datetime.fromisoformat(stamp.replace("Z", "+00:00"))
    return _now(value)


def _root(root: Path) -> Path:
    if (not isinstance(root, Path) or root.is_symlink()
            or root.name.casefold() != "ucie" or not root.is_dir()):
        raise PendingQueueError("dedicated UCIE root required")
    runtime = root / "runtime"
    if not runtime.is_dir() or runtime.is_symlink():
        raise PendingQueueError("existing isolated UCIE runtime required")
    target = runtime / DB_NAME
    if target.is_symlink() or (target.exists() and not target.is_file()):
        raise PendingQueueError("unsafe queue database")
    return target


def _conn(root: Path, *, create: bool = False) -> sqlite3.Connection:
    path = _root(root)
    if not path.exists() and not create:
        raise PendingQueueError("queue not initialized (no changes performed)")
    # All code that opens the queue is limited to an existing dedicated UCIE
    # runtime. This file is never the operating PublicMiner SQLite database.
    database = sqlite3.connect(str(path), timeout=0.25, isolation_level=None)
    database.row_factory = sqlite3.Row
    database.execute("PRAGMA busy_timeout=250")
    database.execute("PRAGMA journal_mode=WAL")
    return database


def initialize_queue(root: Path) -> dict:
    """Explicit opt-in. Never installs Windows Scheduled Tasks or workers."""
    with closing(_conn(root, create=True)) as db:
        db.executescript("""
        CREATE TABLE IF NOT EXISTS jobs (
            job_id INTEGER PRIMARY KEY,
            dedupe_key TEXT NOT NULL UNIQUE,
            kind TEXT NOT NULL,
            status TEXT NOT NULL CHECK(status IN
                ('PENDING','RUNNING','SUCCEEDED','REVIEW_REQUIRED')),
            due_at TEXT NOT NULL,
            attempts INTEGER NOT NULL DEFAULT 0,
            max_attempts INTEGER NOT NULL,
            lease_token TEXT,
            lease_expires_at TEXT,
            last_reason TEXT,
            completed_at TEXT,
            CHECK(attempts BETWEEN 0 AND max_attempts)
        );
        CREATE INDEX IF NOT EXISTS jobs_schedule
            ON jobs(status, due_at, job_id);
        """)
    return {
        "schema": SCHEMA, "status": "QUEUE_READY_EXPLICIT_OPT_IN",
        "database": "runtime/" + DB_NAME,
        "windows_tasks_registered": 0,
        "existing_hourly_miner_changed": False,
        "production_handlers_enabled": False,
        "auto_promoted": False,
    }


def _valid_key(dedupe_key: str) -> bool:
    if type(dedupe_key) is not str or not 1 <= len(dedupe_key) <= 96:
        return False
    allowed = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_.:-"
    return all(ch in allowed for ch in dedupe_key)


def enqueue(root: Path, *, kind: str, dedupe_key: str,
            due: datetime | None = None, max_attempts: int = 5) -> dict:
    if (type(kind) is not str or kind not in KINDS or not _valid_key(dedupe_key)
            or type(max_attempts) is not int
            or not 1 <= max_attempts <= MAX_ATTEMPTS):
        raise PendingQueueError("only bounded first-party job metadata allowed")
    due_at = _stamp(_now(due))
    with closing(_conn(root)) as db:
        db.execute("BEGIN IMMEDIATE")
        count = db.execute("SELECT COUNT(*) FROM jobs").fetchone()[0]
        prior = db.execute(
            "SELECT job_id, kind, status FROM jobs WHERE dedupe_key=?",
            (dedupe_key,)).fetchone()
        if prior:
            if prior["kind"] != kind:
                db.execute("ROLLBACK")
                raise PendingQueueError("dedupe key cannot switch job kind")
            db.execute("COMMIT")
            return {
                "schema": SCHEMA, "status": "DUPLICATE_NOT_ENQUEUED",
                "job_id": prior["job_id"], "job_status": prior["status"],
                "new_rows": 0, "auto_promoted": False,
            }
        if count >= MAX_ROWS:
            db.execute("ROLLBACK")
            raise PendingQueueError("bounded UCIE queue full")
        cursor = db.execute(
            "INSERT INTO jobs(dedupe_key,kind,status,due_at,max_attempts)"
            " VALUES(?,?,'PENDING',?,?)",
            (dedupe_key, kind, due_at, max_attempts))
        db.execute("COMMIT")
    return {
        "schema": SCHEMA, "status": "ENQUEUED_PENDING",
        "job_id": cursor.lastrowid, "new_rows": 1,
        "auto_promoted": False,
    }


def _retry_delay(attempts: int) -> int:
    return min(MAX_RETRY_SECONDS, MIN_RETRY_SECONDS * (2 ** max(0, attempts - 1)))


def _reclaim_stale(db: sqlite3.Connection, now: datetime) -> tuple[int, int]:
    rows = db.execute(
        "SELECT job_id, attempts, max_attempts FROM jobs "
        "WHERE status='RUNNING' AND lease_expires_at<=? ORDER BY job_id",
        (_stamp(now),)).fetchall()
    repending = dead = 0
    for row in rows:
        if row["attempts"] >= row["max_attempts"]:
            db.execute(
                "UPDATE jobs SET status='REVIEW_REQUIRED',last_reason=?,"
                "lease_token=NULL,lease_expires_at=NULL WHERE job_id=?",
                ("LEASE_EXPIRED", row["job_id"]))
            dead += 1
        else:
            delay = _retry_delay(row["attempts"])
            db.execute(
                "UPDATE jobs SET status='PENDING',last_reason=?,due_at=?,"
                "lease_token=NULL,lease_expires_at=NULL WHERE job_id=?",
                ("LEASE_EXPIRED", _stamp(now + timedelta(seconds=delay)),
                 row["job_id"]))
            repending += 1
    return repending, dead


def claim_ready(root: Path, *, now: datetime | None = None,
                limit: int = 4, lease_seconds: int = 120) -> dict:
    """One SHORT transaction. It never runs a job or waits for a worker.

    If job A is RUNNING (healthy or expired), job B can be claimed on the same
    tick. Expired A becomes PENDING with delay or REVIEW_REQUIRED, and old
    tokens are fenced. Actual work happens in independently managed workers.
    """
    current = _now(now)
    if (type(limit) is not int or not 1 <= limit <= MAX_CLAIM
            or type(lease_seconds) is not int
            or not MIN_LEASE_SECONDS <= lease_seconds <= MAX_LEASE_SECONDS):
        raise PendingQueueError("bounded dispatch/lease required")
    claimed = []
    with closing(_conn(root)) as db:
        db.execute("BEGIN IMMEDIATE")
        repending, needs_review = _reclaim_stale(db, current)
        rows = db.execute(
            "SELECT job_id,dedupe_key,kind,attempts,max_attempts "
            "FROM jobs WHERE status='PENDING' AND due_at<=? "
            "ORDER BY due_at,job_id LIMIT ?",
            (_stamp(current), limit)).fetchall()
        for row in rows:
            token = token_hex(16)
            lease_until = _stamp(current + timedelta(seconds=lease_seconds))
            attempt = row["attempts"] + 1
            db.execute(
                "UPDATE jobs SET status='RUNNING',attempts=?,"
                "lease_token=?,lease_expires_at=?,last_reason=NULL "
                "WHERE job_id=? AND status='PENDING'",
                (attempt, token, lease_until, row["job_id"]))
            claimed.append({
                "job_id": row["job_id"], "kind": row["kind"],
                "dedupe_key": row["dedupe_key"], "attempt": attempt,
                "lease_token": token, "lease_expires_at": lease_until,
            })
        db.execute("COMMIT")
    return {
        "schema": SCHEMA,
        "status": "NONBLOCKING_DISPATCH_FINISHED",
        "claimed_count": len(claimed), "claimed": claimed,
        "stale_requeued_count": repending,
        "stale_review_required_count": needs_review,
        "waited_for_running_tasks": False,
        "job_handlers_executed": 0,
        "external_api_requests": 0,
        "existing_hourly_miner_changed": False,
        "auto_promoted": False,
    }


def _leased(db: sqlite3.Connection, job_id: int, lease_token: str,
            current: datetime) -> sqlite3.Row:
    if (type(job_id) is not int or job_id < 1
            or type(lease_token) is not str or len(lease_token) != 32
            or any(x not in "0123456789abcdef" for x in lease_token)):
        raise PendingQueueError("invalid worker lease identity")
    row = db.execute(
        "SELECT * FROM jobs WHERE job_id=?", (job_id,)).fetchone()
    if (row is None or row["status"] != "RUNNING"
            or row["lease_token"] != lease_token
            or _parse(row["lease_expires_at"]) <= current):
        raise PendingQueueError("stale or invalid worker lease: refuse completion")
    return row


def heartbeat(root: Path, *, job_id: int, lease_token: str,
              now: datetime | None = None, extension_seconds: int = 120) -> dict:
    """A legitimately long-running worker remains RUNNING, not PENDING."""
    current = _now(now)
    if (type(extension_seconds) is not int
            or not MIN_LEASE_SECONDS <= extension_seconds <= MAX_LEASE_SECONDS):
        raise PendingQueueError("bounded heartbeat extension required")
    with closing(_conn(root)) as db:
        db.execute("BEGIN IMMEDIATE")
        row = _leased(db, job_id, lease_token, current)
        until = max(
            _parse(row["lease_expires_at"]),
            current + timedelta(seconds=extension_seconds))
        db.execute(
            "UPDATE jobs SET lease_expires_at=? WHERE job_id=?",
            (_stamp(until), job_id))
        db.execute("COMMIT")
    return {
        "schema": SCHEMA, "status": "LEASE_RENEWED_RUNNING",
        "job_id": job_id, "lease_expires_at": _stamp(until),
        "other_jobs_blocked": False,
    }


def finish_job(root: Path, *, job_id: int, lease_token: str,
               outcome: str, now: datetime | None = None,
               reason: str | None = None,
               retry_after_seconds: int | None = None) -> dict:
    """A worker reports success or a bounded PENDING retry, never auto-approves."""
    current = _now(now)
    if outcome not in ("SUCCEEDED", "BLOCKED"):
        raise PendingQueueError("unsupported worker outcome")
    if outcome == "BLOCKED":
        if type(reason) is not str or reason not in REASONS:
            raise PendingQueueError("sanitized blocker code required")
        if (retry_after_seconds is not None and
                (type(retry_after_seconds) is not int
                 or not MIN_RETRY_SECONDS <= retry_after_seconds <= MAX_RETRY_SECONDS)):
            raise PendingQueueError("bounded retry interval required")
    elif reason is not None or retry_after_seconds is not None:
        raise PendingQueueError("success must not contain failure data")
    with closing(_conn(root)) as db:
        db.execute("BEGIN IMMEDIATE")
        row = _leased(db, job_id, lease_token, current)
        if outcome == "SUCCEEDED":
            new_status, due_at, why = "SUCCEEDED", row["due_at"], None
        elif row["attempts"] >= row["max_attempts"]:
            new_status, due_at, why = "REVIEW_REQUIRED", row["due_at"], reason
        else:
            delay = max(_retry_delay(row["attempts"]),
                        retry_after_seconds or MIN_RETRY_SECONDS)
            new_status = "PENDING"
            due_at = _stamp(current + timedelta(seconds=delay))
            why = reason
        db.execute(
            "UPDATE jobs SET status=?, due_at=?, last_reason=?,"
            "lease_token=NULL,lease_expires_at=NULL,completed_at=? WHERE job_id=?",
            (new_status, due_at, why,
             _stamp(current) if new_status == "SUCCEEDED" else None, job_id))
        db.execute("COMMIT")
    return {
        "schema": SCHEMA, "status": new_status,
        "job_id": job_id, "next_due_at": due_at if new_status == "PENDING" else None,
        "reason": why,
        "next_job_can_proceed": True,
        "auto_promoted": False,
    }


def inspect_queue(root: Path, *, limit: int = 20) -> dict:
    """Metadata only. Never returns lease tokens, code or private payloads."""
    if type(limit) is not int or not 1 <= limit <= 100:
        raise PendingQueueError("bounded queue status page required")
    path = _root(root)
    if not path.exists():
        return {
            "schema": SCHEMA, "status": "QUEUE_NOT_INSTALLED_READ_ONLY",
            "counts": {x: 0 for x in STATUSES},
            "jobs": [], "schedulers_changed": False,
        }
    # Read-only open does not change operating SQLite or create queue.
    with closing(sqlite3.connect(f"file:{path.as_posix()}?mode=ro", uri=True,
                                 timeout=0.25)) as db:
        db.row_factory = sqlite3.Row
        counts = {r["status"]: r["n"] for r in db.execute(
            "SELECT status,COUNT(*) AS n FROM jobs GROUP BY status")}
        details = db.execute(
            "SELECT job_id,kind,status,attempts,max_attempts,due_at,last_reason "
            "FROM jobs ORDER BY job_id LIMIT ?", (limit,)).fetchall()
    return {
        "schema": SCHEMA, "status": "READ_ONLY_PENDING_QUEUE_SNAPSHOT",
        "counts": {x: counts.get(x, 0) for x in STATUSES},
        "jobs": [dict(row) for row in details],
        "lease_tokens_exported": 0, "network_requests": 0,
        "existing_hourly_miner_changed": False,
        "auto_promoted": False,
    }


def demo_pending_no_head_of_line_block() -> dict:
    """Actual queue algorithm exercise in an isolated synthetic temp UCIE."""
    with tempfile.TemporaryDirectory() as base:
        root = Path(base) / "UCIE"
        (root / "runtime").mkdir(parents=True)
        initialize_queue(root)
        start = datetime(2026, 10, 28, tzinfo=timezone.utc)
        a = enqueue(root, kind="PUBLIC_METADATA_REVIEW",
                    dedupe_key="UCIE:DEMO:A", due=start)
        b = enqueue(root, kind="UCIE_LIBRARY_INDEX_CHECK",
                    dedupe_key="UCIE:DEMO:B", due=start)
        first = claim_ready(root, now=start, limit=1)
        blocked = finish_job(root, job_id=a["job_id"],
                             lease_token=first["claimed"][0]["lease_token"],
                             outcome="BLOCKED", reason="DEPENDENCY_NOT_READY",
                             now=start + timedelta(seconds=1))
        second = claim_ready(root, now=start + timedelta(seconds=2), limit=1)
        independent = second["claimed"][0]["job_id"] == b["job_id"]
        done = finish_job(root, job_id=b["job_id"],
                          lease_token=second["claimed"][0]["lease_token"],
                          outcome="SUCCEEDED", now=start + timedelta(seconds=3))
        state = inspect_queue(root)
        ok = (blocked["status"] == "PENDING" and independent
              and done["status"] == "SUCCEEDED"
              and state["counts"]["PENDING"] == 1
              and state["counts"]["SUCCEEDED"] == 1)
        return {
            "schema": SCHEMA,
            "status": "NONBLOCKING_PENDING_DEMO_PASS" if ok
                      else "NONBLOCKING_PENDING_DEMO_FAIL",
            "blocked_job_status": blocked["status"],
            "independent_job_status": done["status"],
            "other_job_proceeded_in_same_minute": independent,
            "next_due_at": blocked["next_due_at"],
            "simulation_only": True,
            "production_worker_connected": False,
            "windows_task_registered": False,
            "operating_database_writes": 0,
            "auto_promoted": False,
        }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="UCIE-only nonblocking task queue: read-only status or safe synthetic demo")
    parser.add_argument("--ucie-root", type=Path)
    parser.add_argument("--demo", action="store_true")
    args = parser.parse_args()
    try:
        if args.demo and args.ucie_root is None:
            data = demo_pending_no_head_of_line_block()
        elif args.ucie_root is not None and not args.demo:
            data = inspect_queue(args.ucie_root)
        else:
            raise PendingQueueError("choose synthetic demo or read-only UCIE queue snapshot")
    except (PendingQueueError, OSError, sqlite3.Error, ValueError) as exc:
        print(json.dumps({"schema": SCHEMA, "status": "QUEUE_FAIL_CLOSED",
                          "error_type": type(exc).__name__,
                          "windows_task_registered": False}, sort_keys=True))
        return 2
    print(json.dumps(data, sort_keys=True))
    return 0 if data["status"] != "NONBLOCKING_PENDING_DEMO_FAIL" else 3


if __name__ == "__main__":
    raise SystemExit(main())
