"""UCIE W20: exact SQLite drift gate BEFORE a separately approved activation.

Default CLI mode performs no host access. The opt-in owner-only Windows mode
compares 10 *current* original SQLite logical images with both protected W19
handoff copies while all 10 source databases hold BEGIN IMMEDIATE.
This detects changes after W19 handoff; it does NOT prove that old non-SQLite
writers have stopped, or that C40 / MCP / LocalV1 is connected. It NEVER
starts Tasks, deletes files, alters customer data, or auto-rolls back a DB.
"""
from __future__ import annotations

import argparse
from contextlib import ExitStack, closing
from hashlib import sha256, file_digest
import importlib.util
import json
import os
from pathlib import Path
import re
import sqlite3
import stat
import sys
from typing import Callable

SCHEMA = "UCIE_W20_OWNER_ACTIVATION_DRIFT_GATE_V01"
APPROVAL = "AUTHORIZE_UCIE_W20_READONLY_WRITER_BARRIER_CHECK"
OLD = Path(r"D:\UCIE\runtime")
ROOT = Path(r"D:\UCIE_PROJECT\UCIE")
ARCHIVE = Path(r"D:\UCIE_PROJECT\ARCHIVE")
PRIVATE = ARCHIVE / "UCIE_W19_LOCKSTEP_FINAL_DATA_V01"
TARGET = ROOT / "runtime"
MANIFEST = PRIVATE / "private_handoff_manifest.json"
MARKER = ARCHIVE / ".ucie_owner_runtime_opt_in_v01"
W19_STAGE = ARCHIVE / "UCIE_W19_OWNER_DATA_TASK_STAGE_JOURNAL_V01.json"
W13_STAGE = ARCHIVE / "UCIE_W13_TASK_REBIND_V01.json"
NAMES = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,120}\.sqlite3\Z")
DIGEST = re.compile(r"[a-f0-9]{64}\Z")
MAX_DB = 512 * 1024 * 1024
MAX_MANIFEST = 1_000_000


class ActivationHold(ValueError):
    """Refuse further activation without modifying or deleting snapshots."""


def direct(path: Path, directory: bool | None = None) -> bool:
    try:
        m = path.lstat()
        if directory is True and not stat.S_ISDIR(m.st_mode):
            return False
        if directory is False and not stat.S_ISREG(m.st_mode):
            return False
        for p in (path, *path.parents):
            entry = p.lstat()
            if stat.S_ISLNK(entry.st_mode) or (
                    getattr(entry, "st_file_attributes", 0) & 0x400):
                return False
        return True
    except OSError:
        return False


def _file_hash(path: Path) -> str:
    with path.open("rb") as f:
        return file_digest(f, "sha256").hexdigest()


def _manifest_rows(path: Path, source: Path, target: Path) -> list[dict]:
    if not direct(path, directory=False) or not 0 < path.stat().st_size < MAX_MANIFEST:
        raise ActivationHold("UCIE_W20_PRIVATE_W19_MANIFEST_UNSAFE")
    try:
        m = json.loads(path.read_text("utf-8"))
    except (UnicodeError, ValueError) as exc:
        raise ActivationHold("UCIE_W20_PRIVATE_W19_MANIFEST_INVALID") from exc
    if (not isinstance(m, dict) or
            m.get("schema") != "UCIE_W19_OWNER_LOCKSTEP_SQLITE_HANDOFF_V01"
            or m.get("status") != "UCIE_W19_ALL_SQLITE_WRITER_LOCKS_HELD_DURING_HANDOFF"
            or m.get("sqlite_writer_barrier_held") is not True
            or m.get("external_non_sqlite_state_frozen") is not False
            or m.get("c40_tunnel_health_verified") is not False
            or m.get("tasks_rebound_or_enabled") is not False
            or m.get("live_cutover_authorized") is not False
            or m.get("source_root") != str(source)
            or m.get("staged_root") != str(target)):
        raise ActivationHold("UCIE_W20_W19_HANDOFF_PROVENANCE_REJECTED")
    rows = m.get("dbs")
    if not isinstance(rows, list) or len(rows) != 10:
        raise ActivationHold("UCIE_W20_EXPECTED_TEN_SQLITE_REQUIRED")
    seen: set[str] = set()
    for r in rows:
        if (not isinstance(r, dict)
                or not isinstance(r.get("name"), str)
                or NAMES.fullmatch(r["name"]) is None
                or not isinstance(r.get("sha256"), str)
                or DIGEST.fullmatch(r["sha256"]) is None
                or type(r.get("bytes")) is not int
                or not 512 <= r["bytes"] <= MAX_DB
                or r["name"].casefold() in seen):
            raise ActivationHold("UCIE_W20_W19_MANIFEST_ROW_INVALID")
        seen.add(r["name"].casefold())
    if "public_miner.sqlite3" not in seen:
        raise ActivationHold("UCIE_W20_PUBLIC_MINER_NOT_IN_STAGED_SET")
    return rows


