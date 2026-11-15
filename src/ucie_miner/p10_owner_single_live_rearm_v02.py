"""One exact UCIE owner-approved P10 non-network job rearm.

Default is read-only. No shell launches from queue, no task modifications,
public GET, blanket retry-count reset or rule promotion. Live mutation
requires a fresh row hash, exact job ID and real Windows owner/task evidence.

This is intentionally independent of synthetic-only p10_owner_rearm_v01.
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
import subprocess
import sys
import tempfile

from . import pending_queue as q
from .runtime_pipeline import DEDUPES

SCHEMA = "UCIE_P10_OWNER_ONE_NONNETWORK_LIVE_REARM_V02"
TABLE = "p10_owner_live_one_rearm_v02"
KINDS = frozenset(("PUBLIC_METADATA_REVIEW", "UCIE_REPORT_PREPARATION"))
CONSENT = "UCIE_OWNER_APPROVES_EXACT_ONE_NONNETWORK_JOB_REARM"
ROLLBACK_CONSENT = "UCIE_OWNER_APPROVES_EXACT_ONE_NONNETWORK_JOB_ROLLBACK"
FINALIZE_CONSENT = "UCIE_OWNER_APPROVES_EXACT_ONE_NONNETWORK_JOB_FINALIZE"
SYNTH_MARKER = "UCIE_P10_LIVE_REARM_SYNTH_ONLY_V02"
COOLDOWN = timedelta(minutes=10)
ROOT = Path("D:/UCIE")
COLUMNS = ("job_id", "dedupe_key", "kind", "status", "due_at", "attempts",
           "max_attempts", "lease_token", "lease_expires_at", "last_reason",
           "completed_at")

# Exact Windows task identity only. Never queries other tasks, reads their
# files, or grants/suggests privileges. Exit/summary is bounded and sanitized.
OWNER_TASK_PS = r"""
$ErrorActionPreference='Stop'
$name='UCIE-Internal-Minute'
$root='D:\UCIE'
$task=Get-ScheduledTask -TaskPath '\' -TaskName $name -ErrorAction Stop
$info=Get-ScheduledTaskInfo -TaskPath '\' -TaskName $name -ErrorAction Stop
$expectedExe=Join-Path $root '.venv\Scripts\python.exe'
$expectedArg='-B "' + (Join-Path $root 'scripts\internal_minute_tick.py') + '"'
$actions=@($task.Actions)
$triggers=@($task.Triggers)
$actionOk=($actions.Count -eq 1 -and
    [string]::Equals([string]$actions[0].Execute,$expectedExe,
        [StringComparison]::OrdinalIgnoreCase) -and
    [string]::Equals([string]$actions[0].Arguments,$expectedArg,
        [StringComparison]::Ordinal) -and
    [string]::Equals(([string]$actions[0].WorkingDirectory).TrimEnd('\'),
        $root,[StringComparison]::OrdinalIgnoreCase))
$principalOk=$false
try {
    $identity=[string]$task.Principal.UserId
    $sid=if($identity -match '^S-[0-9]+-[0-9]+(-[0-9]+)+$') {
        [Security.Principal.SecurityIdentifier]::new($identity)
    } else {
        ([Security.Principal.NTAccount]::new($identity)).Translate(
            [Security.Principal.SecurityIdentifier])
    }
    $principalOk=($sid.Equals([Security.Principal.WindowsIdentity]::GetCurrent().User) -and
        [string]$task.Principal.LogonType -eq 'Interactive' -and
        [string]$task.Principal.RunLevel -eq 'Limited')
} catch { $principalOk=$false }
$cadenceOk=($triggers.Count -eq 1 -and
    [string]$triggers[0].Repetition.Interval -eq 'PT1M' -and
    [string]$task.Settings.MultipleInstances -eq 'IgnoreNew')
$recentCompleteCount=0
try {
    $xpath="*[System[(EventID=100 or EventID=102 or EventID=200 or EventID=201) and TimeCreated[timediff(@SystemTime) <= 7200000]] and EventData[Data[@Name='TaskName']='\UCIE-Internal-Minute']]"
    $events=@(Get-WinEvent -LogName 'Microsoft-Windows-TaskScheduler/Operational' -FilterXPath $xpath -MaxEvents 64 -ErrorAction Stop)
    $instances=@{}
    foreach($e in $events){
        [xml]$xml=$e.ToXml()
        $node=$xml.SelectSingleNode("//*[local-name()='EventData']/*[local-name()='Data' and (@Name='TaskInstanceId' or @Name='InstanceId')]")
        if($null -eq $node){continue}
        $g=[guid]::Empty
        if(-not [guid]::TryParse([string]$node.InnerText,[ref]$g)){continue}
        $key=$g.ToString('D')
        if(-not $instances.ContainsKey($key)){
            $instances[$key]=@{a=$false;b=$false;c=$false;d=$false;success=$false}
        }
        $row=$instances[$key]
        if($e.Id -eq 100){$row.a=$true}
        if($e.Id -eq 102){$row.b=$true}
        if($e.Id -eq 200){$row.c=$true}
        if($e.Id -eq 201){
            $row.d=$true
            $n=$xml.SelectSingleNode("//*[local-name()='EventData']/*[local-name()='Data' and @Name='ResultCode']")
            $value=[int64]0
            if($null -ne $n -and
                [int64]::TryParse([string]$n.InnerText,[ref]$value) -and
                $value -eq 0){$row.success=$true}
        }
    }
    foreach($row in $instances.Values){
        if($row.a -and $row.b -and $row.c -and $row.d -and $row.success){
            $recentCompleteCount++
        }
    }
} catch {$recentCompleteCount=0}
[pscustomobject]@{
    schema='UCIE_P10_OWNER_LIVE_TASK_ATTEST_V02'
    exact_task_verified=($actionOk -and $principalOk -and $cadenceOk -and
        [string]$task.State -eq 'Ready' -and
        [int64]$info.LastTaskResult -eq 0 -and $recentCompleteCount -gt 0)
    approved_action=$actionOk
    same_owner_least_privilege=$principalOk
    one_minute_no_overlap=$cadenceOk
    last_task_result_zero=([int64]$info.LastTaskResult -eq 0)
    completed_task_instances=$recentCompleteCount
    instance_to_queue_job_completion_proven=$false
    task_or_database_modified=$false
    other_tasks_queried=$false
} | ConvertTo-Json -Compress
"""


class OwnerLiveRearmError(ValueError):
    pass


def _validate_root(root: Path) -> Path:
    if not isinstance(root, Path) or root.is_symlink():
        raise OwnerLiveRearmError("exact owner UCIE root required")
    resolved = root.resolve()
    if (os.name != "nt" or resolved != ROOT.resolve()
            or not (resolved / ".git").is_dir()
            or not (resolved / ".venv" / "Scripts" / "python.exe").is_file()):
        raise OwnerLiveRearmError("exact owner Windows UCIE checkout required")
    if (resolved / "runtime").is_symlink():
        raise OwnerLiveRearmError("linked runtime denied")
    queue_file = q._root(resolved)
    if not queue_file.is_file() or queue_file.is_symlink():
        raise OwnerLiveRearmError("existing UCIE P10 queue required")
    return resolved


def _attest_windows_owner(root: Path) -> dict:
    _validate_root(root)
    child = subprocess.run(
        ["powershell.exe", "-NoProfile", "-NonInteractive",
         "-Command", OWNER_TASK_PS],
        cwd=str(root), capture_output=True, timeout=30, check=False,
        env={"SystemRoot": os.environ.get("SystemRoot", "C:\\Windows"),
             "PATH": os.environ.get("PATH", "")})
    if child.returncode != 0 or len(child.stdout) > 4000:
        raise OwnerLiveRearmError("exact owner task evidence failed")
    try:
        out = json.loads(child.stdout.decode("utf-8-sig", "strict"))
    except (ValueError, UnicodeError) as exc:
        raise OwnerLiveRearmError("invalid task evidence format") from exc
    expected = {
        "schema": "UCIE_P10_OWNER_LIVE_TASK_ATTEST_V02",
        "exact_task_verified": True, "approved_action": True,
        "same_owner_least_privilege": True, "one_minute_no_overlap": True,
        "last_task_result_zero": True,
        "instance_to_queue_job_completion_proven": False,
        "task_or_database_modified": False, "other_tasks_queried": False,
    }
    if (not isinstance(out, dict) or
            any(out.get(k) != v for k, v in expected.items()) or
            type(out.get("completed_task_instances")) is not int or
            not 1 <= out["completed_task_instances"] <= 64):
        raise OwnerLiveRearmError("owner task identity/event failed")
    return {"task_verified": True,
            "recent_task_instances": out["completed_task_instances"],
            "job_completed_by_scheduler_event": False}


def _require_write_gate(root: Path, consent: str, *, action: str) -> None:
    """All internal transaction entrypoints must independently prove scope.

    Production uses owner SID and exact task/event attestation; synthetic
    testing is allowed ONLY in a marked disposable TemporaryDirectory/UCIE.
    Neither path accepts a caller-provided boolean instead of evidence.
    """
    expected = {"apply": CONSENT, "rollback": ROLLBACK_CONSENT,
                "finalize": FINALIZE_CONSENT}.get(action)
    if consent != expected or not isinstance(root, Path) or root.is_symlink():
        raise OwnerLiveRearmError("exact owner action scope/consent required")
    target = root.resolve()
    if target == ROOT.resolve():
        _attest_windows_owner(root)
        return
    if (target.name.casefold() != "ucie"
            or not target.is_relative_to(Path(tempfile.gettempdir()).resolve())):
        raise OwnerLiveRearmError("only disposable synthetic root allowed")
    marker = target / "runtime" / "UCIE_P10_LIVE_REARM_SYNTH_ONLY.marker"
    if (marker.is_symlink() or not marker.is_file()
            or marker.stat().st_size != len(SYNTH_MARKER)
            or marker.read_text(encoding="ascii") != SYNTH_MARKER):
        raise OwnerLiveRearmError("synthetic-only marker required")


def _row(db: sqlite3.Connection, kind: str):
    if kind not in KINDS:
        raise OwnerLiveRearmError("P11 network and unapproved jobs denied")
    row = db.execute("SELECT " + ",".join(COLUMNS) +
                     " FROM jobs WHERE dedupe_key=?", (DEDUPES[kind],)
                     ).fetchone()
    if row is None or row["kind"] != kind or row["job_id"] <= 0:
        raise OwnerLiveRearmError("exact P10 held job not found")
    return row


def _fingerprint(row) -> str:
    return sha256(json.dumps(
        {key: row[key] for key in COLUMNS}, sort_keys=True,
        separators=(",", ":"), ensure_ascii=True
    ).encode("ascii")).hexdigest()


def _held(row) -> bool:
    return (row["status"] == "REVIEW_REQUIRED"
            and row["attempts"] == row["max_attempts"] == q.MAX_ATTEMPTS
            and row["last_reason"] == "RETRYABLE_ERROR"
            and row["lease_token"] is None
            and row["lease_expires_at"] is None
            and row["completed_at"] is None)


def _conn(root, *, readonly):
    path = q._root(root)
    if readonly:
        db = sqlite3.connect(path.as_uri()+"?mode=ro", uri=True,
                             timeout=0.5, isolation_level=None)
        db.execute("PRAGMA query_only=ON")
    else:
        db = sqlite3.connect(str(path), timeout=0.5, isolation_level=None)
    db.row_factory = sqlite3.Row
    return db


def _no_overlap(db) -> bool:
    running = db.execute("SELECT COUNT(*) FROM jobs WHERE status='RUNNING'"
                         ).fetchone()[0]
    present = db.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
        (TABLE,)).fetchone()
    active = 0 if present is None else db.execute(
        "SELECT COUNT(*) FROM "+TABLE+" WHERE state='ACTIVE'"
        ).fetchone()[0]
    return running == 0 and active == 0


def preview(root: Path, kind: str) -> dict:
    root = _validate_root(root)
    evidence = _attest_windows_owner(root)
    with closing(_conn(root, readonly=True)) as db:
        row = _row(db, kind)
        good = _held(row) and _no_overlap(db)
        return {
            "schema": SCHEMA, "status": "EXACT_OWNER_P10_SINGLE_JOB_PREVIEW_ONLY",
            "kind": kind, "job_id": row["job_id"],
            "held": _held(row), "attempts": row["attempts"],
            "last_reason": row["last_reason"],
            "exact_row_fingerprint_sha256": _fingerprint(row) if good else None,
            "eligible_for_explicit_single_owner_action": bool(good),
            **evidence, "apply_executed": False, "queue_modified": False,
            "public_gets": 0, "scheduler_modified": False,
            "auto_promoted": False,
        }


def _commit_once(root: Path, kind: str, job_id: int,
                 expected_sha256: str, now: datetime,
                 *, owner_consent: str) -> dict:
    """Exactly one delayed queue-row transaction; caller MUST attest OS first.

    Publicly callable Python is not an OS security boundary; it requires the
    same local filesystem write permission as direct SQLite modification.
    CLI refuses this route without exact Windows owner-task attestation.
    """
    _require_write_gate(root, owner_consent, action="apply")
    if (kind not in KINDS or type(job_id) is not int or job_id <= 0
            or type(expected_sha256) is not str
            or re.fullmatch("[0-9a-f]{64}", expected_sha256) is None
            or not isinstance(now, datetime) or now.utcoffset() != timedelta(0)):
        raise OwnerLiveRearmError("explicit exact job/fingerprint/UTC required")
    due = q._stamp(now + COOLDOWN)
    with closing(_conn(root, readonly=False)) as db:
        try:
            db.execute("BEGIN IMMEDIATE")
            row = _row(db, kind)
            if (row["job_id"] != job_id or _fingerprint(row) != expected_sha256
                    or not _held(row) or not _no_overlap(db)):
                raise OwnerLiveRearmError("held row drift or active worker")
            db.execute(
                "CREATE TABLE IF NOT EXISTS "+TABLE+"("
                "operation_sha256 TEXT PRIMARY KEY,"
                "job_id INTEGER NOT NULL,kind TEXT NOT NULL,"
                "before_sha256 TEXT NOT NULL UNIQUE,"
                "after_sha256 TEXT NOT NULL,"
                "before_due_at TEXT NOT NULL,"
                "before_reason TEXT NOT NULL,"
                "before_attempts INTEGER NOT NULL,"
                "scheduled_due_at TEXT NOT NULL,"
                "state TEXT NOT NULL CHECK(state IN ('ACTIVE','ROLLED_BACK','COMPLETED')))"
            )
            op = sha256((SCHEMA+"|"+kind+"|"+expected_sha256+"|"+due
                         ).encode("ascii")).hexdigest()
            affected = db.execute(
                "UPDATE jobs SET status='PENDING',attempts=0,due_at=?,"
                "last_reason=NULL,lease_token=NULL,lease_expires_at=NULL "
                "WHERE job_id=? AND status='REVIEW_REQUIRED'",
                (due, job_id)).rowcount
            if affected != 1:
                raise OwnerLiveRearmError("exactly one held row must update")
            after = _row(db, kind)
            db.execute(
                "INSERT INTO "+TABLE+"(operation_sha256,job_id,kind,"
                "before_sha256,after_sha256,before_due_at,before_reason,"
                "before_attempts,scheduled_due_at,state) "
                "VALUES(?,?,?,?,?,?,?,?,?,'ACTIVE')",
                (op, job_id, kind, expected_sha256, _fingerprint(after),
                 row["due_at"], row["last_reason"], row["attempts"], due))
            db.execute("COMMIT")
        except Exception:
            if db.in_transaction:
                db.execute("ROLLBACK")
            raise
    return {
        "schema": SCHEMA, "status": "EXACT_ONE_NONNETWORK_JOB_DELAYED_PENDING",
        "kind": kind, "job_id": job_id,
        "operation_sha256": op, "scheduled_due_at": due,
        "worker_started": False, "public_gets": 0,
        "scheduler_modified": False, "auto_promoted": False,
    }


def _rollback_once(root: Path, operation_sha256: str,
                   now: datetime, *, owner_consent: str) -> dict:
    """Rollback only an unclaimed delayed PENDING job before its due time."""
    _require_write_gate(root, owner_consent, action="rollback")
    if (type(operation_sha256) is not str
            or re.fullmatch("[0-9a-f]{64}", operation_sha256) is None
            or not isinstance(now, datetime)
            or now.utcoffset() != timedelta(0)):
        raise OwnerLiveRearmError("exact operation SHA and UTC required")
    with closing(_conn(root, readonly=False)) as db:
        try:
            db.execute("BEGIN IMMEDIATE")
            found = db.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
                (TABLE,)).fetchone()
            if found is None:
                raise OwnerLiveRearmError("no owner operation recorded")
            active = db.execute(
                "SELECT COUNT(*) FROM "+TABLE+" WHERE state='ACTIVE'"
            ).fetchone()[0]
            running = db.execute(
                "SELECT COUNT(*) FROM jobs WHERE status='RUNNING'"
            ).fetchone()[0]
            if active != 1 or running:
                raise OwnerLiveRearmError("overlap or ambiguous active operation")
            receipt = db.execute(
                "SELECT * FROM "+TABLE+" WHERE operation_sha256=? "
                "AND state='ACTIVE'", (operation_sha256,)
            ).fetchone()
            if receipt is None or receipt["kind"] not in KINDS:
                raise OwnerLiveRearmError("unknown owner operation")
            if now >= q._parse(receipt["scheduled_due_at"]):
                raise OwnerLiveRearmError("rollback window expired")
            row = _row(db, receipt["kind"])
            if (row["job_id"] != receipt["job_id"]
                    or row["status"] != "PENDING"
                    or row["attempts"] != 0
                    or row["lease_token"] is not None
                    or row["lease_expires_at"] is not None
                    or _fingerprint(row) != receipt["after_sha256"]):
                raise OwnerLiveRearmError("already claimed or changed")
            db.execute(
                "UPDATE jobs SET status='REVIEW_REQUIRED',attempts=?,"
                "due_at=?,last_reason=?,lease_token=NULL,"
                "lease_expires_at=NULL WHERE job_id=?",
                (receipt["before_attempts"], receipt["before_due_at"],
                 receipt["before_reason"], receipt["job_id"]))
            if _fingerprint(_row(db, receipt["kind"])) != receipt["before_sha256"]:
                raise OwnerLiveRearmError("rollback did not restore exact row")
            db.execute(
                "UPDATE "+TABLE+" SET state='ROLLED_BACK' WHERE "
                "operation_sha256=? AND state='ACTIVE'",
                (operation_sha256,))
            db.execute("COMMIT")
        except Exception:
            if db.in_transaction:
                db.execute("ROLLBACK")
            raise
    return {
        "schema": SCHEMA,
        "status": "EXACT_ONE_OWNER_P10_ROLLBACK_CONFIRMED",
        "operation_sha256": operation_sha256,
        "worker_stopped": False, "public_gets": 0,
        "scheduler_modified": False, "auto_promoted": False,
    }


def _finalize_once(root: Path, operation_sha256: str,
                   now: datetime, *, owner_consent: str) -> dict:
    """Close one ACTIVE rearm only after a matching completed P10 job receipt.

    No worker action or P11 GET. A P10 success row or immutable completion
    summary after the scheduled due is mandatory. Fail closed otherwise.
    """
    _require_write_gate(root, owner_consent, action="finalize")
    if (type(operation_sha256) is not str
            or re.fullmatch("[0-9a-f]{64}", operation_sha256) is None
            or not isinstance(now, datetime)
            or now.utcoffset() != timedelta(0)):
        raise OwnerLiveRearmError("exact completion receipt and UTC required")
    with closing(_conn(root, readonly=False)) as db:
        try:
            db.execute("BEGIN IMMEDIATE")
            if db.execute(
                "SELECT COUNT(*) FROM jobs WHERE status='RUNNING'"
            ).fetchone()[0]:
                raise OwnerLiveRearmError("worker still running")
            receipt = db.execute(
                "SELECT * FROM "+TABLE+" WHERE operation_sha256=? "
                "AND state='ACTIVE'", (operation_sha256,)
            ).fetchone()
            if receipt is None or receipt["kind"] not in KINDS:
                raise OwnerLiveRearmError("unrecognized owner rearm receipt")
            due = q._parse(receipt["scheduled_due_at"])
            if now < due:
                raise OwnerLiveRearmError("job has not reached due time")
            row = _row(db, receipt["kind"])
            if row["job_id"] != receipt["job_id"]:
                raise OwnerLiveRearmError("job identity drift")
            completed = False
            if row["status"] == "SUCCEEDED" and row["completed_at"]:
                completed = q._parse(row["completed_at"]) >= due
            summary_exists = db.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' "
                "AND name='p10_completed'").fetchone() is not None
            if not completed and summary_exists:
                summary = db.execute(
                    "SELECT job_id, finished_at, completion_count "
                    "FROM p10_completed WHERE kind=?",
                    (receipt["kind"],)).fetchone()
                completed = bool(
                    summary is not None
                    and summary["job_id"] == receipt["job_id"]
                    and summary["completion_count"] >= 1
                    and q._parse(summary["finished_at"]) >= due)
            if not completed:
                raise OwnerLiveRearmError("no exact successful job completion")
            affected = db.execute(
                "UPDATE "+TABLE+" SET state='COMPLETED' WHERE "
                "operation_sha256=? AND state='ACTIVE'",
                (operation_sha256,)).rowcount
            if affected != 1:
                raise OwnerLiveRearmError("one receipt must be finalized")
            db.execute("COMMIT")
        except Exception:
            if db.in_transaction:
                db.execute("ROLLBACK")
            raise
    return {
        "schema": SCHEMA,
        "status": "EXACT_ONE_P10_COMPLETION_RECEIPT_FINALIZED",
        "operation_sha256": operation_sha256, "kind": receipt["kind"],
        "scheduler_modified": False, "public_gets": 0,
        "auto_promoted": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="UCIE owner-only one-job rearm")
    parser.add_argument("--ucie-root", type=Path, required=True)
    parser.add_argument("--kind", choices=sorted(KINDS), required=True)
    choice = parser.add_mutually_exclusive_group()
    choice.add_argument("--apply", action="store_true")
    choice.add_argument("--rollback", action="store_true")
    choice.add_argument("--finalize", action="store_true")
    parser.add_argument("--job-id", type=int)
    parser.add_argument("--expected-sha256")
    parser.add_argument("--operation-sha256")
    parser.add_argument("--owner-consent")
    args = parser.parse_args()
    try:
        if args.apply:
            if (args.owner_consent != CONSENT or args.job_id is None
                    or args.expected_sha256 is None
                    or args.operation_sha256 is not None):
                raise OwnerLiveRearmError("exact owner authorization required")
            root = _validate_root(args.ucie_root)
            result = _commit_once(
                root, args.kind, args.job_id,
                args.expected_sha256, datetime.now(timezone.utc),
                owner_consent=args.owner_consent)
        elif args.rollback:
            if (args.owner_consent !=
                    ROLLBACK_CONSENT
                    or args.operation_sha256 is None
                    or args.expected_sha256 is not None
                    or args.job_id is not None):
                raise OwnerLiveRearmError("exact rollback authorization required")
            root = _validate_root(args.ucie_root)
            result = _rollback_once(
                root, args.operation_sha256, datetime.now(timezone.utc),
                owner_consent=args.owner_consent)
            if result["status"] != "EXACT_ONE_OWNER_P10_ROLLBACK_CONFIRMED":
                raise OwnerLiveRearmError("rollback verification failed")
        elif args.finalize:
            if (args.owner_consent != FINALIZE_CONSENT
                    or args.operation_sha256 is None
                    or args.expected_sha256 is not None
                    or args.job_id is not None):
                raise OwnerLiveRearmError("exact finalize authorization required")
            root = _validate_root(args.ucie_root)
            result = _finalize_once(
                root, args.operation_sha256, datetime.now(timezone.utc),
                owner_consent=args.owner_consent)
        else:
            if (args.owner_consent is not None or args.job_id is not None
                    or args.expected_sha256 is not None
                    or args.operation_sha256 is not None):
                raise OwnerLiveRearmError("preview accepts no mutation fields")
            result = preview(args.ucie_root, args.kind)
    except (OwnerLiveRearmError, sqlite3.Error, q.PendingQueueError,
            OSError, ValueError, subprocess.TimeoutExpired) as exc:
        print(json.dumps({"schema": SCHEMA,
                          "status": "P10_ONE_OWNER_JOB_FAIL_CLOSED",
                          "error_type": type(exc).__name__,
                          "scheduler_modified": False,
                          "public_gets": 0, "auto_promoted": False},
                         sort_keys=True))
        return 2
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
