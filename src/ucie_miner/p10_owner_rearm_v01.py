"""UCIE P10 single-job owner recovery core. No live apply launcher is exposed.

Preview reads only the isolated UCIE queue. Two first-party no-network kinds
are supported; P11 public collection is NEVER rearmed here. The mutating
functions are for isolated synthetic QA until a separately verified Windows
owner/task/event preflight and explicit authorization exist. Never auto-run.
"""
from __future__ import annotations

import argparse
from contextlib import closing
from datetime import datetime, timedelta, timezone
from hashlib import sha256
import json
from pathlib import Path
import os
import sqlite3
import tempfile

from . import pending_queue as queue
from .runtime_pipeline import DEDUPES

SCHEMA = "UCIE_P10_OWNER_ONE_JOB_REARM_V01"
TABLE = "p10_owner_one_rearm_receipts_v01"
SAFE_KINDS = frozenset(("PUBLIC_METADATA_REVIEW", "UCIE_REPORT_PREPARATION"))
COOLDOWN = timedelta(minutes=10)
COLUMNS = ("job_id", "dedupe_key", "kind", "status", "due_at", "attempts",
           "max_attempts", "lease_token", "lease_expires_at",
           "last_reason", "completed_at")


class OwnerRearmError(ValueError):
    pass


# There is no live owner launcher yet. Fail closed even when a caller sets
# both Boolean flags to True: they are not owner identity/task attestations.
SYNTH_MARKER = "UCIE_P10_REARM_SYNTH_ONLY_V1"


def _require_synthetic_root(root: Path) -> None:
    if not isinstance(root, Path) or root.is_symlink():
        raise OwnerRearmError("synthetic UCIE root required")
    resolved = root.resolve()
    if (resolved == Path("D:/UCIE").resolve()
            or resolved.name.casefold() != "ucie"
            or not resolved.is_relative_to(Path(tempfile.gettempdir()).resolve())):
        raise OwnerRearmError("operating UCIE recovery is not enabled")
    marker = resolved / "runtime" / "UCIE_P10_REARM_SYNTH_ONLY.marker"
    if (marker.is_symlink() or not marker.is_file()
            or marker.stat().st_size != len(SYNTH_MARKER)
            or marker.read_text(encoding="ascii") != SYNTH_MARKER):
        raise OwnerRearmError("disposable synthetic marker required")


def _clock(now):
    now = datetime.now(timezone.utc) if now is None else now
    if (not isinstance(now, datetime) or now.tzinfo is None
            or now.utcoffset() != timedelta(0)):
        raise OwnerRearmError("UTC-aware clock required")
    return now


def _conn(root, *, readonly):
    if not isinstance(root, Path):
        raise OwnerRearmError("dedicated UCIE Path required")
    path = queue._root(root)
    if not path.is_file() or path.is_symlink():
        raise OwnerRearmError("existing exact UCIE queue required")
    if readonly:
        db = sqlite3.connect(path.as_uri() + "?mode=ro", uri=True,
                             timeout=0.5, isolation_level=None)
        db.execute("PRAGMA query_only=ON")
    else:
        db = sqlite3.connect(str(path), timeout=0.5, isolation_level=None)
    db.row_factory = sqlite3.Row
    return db


def _row(db, kind):
    if type(kind) is not str or kind not in SAFE_KINDS:
        raise OwnerRearmError("unapproved kind, including P11 network kind")
    row = db.execute(
        "SELECT " + ",".join(COLUMNS) + " FROM jobs WHERE dedupe_key=?",
        (DEDUPES[kind],)).fetchone()
    if row is None or row["kind"] != kind or row["job_id"] < 1:
        raise OwnerRearmError("missing exact existing UCIE job")
    return row


def _fp(row):
    # Lease metadata affects the digest but is never exposed as text.
    return sha256(json.dumps(
        {column: row[column] for column in COLUMNS}, sort_keys=True,
        separators=(",", ":"), ensure_ascii=True).encode("ascii")).hexdigest()


def _held(row):
    return (row["status"] == "REVIEW_REQUIRED"
            and type(row["attempts"]) is int
            and row["attempts"] == row["max_attempts"] == queue.MAX_ATTEMPTS
            and row["last_reason"] == "RETRYABLE_ERROR"
            and row["lease_token"] is None
            and row["lease_expires_at"] is None
            and row["completed_at"] is None)


