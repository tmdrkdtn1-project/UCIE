"""UCIE P11 one owner-approved anonymous GitHub metadata GET diagnostic.

NOT a P10 queue reset: exactly one approved source URL is requested at most
once, only with explicit owner action. No task change, P10 rearm, credentials,
extra endpoints, private data, untrusted code execution or auto promotion.
An interrupted request consumes its single-use receipt (fail closed).
"""
from __future__ import annotations

import argparse
from contextlib import closing
from datetime import datetime, timedelta, timezone
from hashlib import sha256
import json
import os
from pathlib import Path
import re
import sqlite3
import tempfile

from . import pending_queue as q
from . import p11_closed_loop as p11
from . import p11_rate_guard_v03 as rate
from . import p10_owner_single_live_rearm_v02 as owner
from . import worker
from .public_discovery import public_feed_get, public_feed_url, SOURCES

SCHEMA = "UCIE_P11_OWNER_EXACT_ONE_GET_TRIAL_V01"
TABLE = "p11_owner_exact_one_get_trial_v01"
KIND = "PUBLIC_INCREMENTAL_MINING"
JOB_ID = 6
SOURCE = "python/cpython"
SOURCE_INDEX = 0
CONSENT = "UCIE_OWNER_APPROVES_ONE_PUBLIC_GET_ACCEPTING_UNKNOWN_SHARED_QUOTA"
SYNTH_MARKER = "UCIE_P11_ONE_GET_SYNTHETIC_ONLY_V01"
P10_RECENT_AGE = timedelta(minutes=30)
SOURCE_BEFORE_SHA = owner.COLUMNS


class OneGetError(ValueError):
    pass


def _scope(root: Path, *, mutation: bool) -> Path:
    if not isinstance(root, Path) or root.is_symlink():
        raise OneGetError("exact UCIE root required")
    resolved = root.resolve()
    if resolved == owner.ROOT.resolve():
        owner._validate_root(resolved)
        owner._attest_windows_owner(resolved)
    else:
        temp = Path(tempfile.gettempdir()).resolve()
        marker = resolved / "runtime" / "UCIE_P11_ONE_GET_SYNTH_ONLY.marker"
        if (resolved.name.casefold() != "ucie"
                or not resolved.is_relative_to(temp)
                or resolved.is_symlink() or marker.is_symlink()
                or not marker.is_file()
                or marker.read_text(encoding="ascii") != SYNTH_MARKER):
            raise OneGetError("non-owner root without synthetic proof denied")
    if not p11.enabled(resolved):
        raise OneGetError("P11 opt-in and existing ledger required")
    if (resolved / "runtime" / p11.DB_NAME).is_symlink():
        raise OneGetError("linked P11 ledger denied")
    return resolved


def _last_miner_ok(root: Path, now: datetime) -> bool:
    path = root / "runtime" / "last_run.json"
    if (path.is_symlink() or not path.is_file()
            or not 10 <= path.stat().st_size <= 4096):
        return False
    try:
        row = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(row, dict) or row.get("schema") != "UCIE_MINER_CYCLE_V1":
            return False
        finish = p11._parse(row["finished_utc"])
        if not timedelta(0) <= now - finish <= P10_RECENT_AGE:
            return False
        if (row.get("status") != "COLLECTED_UNVERIFIED"
                or row.get("production_approved") is not False
                or row.get("error_http_status") in (403, 429)
                or row.get("consecutive_failures", 0) != 0):
            return False
        if row.get("stage10_status") in (
                "STAGE10_HOURLY_FAILED_NO_GO",
                "STAGE10_HOURLY_PARTIAL_NO_GO"):
            return False
        if row.get("stage10_error_category") in (
                "UPSTREAM_HTTP_403", "UPSTREAM_HTTP_429"):
            return False
        if row.get("stage13_history_status") in (
                "EXTERNAL_HISTORY_RATE_BUDGET_PAUSED_NO_GO",
                "EXTERNAL_HISTORY_UPSTREAM_OR_METADATA_FAILED_NO_GO"):
            return False
        if row.get("stage16_safe_qa_status") in (
                "STAGE16_SAFE_QA_RATE_PAUSED_NO_GO",
                "STAGE16_SAFE_QA_24H_BUDGET_PAUSED_NO_GO"):
            return False
        return True
    except (KeyError, OSError, ValueError, TypeError):
        return False


