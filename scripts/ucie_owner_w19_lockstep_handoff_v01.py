"""W19 owner-only, write-locked SQLite handoff; NEVER activates live tasks/C40.

All ten SQLite source connections acquire BEGIN IMMEDIATE before *any* image is
serialized. Once the last lock is acquired, their committed images coexist at
a common write barrier until the capture completes. The barrier does NOT
freeze external non-SQLite state or independently prove tunnel health.

Default invocation is NO-HOST. Only a separately approved, interactive Windows
maintenance call may populate an absent new-root runtime and a private journal.
Source database SQL is read-only apart from transient SQLite transaction locks;
WAL/SHM sidecars may be opened by SQLite. No source file is moved/deleted.
"""
from __future__ import annotations

import argparse
from contextlib import ExitStack, closing
from hashlib import sha256
import json
import os
from pathlib import Path
import re
import sqlite3
import stat
import subprocess
import sys
from typing import Callable

SCHEMA = "UCIE_W19_OWNER_LOCKSTEP_SQLITE_HANDOFF_V01"
APPROVAL = "AUTHORIZE_UCIE_W19_LOCKSTEP_FINAL_SQLITE_HANDOFF"
SOURCE = Path(r"D:\UCIE\runtime")
ROOT = Path(r"D:\UCIE_PROJECT\UCIE")
ARCHIVE = Path(r"D:\UCIE_PROJECT\ARCHIVE")
PRIVATE = ARCHIVE / "UCIE_W19_LOCKSTEP_FINAL_DATA_V01"
TARGET = ROOT / "runtime"
W16 = ARCHIVE / "UCIE_W16_SQLITE_REHEARSAL_V01" / "private_manifest.json"
W18 = ARCHIVE / "UCIE_W18_SQLITE_RESTORE_SANDBOX_V01" / "private_restore_receipt.json"
W14 = ARCHIVE / "UCIE_W14_OFFLINE_RUNTIME_RECEIPT_V01.json"
W17_ANCESTOR = "4c3de429680bbfb4da369ba04bc9e4e1a407cbb1"
EXPECTED_COUNT = 10
MAX_DB = 512 * 1024 * 1024
MAX_JSON = 1024 * 1024
DB_NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,120}\.sqlite3\Z")


class HandoffHold(ValueError):
    """Fail closed, preserve partial outputs; never expose owner filenames."""


def direct(path: Path, *, directory: bool | None = None) -> bool:
    try:
        item = path.lstat()
        if directory is True and not stat.S_ISDIR(item.st_mode):
            return False
        if directory is False and not stat.S_ISREG(item.st_mode):
            return False
        for part in (path, *path.parents):
            metadata = part.lstat()
            if (stat.S_ISLNK(metadata.st_mode)
                    or getattr(metadata, "st_file_attributes", 0) & 0x400):
                return False
        return True
    except OSError:
        return False


def absent(path: Path) -> bool:
    return not path.exists() and not path.is_symlink()


def read_json(path: Path) -> dict:
    if not direct(path, directory=False) or not 0 < path.stat().st_size <= MAX_JSON:
        raise HandoffHold("UCIE_W19_PRIVATE_RECEIPT_UNREADABLE")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (UnicodeError, ValueError) as exc:
        raise HandoffHold("UCIE_W19_PRIVATE_RECEIPT_INVALID") from exc
    if not isinstance(value, dict):
        raise HandoffHold("UCIE_W19_PRIVATE_RECEIPT_INVALID")
    return value