def _running(db):
    return db.execute(
        "SELECT COUNT(*) FROM jobs WHERE status='RUNNING'").fetchone()[0]


def _active(db):
    found = db.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
        (TABLE,)).fetchone()
    if found is None:
        return 0
    return db.execute(
        "SELECT COUNT(*) FROM " + TABLE + " WHERE state='ACTIVE'"
    ).fetchone()[0]


def preview(root: Path, *, kind: str) -> dict:
    """Read-only owner preflight; never grants approval or invokes a worker."""
    with closing(_conn(root, readonly=True)) as db:
        row = _row(db, kind)
        held, running, active = _held(row), _running(db), _active(db)
        return {
            "schema": SCHEMA, "status": "OWNER_REARM_REVIEW_ONLY_NO_GO",
            "kind": kind, "job_id": row["job_id"],
            "held": held, "attempts": row["attempts"],
            "max_attempts": row["max_attempts"],
            "last_reason": row["last_reason"],
            "running_jobs": running, "active_rearms": active,
            "exact_row_fingerprint_sha256": _fp(row) if held else None,
            "candidate_for_independent_owner_review":
                bool(held and running == 0 and active == 0),
            "task_scheduler_owner_and_event_binding": "NOT_ATTESTED_BY_PREVIEW",
            "actual_rearm_authorized": False, "db_writes": 0,
            "public_api_gets": 0, "scheduler_changed": False,
            "auto_promoted": False,
        }


def apply_one(root: Path, *, kind: str, expected_sha256: str,
              owner_authorized: bool = False,
              task_evidence_independently_verified: bool = False,
              now: datetime | None = None) -> dict:
    """Core only, NOT a live CLI. Owner and task evidence must be enforced
    independently by a future trusted owner launcher, not merely booleans.
    """
    if (owner_authorized is not True
            or task_evidence_independently_verified is not True):
        raise OwnerRearmError("independent owner/task authorization required")
    _require_synthetic_root(root)
    current = _clock(now)
    due = queue._stamp(current + COOLDOWN)
    with closing(_conn(root, readonly=False)) as db:
        try:
            db.execute("BEGIN IMMEDIATE")
            row = _row(db, kind)
            if (type(expected_sha256) is not str
                    or len(expected_sha256) != 64
                    or _fp(row) != expected_sha256):
                raise OwnerRearmError("fresh row fingerprint required")
            if not _held(row) or _running(db) != 0 or _active(db) != 0:
                raise OwnerRearmError("job/overlap safety contract failed")
            db.execute(
                "CREATE TABLE IF NOT EXISTS " + TABLE + " ("
                "operation_sha256 TEXT PRIMARY KEY,job_id INTEGER NOT NULL,"
                "kind TEXT NOT NULL,before_sha256 TEXT NOT NULL UNIQUE,"
                "after_sha256 TEXT NOT NULL,before_due_at TEXT NOT NULL,"
                "before_attempts INTEGER NOT NULL,before_reason TEXT NOT NULL,"
                "scheduled_due_at TEXT NOT NULL,"
                "state TEXT NOT NULL CHECK(state IN ('ACTIVE','ROLLED_BACK')))"
            )
            op = sha256(
                (SCHEMA + "|" + kind + "|" + expected_sha256 + "|" + due
                 ).encode("ascii")).hexdigest()
            db.execute(
                "UPDATE jobs SET status='PENDING',attempts=0,due_at=?,"
                "last_reason=NULL,lease_token=NULL,lease_expires_at=NULL "
                "WHERE job_id=? AND status='REVIEW_REQUIRED'",
                (due, row["job_id"]))
            after = _row(db, kind)
            db.execute(
                "INSERT INTO " + TABLE + "("
                "operation_sha256,job_id,kind,before_sha256,after_sha256,"
                "before_due_at,before_attempts,before_reason,scheduled_due_at,"
                "state) VALUES(?,?,?,?,?,?,?,?,?,'ACTIVE')",
                (op, row["job_id"], kind, expected_sha256, _fp(after),
                 row["due_at"], row["attempts"], row["last_reason"], due))
            db.execute("COMMIT")
        except Exception:
            if db.in_transaction:
                db.execute("ROLLBACK")
            raise
    return {"schema": SCHEMA, "status": "ONE_P10_PENDING_DELAYED_OWNER_ACTION",
            "kind": kind, "operation_sha256": op, "scheduled_due_at": due,
            "worker_started": False, "public_api_gets": 0,
            "scheduler_changed": False, "auto_promoted": False}