def _p11_readonly(root: Path):
    dbpath, _ = p11._paths(root)
    conn = sqlite3.connect(dbpath.as_uri()+"?mode=ro", uri=True,
                           isolation_level=None, timeout=0.5)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA query_only=ON")
    return conn


def _queue_preimage(root: Path):
    with closing(owner._conn(root, readonly=True)) as db:
        rows = db.execute(
            "SELECT "+",".join(SOURCE_BEFORE_SHA)+" FROM jobs "
            "WHERE kind=?", (KIND,)).fetchall()
        if len(rows) != 1:
            raise OneGetError("exact one P11 queue job required")
        row = rows[0]
        if (row["job_id"] != JOB_ID or
                row["dedupe_key"] != "UCIE:P10:PUBLIC_INCREMENTAL_MINING" or
                row["status"] != "REVIEW_REQUIRED" or
                row["attempts"] != 5 or row["max_attempts"] != 5 or
                row["last_reason"] != "RETRYABLE_ERROR" or
                row["lease_token"] is not None or
                row["lease_expires_at"] is not None or
                row["completed_at"] is not None):
            raise OneGetError("P11 queue identity/hold state denied")
        if db.execute(
            "SELECT COUNT(*) FROM jobs WHERE status='RUNNING'"
        ).fetchone()[0] != 0:
            raise OneGetError("another worker running")
        active = db.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
            (owner.TABLE,)).fetchone()
        if active and db.execute(
            "SELECT COUNT(*) FROM "+owner.TABLE+" WHERE state='ACTIVE'"
        ).fetchone()[0]:
            raise OneGetError("P10 owner operation active")
        return owner._fingerprint(row)


def _cursor_preflight(root: Path, now: datetime) -> dict:
    status = p11.status(root)
    if (status["status"] != "P11_PUBLIC_EVIDENCE_EXPERIENCE_READ_ONLY"
            or status["sources"] != len(SOURCES)
            or status["next_source_id"] != "repo:"+SOURCE
            or status["auto_promoted"] is not False
            or status["production_improvements_auto_applied"] != 0
            or status["rate_guard_active"]
            or status["last_public_attempt_failed"] is not True):
        raise OneGetError("P11 source/rate/promotion guard not eligible")
    due = status["next_public_get_due_utc"]
    if due is not None and now < p11._parse(due):
        raise OneGetError("existing P11 5m cooldown not due")
    with closing(_p11_readonly(root)) as db:
        cursor = db.execute(
            "SELECT source_index,last_attempt_at,last_attempt_failed "
            "FROM cursor WHERE slot=1").fetchone()
        if cursor is None or cursor["source_index"] != SOURCE_INDEX:
            raise OneGetError("P11 source cursor drift")
        row = db.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
            (TABLE,)).fetchone()
        if row is not None:
            # Exactly ONE allowed trial for this version, even if it failed,
            # crashed, timed out or never made a network request.
            raise OneGetError("P11 one-shot receipt already exists")
    return {"source_id": "repo:"+SOURCE,
            "old_attempt_failed": status["last_public_attempt_failed"],
            "rate_guard_active": False}


def preview(root: Path, *, now: datetime | None = None) -> dict:
    now = datetime.now(timezone.utc) if now is None else now
    p11._stamp(now)
    root = _scope(root, mutation=False)
    fp = _queue_preimage(root)
    if not _last_miner_ok(root, now):
        raise OneGetError("recent healthy UCIE 10m collector receipt required")
    cursor = _cursor_preflight(root, now)
    return {
        "schema": SCHEMA,
        "status": "ONE_GET_OWNER_PREVIEW_ONLY_SHARED_QUOTA_UNKNOWN",
        "kind": KIND, "job_id": JOB_ID,
        "exact_held_row_sha256": fp,
        "source_id": cursor["source_id"],
        "shared_public_miner_last_run_healthy": True,
        "shared_rate_remaining_verified": False,
        "max_additional_approved_public_gets": 1,
        "requested_public_gets": 0, "p10_queue_modified": False,
        "scheduler_modified": False, "auto_promoted": False,
    }


