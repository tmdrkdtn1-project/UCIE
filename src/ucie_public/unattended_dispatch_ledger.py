"""Append-only UCIE operation lifecycle receipts, never an action dispatcher.

SQLite serializes local writes, but CANNOT attest DB rollback/replacement.
Caller must separately pin the latest event digest and owner epoch in an
independent, OS-protected anti-rollback service before live activity.
No arbitrary paths, host process, network, secret or rulepack operation.
"""
from __future__ import annotations

from contextlib import closing
from datetime import datetime, timezone
import hashlib
from pathlib import Path
import sqlite3
import re

from .policy import PolicyError
from .rulepack import canonical_json
from .unattended_journal import _checked_db_path
from .unattended_ops import TASK, SHA64

GENESIS = "0" * 64
SCHEMA = "UCIE_OWNER_OPERATION_LIFECYCLE_V1"
EVENTS_TABLE = """
CREATE TABLE IF NOT EXISTS operation_events(
  event_number INTEGER PRIMARY KEY AUTOINCREMENT,
  task_id TEXT NOT NULL,
  grant_sha256 TEXT NOT NULL,
  operation TEXT NOT NULL,
  state TEXT NOT NULL,
  detail_sha256 TEXT NOT NULL,
  recorded_utc TEXT NOT NULL,
  previous_sha256 TEXT NOT NULL,
  event_sha256 TEXT NOT NULL UNIQUE
)
"""
OP = frozenset({"GIT_BRANCH_PUBLISH", "C40_RECOVERY", "RULE_SHADOW_REVIEW"})
START = frozenset({"CLAIMED"})
TRANSITIONS = {
    "CLAIMED": frozenset({"REMOTE_MUTATION_STARTED", "RECOVERY_STARTED", "FAILED_CLOSED"}),
    "REMOTE_MUTATION_STARTED": frozenset({"DRAFT_PR_API_RESPONSE", "AMBIGUOUS_REMOTE_STATE", "FAILED_CLOSED"}),
    "DRAFT_PR_API_RESPONSE": frozenset({"CI_PENDING", "AMBIGUOUS_REMOTE_STATE"}),
    "CI_PENDING": frozenset({"CI_PASS_REVIEW_REQUIRED", "CI_FAILED_HOLD"}),
    "RECOVERY_STARTED": frozenset({"C40_POST_PROBE_PASS", "C40_POST_PROBE_FAILED_HOLD"}),
    "AMBIGUOUS_REMOTE_STATE": frozenset({"OPERATOR_RECONCILIATION_REQUIRED"}),
}
TERMINAL = frozenset({
    "CI_PASS_REVIEW_REQUIRED", "CI_FAILED_HOLD", "C40_POST_PROBE_PASS",
    "C40_POST_PROBE_FAILED_HOLD", "FAILED_CLOSED", "OPERATOR_RECONCILIATION_REQUIRED",
})


def _make_hash(obj: dict) -> str:
    return hashlib.sha256(canonical_json(obj)).hexdigest()


def _require_utc(now: datetime) -> str:
    if (not isinstance(now, datetime) or now.tzinfo is None
            or now.utcoffset() != timezone.utc.utcoffset(now)):
        raise PolicyError("UCIE lifecycle requires UTC")
    return now.replace(microsecond=0).strftime("%Y-%m-%dT%H:%M:%SZ")


def _check_rows(rows: list[tuple]) -> None:
    previous = GENESIS
    task_state: dict[str, tuple[str, str, str]] = {}
    for number, task, grant, op, state, detail, time, prev, event in rows:
        if (type(number) is not int or number <= 0 or
                type(task) is not str or TASK.fullmatch(task) is None or
                type(grant) is not str or SHA64.fullmatch(grant) is None or
                op not in OP or state not in START | TERMINAL | frozenset(TRANSITIONS) |
                frozenset(x for values in TRANSITIONS.values() for x in values) or
                type(detail) is not str or SHA64.fullmatch(detail) is None or
                prev != previous):
            raise PolicyError("UCIE operation journal chain invalid")
        core = {
            "schema": SCHEMA, "event_number": number, "task_id": task,
            "grant_sha256": grant, "operation": op, "state": state,
            "detail_sha256": detail, "recorded_utc": time,
            "previous_sha256": prev,
        }
        if _make_hash(core) != event:
            raise PolicyError("UCIE operation journal receipt altered")
        old = task_state.get(task)
        if old is None:
            if state != "CLAIMED":
                raise PolicyError("UCIE operation must first be claimed")
        else:
            if grant != old[1] or op != old[2] or state not in TRANSITIONS.get(old[0], frozenset()):
                raise PolicyError("UCIE operation lifecycle unauthorized transition")
        task_state[task] = (state, grant, op)
        previous = event