def rollback_one(root: Path, *, operation_sha256: str,
                 owner_authorized: bool = False,
                 task_evidence_independently_verified: bool = False,
                 now: datetime | None = None) -> dict:
    """Only before due, with original unchanged pending row and no workers."""
    if (owner_authorized is not True
            or task_evidence_independently_verified is not True):
        raise OwnerRearmError("independent owner/task authorization required")
    _require_synthetic_root(root)
    current = _clock(now)
    if (type(operation_sha256) is not str or len(operation_sha256) != 64
            or any(c not in "0123456789abcdef" for c in operation_sha256)):
        raise OwnerRearmError("invalid operation fingerprint")
    with closing(_conn(root, readonly=False)) as db:
        try:
            db.execute("BEGIN IMMEDIATE")
            if _running(db) or _active(db) != 1:
                raise OwnerRearmError("overlap or invalid recovery state")
            receipt = db.execute(
                "SELECT * FROM " + TABLE +
                " WHERE operation_sha256=? AND state='ACTIVE'",
                (operation_sha256,)).fetchone()
            if receipt is None or receipt["kind"] not in SAFE_KINDS:
                raise OwnerRearmError("unknown active operation")
            if current >= queue._parse(receipt["scheduled_due_at"]):
                raise OwnerRearmError("rollback deadline expired")
            row = _row(db, receipt["kind"])
            if (row["job_id"] != receipt["job_id"]
                    or row["status"] != "PENDING" or row["attempts"] != 0
                    or _fp(row) != receipt["after_sha256"]):
                raise OwnerRearmError("pending job changed; refuse rollback")
            db.execute(
                "UPDATE jobs SET status='REVIEW_REQUIRED',attempts=?,"
                "due_at=?,last_reason=?,lease_token=NULL,lease_expires_at=NULL "
                "WHERE job_id=?",
                (receipt["before_attempts"], receipt["before_due_at"],
                 receipt["before_reason"], row["job_id"]))
            if _fp(_row(db, receipt["kind"])) != receipt["before_sha256"]:
                raise OwnerRearmError("exact rollback fingerprint mismatch")
            db.execute(
                "UPDATE " + TABLE + " SET state='ROLLED_BACK'"
                " WHERE operation_sha256=? AND state='ACTIVE'",
                (operation_sha256,))
            db.execute("COMMIT")
        except Exception:
            if db.in_transaction:
                db.execute("ROLLBACK")
            raise
    return {"schema": SCHEMA, "status": "ONE_P10_OWNER_ROLLBACK_OBSERVED",
            "operation_sha256": operation_sha256,
            "worker_stopped": False, "public_api_gets": 0,
            "scheduler_changed": False, "auto_promoted": False}


def main() -> int:
    # Intentional PREVIEW-ONLY user interface; no --apply/--rollback options.
    parser = argparse.ArgumentParser(description="UCIE P10 owner preview only")
    parser.add_argument("--ucie-root", type=Path, required=True)
    parser.add_argument("--kind", choices=sorted(SAFE_KINDS), required=True)
    args = parser.parse_args()
    try:
        if args.ucie_root.resolve() != Path("D:/UCIE").resolve():
            raise OwnerRearmError("exact Windows owner UCIE root required")
        result = preview(args.ucie_root, kind=args.kind)
    except (OwnerRearmError, queue.PendingQueueError,
            sqlite3.Error, OSError, ValueError) as exc:
        print(json.dumps({
            "schema": SCHEMA, "status": "OWNER_REARM_FAIL_CLOSED",
            "error_type": type(exc).__name__, "db_writes": 0,
            "scheduler_changed": False}, sort_keys=True))
        return 2
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