def _private_prerequisites() -> set[str]:
    historical = read_json(W16)
    restore = read_json(W18)
    environment = read_json(W14)
    if (historical.get("schema") != "UCIE_W16_OWNER_SQLITE_REHEARSAL_V01"
            or historical.get("status") != "UCIE_W16_PRIVATE_SQLITE_REHEARSAL_COMPLETE"
            or historical.get("rehearsal_only") is not True
            or historical.get("single_global_transaction") is not False
            or restore.get("schema") != "UCIE_W18_OWNER_SQLITE_RESTORE_SANDBOX_V01"
            or restore.get("status") != "UCIE_W18_PRIVATE_RESTORE_REHEARSAL_COMPLETE"
            or restore.get("restored_database_count") != EXPECTED_COUNT
            or restore.get("restored_bytes") != 5_656_576
            or restore.get("sqlite_readonly_quick_check") is not True
            or restore.get("global_consistent_cutover_data") is not False
            or restore.get("new_root_runtime_data_written") is not False
            or environment.get("schema") != "UCIE_W14_OFFLINE_RUNTIME_V01"
            or environment.get("status") != "UCIE_W14_ISOLATED_OFFLINE_PYTHON_RUNTIME_PREPARED"
            or environment.get("offline_dependency_import_ok") is not True):
        raise HandoffHold("UCIE_W19_OWNER_W14_W16_W18_GATE_NOT_PASSED")
    rows = historical.get("dbs")
    # W18 bound the historical W16 manifest by hash. Do not accept a
    # subsequently swapped manifest or a mismatched set of restored rows.
    if (restore.get("source_w16_manifest_sha256") !=
            sha256(W16.read_bytes()).hexdigest() or
            restore.get("restored_rows") != rows):
        raise HandoffHold("UCIE_W19_W16_W18_PROVENANCE_MISMATCH")
    if not isinstance(rows, list) or len(rows) != EXPECTED_COUNT:
        raise HandoffHold("UCIE_W19_HISTORICAL_DB_SET_UNVERIFIED")
    names = [row.get("name") for row in rows if isinstance(row, dict)]
    if (len(names) != EXPECTED_COUNT or
            any(not isinstance(name, str) or not DB_NAME.fullmatch(name)
                for name in names) or
            len({name.casefold() for name in names}) != EXPECTED_COUNT or
            "public_miner.sqlite3" not in {name.casefold() for name in names}):
        raise HandoffHold("UCIE_W19_HISTORICAL_DB_NAMES_INVALID")
    return set(names)


def _windows_owner_guard() -> str:
    if os.name != "nt" or not sys.stdin.isatty():
        raise HandoffHold("UCIE_W19_INTERACTIVE_WINDOWS_OWNER_REQUIRED")
    if (not direct(SOURCE, directory=True) or
            not direct(ROOT, directory=True) or
            not direct(ARCHIVE, directory=True) or
            not direct(ROOT / ".git", directory=True) or
            not direct(ROOT / ".venv" / "Scripts" / "python.exe", directory=False)):
        raise HandoffHold("UCIE_W19_EXACT_DIRECT_ROOTS_REQUIRED")
    # This command has no effects on Task Scheduler. Check three task owners,
    # *already Disabled* states, and hash the unchanged C40 action.
    script = r"""
$ErrorActionPreference='Stop'
Import-Module ScheduledTasks -ErrorAction Stop
$owner=[Security.Principal.WindowsIdentity]::GetCurrent().User.Value
foreach($name in @('UCIE-PublicMiner-Hourly','UCIE-Internal-Minute','UCIE-LocalV1-Web')){
  $t=Get-ScheduledTask -TaskPath '\' -TaskName $name -ErrorAction Stop
  if([string]$t.State -ne 'Disabled'){exit 3}
  if(@($t.Actions).Count -ne 1){exit 4}
  $id=[string]$t.Principal.UserId
  $sid=if($id -match '^S-1-[0-9-]+$'){$id}else{
    ([Security.Principal.NTAccount]::new($id)).Translate([Security.Principal.SecurityIdentifier]).Value
  }
  if($sid -ne $owner){exit 5}
}
$c=Get-ScheduledTask -TaskPath '\' -TaskName 'UCIE-C40-Recover' -ErrorAction Stop
if(@($c.Actions).Count -ne 1){exit 6}
$a=$c.Actions[0]
$join=@([string]$a.Execute,[string]$a.Arguments,[string]$a.WorkingDirectory) -join [char]0
$h=[Security.Cryptography.SHA256]::Create()
try {
  $bytes=[Text.Encoding]::UTF8.GetBytes($join)
  $digest=[BitConverter]::ToString($h.ComputeHash($bytes)).Replace('-','').ToLowerInvariant()
  $acl=Get-Acl -LiteralPath 'D:\UCIE_PROJECT\ARCHIVE'
  if(-not $acl.AreAccessRulesProtected -or
     $acl.GetOwner([Security.Principal.SecurityIdentifier]).Value -ne $owner){exit 7}
  [Console]::Out.WriteLine($digest)
} finally {$h.Dispose()}
"""
    result = subprocess.run(
        ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", script],
        check=False, capture_output=True, text=True, timeout=35, errors="replace")
    digest = result.stdout.strip()
    if result.returncode != 0 or not re.fullmatch(r"[0-9a-f]{64}", digest):
        raise HandoffHold("UCIE_W19_DISABLED_TASK_OWNER_C40_OR_ACL_GATE_FAILED")
    check = subprocess.run(
        ["git", "-C", str(ROOT), "merge-base", "--is-ancestor",
         W17_ANCESTOR, "HEAD"], capture_output=True, timeout=15, check=False)
    if check.returncode != 0:
        raise HandoffHold("UCIE_W19_STAGED_ROOT_ANCESTRY_INVALID")
    return digest


