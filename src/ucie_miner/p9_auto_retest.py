"""P9 first-party read-only retest automation on existing P10 experiment worker.

One new immutable P9 receipt per already recorded P11 improvement review.
Reads the P11 ledger in SQLite read-only mode and writes only a small
deduplicated receipt to the P10 UCIE-only queue database. Does not schedule
new jobs, touch the original public miner, approve code, apply upstream code,
or write to the P11/owner source of truth. The P10 worker lease serializes
normal execution; SQLite uniqueness fences duplicate completion/retry.
"""
from __future__ import annotations

from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path
import sqlite3

from . import pending_queue as queue
from . import p11_closed_loop as p11
from . import p11_retest as p9
from .public_discovery import SOURCES

SCHEMA = "UCIE_P9_P10_AUTOMATIC_RETEST_RECEIPT_V1"
MAX_SOURCE_REVIEWS = p11.MAX_LEADS
RECORDED = "P9_RETEST_RECEIPT_RECORDED_UNADOPTED"
NO_WORK = "P9_NO_NEW_RETEST_REVIEW"
NO_OPT_IN = "P9_P11_NOT_ENABLED_NO_WORK"
DECISIONS = frozenset({
    "FIRST_PARTY_RETEST_PASS_MANUAL_REVIEW_ONLY",
    "FIRST_PARTY_RETEST_REGRESSION_HOLD_NO_GO",
})


class P9AutoRetestError(ValueError):
    pass


def _read_review_index(root: Path) -> list[tuple[str, int, str]]:
    """Read bound old+new P11 improvement receipts, never backfill history."""
    db_path, _ = p11._paths(root)
    with closing(sqlite3.connect(
            db_path.as_uri() + "?mode=ro", uri=True, timeout=0.25)) as db:
        db.execute("PRAGMA query_only=ON")
        present = db.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' "
            "AND name='improvement_review'").fetchone()
        if present is None:
            return []  # Old 65 experiences without P8 reviews remain untouched.
        rows = db.execute(
            "SELECT source,pr_number,receipt_sha256 FROM improvement_review "
            "ORDER BY observed_at,source,pr_number LIMIT ?",
            (MAX_SOURCE_REVIEWS + 1,)).fetchall()
    if len(rows) > MAX_SOURCE_REVIEWS:
        raise P9AutoRetestError("P9 candidate ledger exceeds bounded history")
    for source, pr_number, receipt in rows:
        if (source not in SOURCES or type(pr_number) is not int
                or not 1 <= pr_number <= 999999999
                or not p9._digest(receipt)):
            raise P9AutoRetestError("P9 review source identity invalid")
    return rows


def _existing_receipts(root: Path) -> dict[tuple[str, int], str]:
    with closing(queue._conn(root)) as db:
        exists = db.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' "
            "AND name='p9_retest_receipts'").fetchone()
        if exists is None:
            return {}
        rows = db.execute(
            "SELECT source,pr_number,original_receipt_sha256 "
            "FROM p9_retest_receipts LIMIT ?", (MAX_SOURCE_REVIEWS + 1,)
        ).fetchall()
    if len(rows) > MAX_SOURCE_REVIEWS:
        raise P9AutoRetestError("P9 retest receipt history exceeds bound")
    return {(r["source"], r["pr_number"]): r["original_receipt_sha256"]
            for r in rows}