def _rate_header_snapshot(headers) -> dict:
    # Single-use, first-party observer never persists untrusted raw headers.
    def read(name):
        try:
            raw = headers.get(name)
        except (AttributeError, TypeError, ValueError):
            return None
        if (type(raw) is not str or
                re.fullmatch(r"[0-9]{1,12}", raw.strip()) is None):
            return None
        return int(raw.strip())
    remaining, reset = read("X-RateLimit-Remaining"), read("X-RateLimit-Reset")
    return {
        "remaining": remaining if remaining is not None and remaining <= 500000 else None,
        "reset_epoch": reset if reset is not None and reset <= 4102444800 else None,
    }


def _prepare(root: Path, *, now: datetime, fingerprint: str) -> str:
    operation = sha256(
        (SCHEMA+"|"+KIND+"|"+fingerprint+"|"+p11._stamp(now)).encode("ascii")
    ).hexdigest()
    with closing(p11._conn(root)) as db:
        try:
            db.execute("BEGIN IMMEDIATE")
            cursor = db.execute(
                "SELECT source_index FROM cursor WHERE slot=1").fetchone()
            if cursor is None or cursor["source_index"] != SOURCE_INDEX:
                raise OneGetError("P11 cursor drift at prepare")
            guard = rate.view(db, source_index=SOURCE_INDEX, now=now)
            if guard["active"]:
                raise OneGetError("P11 rate hold active before GET")
            if db.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
                (TABLE,)).fetchone() is not None:
                raise OneGetError("duplicate P11 trial forbidden")
            db.execute(
                "CREATE TABLE "+TABLE+" ("
                "slot INTEGER PRIMARY KEY CHECK(slot=1),"
                "operation_sha256 TEXT NOT NULL UNIQUE,"
                "job_id INTEGER NOT NULL CHECK(job_id=6),"
                "source_index INTEGER NOT NULL CHECK(source_index=0),"
                "requested_utc TEXT NOT NULL,"
                "state TEXT NOT NULL CHECK(state IN "
                "('PREPARED','SUCCESS','FAILED','NO_GET')),"
                "get_count INTEGER NOT NULL CHECK(get_count BETWEEN 0 AND 1),"
                "failure_class TEXT,"
                "rate_remaining INTEGER,"
                "rate_reset_epoch INTEGER)"
            )
            db.execute(
                "INSERT INTO "+TABLE+" VALUES(1,?,?,?,?,?,0,NULL,NULL,NULL)",
                (operation, JOB_ID, SOURCE_INDEX, p11._stamp(now),
                 "PREPARED"))
            db.execute("COMMIT")
        except Exception:
            if db.in_transaction:
                db.execute("ROLLBACK")
            raise
    return operation


def _seal(root: Path, *, operation: str, state: str, called: int,
          category: str | None, headers: dict) -> None:
    if (state not in ("SUCCESS","FAILED","NO_GET")
            or type(called) is not int or called not in (0,1)
            or category is not None and category not in p11.PUBLIC_FAILURE_CLASSES):
        raise OneGetError("invalid one-get receipt")
    with closing(p11._conn(root)) as db:
        db.execute("BEGIN IMMEDIATE")
        affected = db.execute(
            "UPDATE "+TABLE+" SET state=?,get_count=?,failure_class=?,"
            "rate_remaining=?,rate_reset_epoch=? "
            "WHERE slot=1 AND operation_sha256=? AND state='PREPARED'",
            (state, called, category, headers.get("remaining"),
             headers.get("reset_epoch"), operation)).rowcount
        if affected != 1:
            db.execute("ROLLBACK")
            raise OneGetError("one-get receipt drift at finalize")
        db.execute("COMMIT")