def _write_exclusive(path: Path, data: bytes) -> None:
    with path.open("xb") as output:
        output.write(data)
        output.flush()
        os.fsync(output.fileno())


def _read_only_quick_check(path: Path) -> None:
    with closing(sqlite3.connect(path.as_uri() + "?mode=ro&immutable=1",
                                 uri=True, timeout=3.0)) as check:
        if check.execute("PRAGMA quick_check").fetchall() != [("ok",)]:
            raise HandoffHold("UCIE_W19_FINAL_SQLITE_QUICK_CHECK_FAILED")


def handoff_locked(source: Path, archive_output: Path, new_runtime: Path,
                   expected_names: set[str], *,
                   at_barrier: Callable[[], None] | None = None) -> dict:
    """Pure local engine, exercised on synthetic SQLite databases in CI.

    Acquires all ten BEGIN IMMEDIATE writer locks before serializing anything.
    Neither C40 continuity nor external non-SQLite writer quiescence is inferred.
    Destination and protected journal must be absent; no automatic retry.
    """
    if (not direct(source, directory=True)
            or not direct(archive_output.parent, directory=True)
            or not direct(new_runtime.parent, directory=True)
            or not absent(archive_output) or not absent(new_runtime)
            or source == new_runtime or source in new_runtime.parents
            or archive_output in new_runtime.parents
            or archive_output == new_runtime):
        raise HandoffHold("UCIE_W19_OUTPUT_OR_DIRECT_PATH_INVALID")
    if (len(expected_names) != EXPECTED_COUNT
            or len({n.casefold() for n in expected_names}) != EXPECTED_COUNT
            or any(DB_NAME.fullmatch(n) is None for n in expected_names)
            or "public_miner.sqlite3" not in {n.casefold() for n in expected_names}):
        raise HandoffHold("UCIE_W19_EXPECTED_DB_SET_INVALID")
    actual = [p for p in source.iterdir() if p.suffix.casefold() == ".sqlite3"]
    if ({p.name.casefold() for p in actual}
            != {name.casefold() for name in expected_names}
            or len(actual) != EXPECTED_COUNT):
        raise HandoffHold("UCIE_W19_CURRENT_DB_SET_CHANGED_REVIEW_REQUIRED")
    actual.sort(key=lambda p: p.name.casefold())
    for entry in actual:
        if (not direct(entry, directory=False)
                or not 512 <= entry.stat().st_size <= MAX_DB):
            raise HandoffHold("UCIE_W19_SOURCE_DB_TYPE_OR_SIZE_INVALID")
    with ExitStack() as stack:
        locked: list[tuple[Path, sqlite3.Connection]] = []
        # A failed or busy lock leaves no output directory and no partial cutover.
        for original in actual:
            conn = sqlite3.connect(original.as_uri() + "?mode=rw",
                                   uri=True, timeout=2.0, isolation_level=None)
            stack.callback(conn.close)
            conn.execute("PRAGMA busy_timeout=2000")
            conn.execute("BEGIN IMMEDIATE")
            stack.callback(conn.rollback)
            if conn.execute("PRAGMA quick_check").fetchall() != [("ok",)]:
                raise HandoffHold("UCIE_W19_SOURCE_QUICK_CHECK_FAILED")
            locked.append((original, conn))
        # At this barrier, writers are prevented from modifying every DB.
        if at_barrier is not None:
            at_barrier()
        archive_output.mkdir(mode=0o700)
        new_runtime.mkdir(mode=0o700)
        if (not direct(archive_output, directory=True)
                or not direct(new_runtime, directory=True)):
            raise HandoffHold("UCIE_W19_NEW_OUTPUT_INDIRECT")
        rows: list[dict] = []
        total = 0
        for original, conn in locked:
            data = conn.serialize()
            if (len(data) < 512 or len(data) > MAX_DB
                    or not data.startswith(b"SQLite format 3\x00")):
                raise HandoffHold("UCIE_W19_SQLITE_SERIALIZATION_FAILED")
            private_file = archive_output / original.name
            destination = new_runtime / original.name
            _write_exclusive(private_file, data)
            _write_exclusive(destination, data)
            digest = sha256(data).hexdigest()
            for candidate in (private_file, destination):
                if (not direct(candidate, directory=False)
                        or sha256(candidate.read_bytes()).hexdigest() != digest):
                    raise HandoffHold("UCIE_W19_STAGED_FILE_HASH_MISMATCH")
                _read_only_quick_check(candidate)
            rows.append({"name": original.name, "sha256": digest, "bytes": len(data)})
            total += len(data)
        private_manifest = {
            "schema": SCHEMA,
            "status": "UCIE_W19_ALL_SQLITE_WRITER_LOCKS_HELD_DURING_HANDOFF",
            "dbs": rows,
            "source_root": str(source),
            "staged_root": str(new_runtime),
            "sqlite_writer_barrier_held": True,
            "external_non_sqlite_state_frozen": False,
            "c40_tunnel_health_verified": False,
            "tasks_rebound_or_enabled": False,
            "source_logical_sql_writes": False,
            "live_cutover_authorized": False,
        }
        _write_exclusive(archive_output / "private_handoff_manifest.json",
                         (json.dumps(private_manifest, sort_keys=True, indent=2)
                          + "\n").encode("utf-8"))
        return {
            "schema": SCHEMA,
            "status": "UCIE_W19_FINAL_SQLITE_DATA_STAGED__TASK_C40_ACTIVATION_HOLD",
            "database_count": len(rows),
            "staged_database_bytes": total,
            "sqlite_quick_check": "PASS",
            "sqlite_writer_barrier_held": True,
            "non_sqlite_global_consistency_proven": False,
            "tasks_rebound_or_enabled": False,
            "c40_tunnel_health_verified": False,
            "live_cutover_authorized": False,
        }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="UCIE owner W19 guarded SQLite final handoff")
    parser.add_argument("--prepare", action="store_true")
    parser.add_argument("--owner-approval", default="")
    args = parser.parse_args(argv)
    if not args.prepare:
        print(json.dumps({
            "schema": SCHEMA,
            "status": "UCIE_W19_CONTRACT_ONLY_NO_HOST_ACCESS",
            "operating_sqlite_opened": False,
            "new_root_runtime_written": False,
            "task_or_c40_accessed": False,
            "live_cutover_authorized": False,
        }, sort_keys=True))
        return 0
    try:
        if args.owner_approval != APPROVAL:
            raise HandoffHold("UCIE_W19_EXPLICIT_OWNER_APPROVAL_REQUIRED")
        c40_before = _windows_owner_guard()
        expected = _private_prerequisites()
        receipt = handoff_locked(SOURCE, PRIVATE, TARGET, expected)
        if _windows_owner_guard() != c40_before:
            raise HandoffHold("UCIE_W19_C40_TASK_ACTION_DRIFT_AFTER_HANDOFF")
        print(json.dumps(receipt, sort_keys=True))
        return 0
    except (HandoffHold, OSError, sqlite3.Error, subprocess.TimeoutExpired,
            ValueError, RuntimeError, MemoryError) as exc:
        code = (str(exc) if isinstance(exc, HandoffHold)
                and re.fullmatch(r"UCIE_W19_[A-Z0-9_]{5,100}", str(exc))
                else type(exc).__name__)
        print(json.dumps({
            "schema": SCHEMA,
            "status": "UCIE_W19_FINAL_SQLITE_HANDOFF_HOLD",
            "reason_code": code,
            "preserve_partial_outputs_no_automatic_retry": True,
            "no_task_or_c40_changes_requested": True,
            "live_cutover_authorized": False,
        }, sort_keys=True))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