def run_one(root: Path) -> dict:
    """Process one new, validated P8 review after the regular P10 experiment.

    NO_WORK is real idle, not an invented learning event. A failed retest
    raises so the normal P10 worker retry/hold path applies. A passing retest
    is a MANUAL REVIEW candidate only, never an auto-adoption.
    """
    root = Path(root)
    queue._root(root)  # exact UCIE root and existing runtime only
    if not p11.enabled(root):
        return {
            "schema": SCHEMA, "status": NO_OPT_IN,
            "retest_receipts_written": 0, "auto_promoted": False,
            "p11_database_writes": 0, "scheduler_modified": False,
        }
    reviews = _read_review_index(root)
    known = _existing_receipts(root)
    # A formerly recorded receipt cannot silently change in the P11 ledger.
    for source, pr, digest in reviews:
        prior = known.get((source, pr))
        if prior is not None and prior != digest:
            raise P9AutoRetestError("original review SHA changed after retest")
    # Fail closed if an old P9 result no longer has its original P11 review.
    identities = {(source, pr) for source, pr, _ in reviews}
    if any(key not in identities for key in known):
        raise P9AutoRetestError("source review vanished after retest")

    item = next(
        ((source, pr, digest) for source, pr, digest in reviews
         if (source, pr) not in known), None)
    if item is None:
        return {
            "schema": SCHEMA, "status": NO_WORK,
            "candidate_reviews_seen": len(reviews),
            "retest_receipts_written": 0,
            "auto_promoted": False, "p11_database_writes": 0,
            "scheduler_modified": False,
        }
    source, pr_number, original_sha = item
    out = p9.retest(root, limit=1, source=source, pr_number=pr_number)
    if (out.get("status") != "P9_FIRST_PARTY_RETEST_COMPLETE_UNADOPTED"
            or out.get("review_rows_checked") != 1
            or len(out.get("items", [])) != 1
            or out.get("auto_promoted") is not False
            or out.get("operating_database_writes") != 0
            or out.get("network_requests") != 0):
        raise P9AutoRetestError("P9 validated retest contract changed")
    result = out["items"][0]
    if (result.get("source_id") != "repo:" + source
            or result.get("pr_number") != pr_number
            or result.get("original_receipt_sha256") != original_sha
            or result.get("retest_decision") not in DECISIONS
            or not p9._digest(result.get("retest_receipt_sha256"))
            or result.get("workloads_checked") != 3
            or result.get("production_code_adopted") is not False
            or result.get("automatically_approved") is not False):
        raise P9AutoRetestError("P9 retest result identity or safety changed")

    recorded_at = datetime.now(timezone.utc).isoformat(timespec="microseconds")
    with closing(queue._conn(root)) as db:
        db.execute("BEGIN IMMEDIATE")
        db.execute("""CREATE TABLE IF NOT EXISTS p9_retest_receipts (
            source TEXT NOT NULL, pr_number INTEGER NOT NULL,
            original_receipt_sha256 TEXT NOT NULL,
            retest_receipt_sha256 TEXT NOT NULL,
            decision TEXT NOT NULL CHECK(decision IN (
                'FIRST_PARTY_RETEST_PASS_MANUAL_REVIEW_ONLY',
                'FIRST_PARTY_RETEST_REGRESSION_HOLD_NO_GO')),
            recorded_at TEXT NOT NULL,
            PRIMARY KEY(source,pr_number)
        )""")
        db.execute(
            "INSERT OR IGNORE INTO p9_retest_receipts VALUES(?,?,?,?,?,?)",
            (source, pr_number, original_sha,
             result["retest_receipt_sha256"], result["retest_decision"],
             recorded_at))
        inserted = db.execute("SELECT changes()").fetchone()[0]
        stored = db.execute(
            "SELECT original_receipt_sha256,retest_receipt_sha256,decision "
            "FROM p9_retest_receipts WHERE source=? AND pr_number=?",
            (source, pr_number)).fetchone()
        if (stored is None or tuple(stored) != (
                original_sha, result["retest_receipt_sha256"],
                result["retest_decision"])):
            db.execute("ROLLBACK")
            raise P9AutoRetestError("conflicting or stale P9 retest receipt")
        db.execute("COMMIT")
    return {
        "schema": SCHEMA, "status": RECORDED if inserted else NO_WORK,
        "source_id": "repo:" + source, "pr_number": pr_number,
        "original_receipt_sha256": original_sha,
        "retest_receipt_sha256": result["retest_receipt_sha256"],
        "retest_decision": result["retest_decision"],
        "retest_receipts_written": inserted,
        "p10_queue_receipts_written": inserted,
        "p11_database_writes": 0,
        "original_public_miner_writes": 0,
        "scheduler_modified": False,
        "production_code_adopted": False, "auto_promoted": False,
    }