def _check_sqlite_image(path: Path, digest: str, length: int) -> None:
    if (not direct(path, directory=False) or path.stat().st_size != length
            or _file_hash(path) != digest):
        raise ActivationHold("UCIE_W20_FINAL_COPY_DIGEST_OR_SIZE_CHANGED")
    with closing(sqlite3.connect(
            path.as_uri() + "?mode=ro&immutable=1", uri=True, timeout=4)) as db:
        if db.execute("PRAGMA quick_check").fetchall() != [("ok",)]:
            raise ActivationHold("UCIE_W20_SQLITE_FINAL_COPY_CORRUPTED")


def compare_frozen_sqlite(
        source: Path, private: Path, target: Path, manifest: Path,
        *,
        at_barrier: Callable[[], None] | None = None,
) -> dict:
    """Pure, synthetic-testable gate. No root mutation or task access.

    A conservative byte-level equality check on SQLite logical serialization:
    a checkpoint/repacking that changes bytes may lead to HOLD, never a
    false 'unchanged' claim. Writer locks are momentary and NOT a lease.
    """
    if (not direct(source, True) or not direct(private, True)
            or not direct(target, True)
            or not direct(manifest, False)):
        raise ActivationHold("UCIE_W20_DIRECT_SOURCE_ARCHIVE_TARGET_REQUIRED")
    rows = _manifest_rows(manifest, source, target)
    expected = {r["name"].casefold(): r for r in rows}
    for directory in (source, target):
        actual = [p for p in directory.iterdir() if p.suffix.casefold() == ".sqlite3"]
        if (len(actual) != 10 or
                {p.name.casefold() for p in actual} != set(expected)):
            raise ActivationHold("UCIE_W20_DATABASE_SET_DRIFT")
        if any(not direct(p, False) for p in actual):
            raise ActivationHold("UCIE_W20_REPARSE_DATABASE_DENIED")
    # Validate *both* staged images before touching source SQLite locks.
    for row in rows:
        for p in (private / row["name"], target / row["name"]):
            _check_sqlite_image(p, row["sha256"], row["bytes"])
    # Keep all ten original write-reservations until every logical source
    # byte image has been rechecked. It does NOT freeze external files.
    with ExitStack() as stack:
        locked: list[tuple[str, sqlite3.Connection]] = []
        for name in sorted(expected):
            original = source / expected[name]["name"]
            if not direct(original, False):
                raise ActivationHold("UCIE_W20_SOURCE_INDIRECT")
            conn = sqlite3.connect(original.as_uri() + "?mode=rw",
                                   uri=True, timeout=2, isolation_level=None)
            stack.callback(conn.close)
            conn.execute("BEGIN IMMEDIATE")
            stack.callback(conn.rollback)
            if conn.execute("PRAGMA quick_check").fetchall() != [("ok",)]:
                raise ActivationHold("UCIE_W20_SOURCE_SQLITE_CORRUPTED")
            locked.append((name, conn))
        if at_barrier:
            at_barrier()
        for name, conn in locked:
            image = conn.serialize()
            row = expected[name]
            if len(image) != row["bytes"] or sha256(image).hexdigest() != row["sha256"]:
                raise ActivationHold("UCIE_W20_POST_W19_SOURCE_SQLITE_DRIFT")
    return {
        "schema": SCHEMA,
        "status": "UCIE_W20_FROZEN_SQLITE_IMAGES_MATCH__LIVE_ACTIVATION_HOLD",
        "sqlitedb_count": len(rows),
        "original_db_images_equal_w19": True,
        "protected_archive_equals_target": True,
        "sqlite_writer_locks_overlap": True,
        "non_sqlite_global_consistency_verified": False,
        "old_writers_permanently_stopped": False,
        "c40_mcp_round_trip_verified": False,
        "localv1_new_process_healthy": False,
        "task_actions_changed": False,
        "live_cutover_authorized": False,
    }