def apply_one(root: Path, *, expected_sha256: str, consent: str,
              now: datetime | None = None, fetch=None) -> dict:
    if (consent != CONSENT or type(expected_sha256) is not str
            or re.fullmatch("[0-9a-f]{64}", expected_sha256) is None):
        raise OneGetError("exact single-GET owner consent and SHA required")
    now = datetime.now(timezone.utc) if now is None else now
    p11._stamp(now)
    root = _scope(root, mutation=True)
    if root == owner.ROOT.resolve() and fetch is not None:
        raise OneGetError("live root cannot inject network caller")
    with worker._single_instance(root / "runtime") as lock_acquired:
        if not lock_acquired:
            raise OneGetError("shared UCIE PublicMiner lock already held")
        evidence = preview(root, now=now)
        if evidence["exact_held_row_sha256"] != expected_sha256:
            raise OneGetError("exact P11 held row SHA drift")
        operation = _prepare(root, now=now, fingerprint=expected_sha256)
        called = 0
        headers = {"remaining": None, "reset_epoch": None}
        status = "FAILED"
        reason = None

        def single_fetch(url: str):
            nonlocal called
            if (url != public_feed_url(SOURCE) or called != 0):
                raise OneGetError("one exact source URL and GET only")
            called = 1
            if fetch is not None:  # synthetic root only
                return fetch(url)
            return public_feed_get(
                url, observe_rate_headers=lambda h:
                    headers.update(_rate_header_snapshot(h)))

        try:
            result = p11.collect_one(root, fetch=single_fetch, now=now)
            if (result["status"] ==
                    "P11_PUBLIC_HASH_METADATA_STAGED_UNVERIFIED" and called == 1):
                status = "SUCCESS"
            elif called == 0 and result["status"] in (
                    "P11_RATE_WINDOW_NOT_DUE",
                    "P11_FAILED_SOURCE_REMAINS_PENDING",
                    "P11_UPSTREAM_RATE_PAUSED_NO_GET"):
                status = "NO_GET"
            else:
                raise OneGetError("unexpected first-party P11 collector status")
        except Exception:
            try:
                current = p11.status(root)
                reason = current["last_failed_public_attempt_category"]
            except (OSError, ValueError, sqlite3.Error, KeyError):
                reason = None
            status = "FAILED"
        # P11 records the sanitized rate pause itself. Regardless of
        # finalization, a crashed PREPARED operation cannot be replayed.
        _seal(root, operation=operation, state=status, called=called,
              category=reason if reason in p11.PUBLIC_FAILURE_CLASSES else None,
              headers=headers)
    return {
        "schema": SCHEMA,
        "status": {"SUCCESS": "ONE_APPROVED_PUBLIC_GET_SUCCEEDED_UNVERIFIED",
                   "FAILED": "ONE_APPROVED_PUBLIC_GET_FAILED_NO_RETRY",
                   "NO_GET": "ONE_APPROVED_PUBLIC_GET_SKIPPED_NO_NETWORK"}[status],
        "operation_sha256": operation, "kind": KIND,
        "job_id": JOB_ID, "source_id": "repo:"+SOURCE,
        "public_gets_requested": called,
        "sanitized_error_category": reason if reason in p11.PUBLIC_FAILURE_CLASSES else None,
        "rate_remaining_observed": headers["remaining"],
        "rate_reset_epoch_observed": headers["reset_epoch"],
        "p10_queue_modified": False, "p10_job_rearmed": False,
        "scheduler_modified": False, "model_weights_changed": False,
        "auto_promoted": False,
        "shared_budget_independently_verified": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="UCIE owner one GET diagnostic")
    parser.add_argument("--ucie-root", type=Path, required=True)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--expected-sha256")
    parser.add_argument("--owner-consent")
    args = parser.parse_args()
    try:
        if args.apply:
            if args.expected_sha256 is None or args.owner_consent is None:
                raise OneGetError("explicit exact owner action required")
            result = apply_one(args.ucie_root,
                               expected_sha256=args.expected_sha256,
                               consent=args.owner_consent)
        else:
            if args.expected_sha256 is not None or args.owner_consent is not None:
                raise OneGetError("preview may not carry apply fields")
            result = preview(args.ucie_root)
    except (OneGetError, ValueError, OSError, sqlite3.Error) as exc:
        print(json.dumps({
            "schema": SCHEMA, "status": "ONE_PUBLIC_GET_FAIL_CLOSED",
            "error_type": type(exc).__name__,
            "public_gets_requested": None, "p10_job_rearmed": False,
            "scheduler_modified": False, "auto_promoted": False,
        }, sort_keys=True))
        return 2
    print(json.dumps(result, sort_keys=True))
    return 0 if result["status"] != "ONE_APPROVED_PUBLIC_GET_FAILED_NO_RETRY" else 3


if __name__ == "__main__":
    raise SystemExit(main())