def append_operation_receipt(
    journal_dir: Path, *, task_id: str, grant_sha256: str,
    operation: str, next_state: str, detail_sha256: str,
    expected_previous_head: str, at_time: datetime | None = None,
) -> dict:
    """Append exactly one transition with an expected head lease.

    The 'expected_previous_head' MUST come from a trusted external OS
    anchor for real execution; a caller-submitted value is not evidence.
    A trusted host must attest and advance its separate monotonic epoch.
    """
    if (type(task_id) is not str or TASK.fullmatch(task_id) is None
            or type(grant_sha256) is not str or SHA64.fullmatch(grant_sha256) is None
            or operation not in OP or type(operation) is not str
            or type(next_state) is not str or
            next_state not in START | TERMINAL | frozenset(TRANSITIONS)
            | frozenset(x for values in TRANSITIONS.values() for x in values)
            or type(detail_sha256) is not str or SHA64.fullmatch(detail_sha256) is None
            or type(expected_previous_head) is not str
            or SHA64.fullmatch(expected_previous_head) is None):
        raise PolicyError("UCIE lifecycle receipt field invalid")
    db = _checked_db_path(journal_dir)
    now = _require_utc(datetime.now(timezone.utc) if at_time is None else at_time)
    try:
        with closing(sqlite3.connect(str(db), timeout=2.0, isolation_level=None)) as conn:
            conn.execute("PRAGMA busy_timeout=2000")
            conn.execute("PRAGMA synchronous=FULL")
            conn.execute("PRAGMA trusted_schema=OFF")
            conn.execute("BEGIN IMMEDIATE")
            conn.execute(EVENTS_TABLE)
            rows = conn.execute(
                "SELECT event_number,task_id,grant_sha256,operation,state,"
                "detail_sha256,recorded_utc,previous_sha256,event_sha256 "
                "FROM operation_events ORDER BY event_number"
            ).fetchall()
            _check_rows(rows)
            last_head = rows[-1][-1] if rows else GENESIS
            if expected_previous_head != last_head:
                raise PolicyError("UCIE lifecycle external head mismatch")
            state_row = conn.execute(
                "SELECT state,grant_sha256,operation FROM operation_events "
                "WHERE task_id=? ORDER BY event_number DESC LIMIT 1", (task_id,)
            ).fetchone()
            if state_row is None:
                if next_state != "CLAIMED":
                    raise PolicyError("UCIE operation not yet claimed")
            elif (state_row[1] != grant_sha256 or state_row[2] != operation
                    or next_state not in TRANSITIONS.get(state_row[0], frozenset())):
                raise PolicyError("UCIE illegal or duplicate operation transition")
            num = (rows[-1][0] + 1) if rows else 1
            payload = {
                "schema": SCHEMA, "event_number": num, "task_id": task_id,
                "grant_sha256": grant_sha256, "operation": operation,
                "state": next_state, "detail_sha256": detail_sha256,
                "recorded_utc": now, "previous_sha256": last_head,
            }
            head = _make_hash(payload)
            conn.execute(
                "INSERT INTO operation_events(event_number,task_id,grant_sha256,"
                "operation,state,detail_sha256,recorded_utc,previous_sha256,event_sha256)"
                " VALUES(?,?,?,?,?,?,?,?,?)",
                (num, task_id, grant_sha256, operation, next_state,
                 detail_sha256, now, last_head, head))
            conn.execute("COMMIT")
    except (sqlite3.Error, OSError) as exc:
        raise PolicyError("UCIE lifecycle SQLite receipt could not be written") from exc
    return {
        "schema": SCHEMA, "status": "UCIE_LOCAL_LIFECYCLE_RECEIPT_ONLY",
        "event_number": num, "state": next_state, "task_id": task_id,
        "previous_sha256": last_head, "event_sha256": head,
        "external_anchor_advanced": False,
        "external_anchor_verified": False,
        "operation_executed": False, "rule_auto_promoted": False,
    }


def inspect_lifecycle(journal_dir: Path, *, expected_external_head: str) -> dict:
    """Read-only integrity check against an independently supplied head."""
    if type(expected_external_head) is not str or SHA64.fullmatch(expected_external_head) is None:
        raise PolicyError("expected UCIE external head required")
    db = _checked_db_path(journal_dir)
    if not db.exists():
        if expected_external_head != GENESIS:
            raise PolicyError("UCIE journal absent but external head exists")
        return {"status": "UCIE_LOCAL_LEDGER_GENESIS_ONLY", "head_sha256": GENESIS,
                "event_count": 0, "external_anchor_independent": False}
    try:
        with closing(sqlite3.connect(str(db), timeout=2.0)) as conn:
            conn.execute("PRAGMA query_only=ON")
            rows = conn.execute(
                "SELECT event_number,task_id,grant_sha256,operation,state,"
                "detail_sha256,recorded_utc,previous_sha256,event_sha256 "
                "FROM operation_events ORDER BY event_number"
            ).fetchall()
        _check_rows(rows)
        head = rows[-1][-1] if rows else GENESIS
        if head != expected_external_head:
            raise PolicyError("UCIE local lifecycle differs from external head")
        return {
            "status": "UCIE_LOCAL_CHAIN_MATCHES_SUPPLIED_HEAD_NOT_OS_ATTESTED",
            "head_sha256": head, "event_count": len(rows),
            "external_anchor_independent": False,
        }
    except sqlite3.Error as exc:
        raise PolicyError("UCIE lifecycle ledger unavailable") from exc