def _owner_gate() -> None:
    if os.name != "nt" or not sys.stdin.isatty():
        raise ActivationHold("UCIE_W20_INTERACTIVE_WINDOWS_OWNER_REQUIRED")
    expected_script = ROOT / "scripts" / "ucie_owner_w20_activation_integrity_v01.py"
    if Path(__file__).resolve() != expected_script:
        raise ActivationHold("UCIE_W20_EXPECTED_STAGED_TOOL_PATH_REQUIRED")
    if (not direct(W19_STAGE, False) or not direct(W13_STAGE, False)
            or not direct(MARKER, False)):
        raise ActivationHold("UCIE_W20_W19_W13_MARKER_MISSING")
    if MARKER.read_bytes() != b"UCIE_OWNER_RELOCATED_RUNTIME_OPT_IN_V01\n":
        raise ActivationHold("UCIE_W20_OWNER_MARKER_INVALID")
    # W19 guards owner ACL, Python3.15 environment, exact Git ancestor,
    # three *already disabled* tasks, and unchanged C40 action hash.
    w19file = ROOT / "scripts" / "ucie_owner_w19_lockstep_handoff_v01.py"
    if not direct(w19file, False):
        raise ActivationHold("UCIE_W20_W19_SOURCE_MISSING")
    spec = importlib.util.spec_from_file_location("ucie_w19_readonly_gate", w19file)
    if spec is None or spec.loader is None:
        raise ActivationHold("UCIE_W20_W19_SOURCE_NOT_IMPORTABLE")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module._windows_owner_guard()
    w19 = json.loads(W19_STAGE.read_text("utf-8"))
    if (not isinstance(w19, dict) or
            w19.get("schema") != "UCIE_W19_OWNER_DATA_TASK_STAGE_V01"
            or w19.get("task_actions_initial") != "THREE_ORIGINAL_DISABLED"
            or w19.get("tasks_enabled") != 0):
        raise ActivationHold("UCIE_W20_W19_STAGE_JOURNAL_UNTRUSTED")


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="W20 owner-only SQLite drift gate")
    p.add_argument("--verify", action="store_true")
    p.add_argument("--owner-approval", default="")
    args = p.parse_args(argv)
    if not args.verify:
        print(json.dumps({
            "schema": SCHEMA,
            "status": "UCIE_W20_CONTRACT_ONLY_NO_HOST_ACCESS",
            "operating_db_opened": False, "sqlite_locks_requested": False,
            "tasks_queried": False, "c40_accessed": False,
            "live_cutover_authorized": False,
        }, sort_keys=True))
        return 0
    try:
        if args.owner_approval != APPROVAL:
            raise ActivationHold("UCIE_W20_EXPLICIT_OWNER_APPROVAL_REQUIRED")
        _owner_gate()
        result = compare_frozen_sqlite(OLD, PRIVATE, TARGET, MANIFEST)
        print(json.dumps(result, sort_keys=True))
        return 0
    except (ActivationHold, OSError, ValueError, sqlite3.Error,
            MemoryError, RuntimeError) as exc:
        reason = (str(exc) if isinstance(exc, ActivationHold)
                  and re.fullmatch(r"UCIE_W20_[A-Z0-9_]{5,90}", str(exc))
                  else type(exc).__name__)
        print(json.dumps({
            "schema": SCHEMA,
            "status": "UCIE_W20_ACTIVATION_SQLITE_GATE_HOLD",
            "reason_code": reason,
            "no_snapshot_or_operating_data_overwrite": True,
            "live_cutover_authorized": False,
        }, sort_keys=True))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
