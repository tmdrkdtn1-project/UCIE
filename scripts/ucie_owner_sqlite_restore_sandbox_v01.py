"""UCIE W18: isolated restore rehearsal from the verified W16 private snapshot.

This does NOT produce operating runtime data, start any process, bind Tasks,
touch C40, or read/modify the original D:/UCIE databases. The destination is
a separate, owner-protected ARCHIVE sandbox. W16's ten SQLite snapshots are
historical and are never claimed to be a globally atomic cutover image.

Default is no-host contract. Real preparation is explicit owner opt-in only.
"""
from __future__ import annotations

import argparse
from contextlib import closing
from hashlib import file_digest
import json
import os
from pathlib import Path
import re
import shutil
import sqlite3
import stat
import subprocess
import sys

SCHEMA = "UCIE_W18_OWNER_SQLITE_RESTORE_SANDBOX_V01"
APPROVAL = "AUTHORIZE_UCIE_W18_PRIVATE_SQLITE_RESTORE_REHEARSAL"
ROOT = Path(r"D:\UCIE_PROJECT\UCIE")
ARCHIVE = Path(r"D:\UCIE_PROJECT\ARCHIVE")
W16 = ARCHIVE / "UCIE_W16_SQLITE_REHEARSAL_V01"
SANDBOX = ARCHIVE / "UCIE_W18_SQLITE_RESTORE_SANDBOX_V01"
W14_RECEIPT = ARCHIVE / "UCIE_W14_OFFLINE_RUNTIME_RECEIPT_V01.json"
OWNER_MARKER = ARCHIVE / ".ucie_owner_runtime_opt_in_v01"
EXPECTED_DB_COUNT = 10
EXPECTED_SNAPSHOT_BYTES = 5_656_576
NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,120}\.sqlite3\Z")
SHA = re.compile(r"[0-9a-f]{64}\Z")
MAX_DB_BYTES = 512 * 1024**2
MAX_JSON_BYTES = 1024 * 1024


class RestoreHold(ValueError):
    """A guarded stop. Leave partial output intact for owner review."""


def direct(path: Path, *, directory: bool | None = None) -> bool:
    try:
        metadata = path.lstat()
        if directory is True and not stat.S_ISDIR(metadata.st_mode):
            return False
        if directory is False and not stat.S_ISREG(metadata.st_mode):
            return False
        for node in (path, *path.parents):
            entry = node.lstat()
            if stat.S_ISLNK(entry.st_mode) or (
                    getattr(entry, "st_file_attributes", 0) & 0x400):
                return False
        return True
    except OSError:
        return False


def _read_bounded_json(path: Path) -> dict:
    if not direct(path, directory=False) or path.stat().st_size > MAX_JSON_BYTES:
        raise RestoreHold("UCIE_W18_MANIFEST_INDIRECT_OR_TOO_LARGE")
    with path.open("rb") as reader:
        try:
            value = json.load(reader)
        except (ValueError, UnicodeError) as exc:
            raise RestoreHold("UCIE_W18_MANIFEST_INVALID_JSON") from exc
    if not isinstance(value, dict):
        raise RestoreHold("UCIE_W18_MANIFEST_NOT_OBJECT")
    return value


def _file_hash(path: Path) -> str:
    with path.open("rb") as reader:
        return file_digest(reader, "sha256").hexdigest()


def _approved_source_rows(source: Path, *, count: int | None,
                          total_bytes: int | None) -> tuple[list[dict], str]:
    if not direct(source, directory=True):
        raise RestoreHold("UCIE_W18_SOURCE_NOT_DIRECT")
    manifest_path = source / "private_manifest.json"
    manifest = _read_bounded_json(manifest_path)
    if (manifest.get("schema") != "UCIE_W16_OWNER_SQLITE_REHEARSAL_V01"
            or manifest.get("status") != "UCIE_W16_PRIVATE_SQLITE_REHEARSAL_COMPLETE"
            or manifest.get("rehearsal_only") is not True
            or manifest.get("single_global_transaction") is not False
            or manifest.get("cutover_data_freshness_accepted") is not False
            or manifest.get("tasks_or_c40_modified") is not False
            or manifest.get("owner_live_cutover_authorized") is not False):
        raise RestoreHold("UCIE_W18_W16_REHEARSAL_PROVENANCE_INVALID")
    rows = manifest.get("dbs")
    if not isinstance(rows, list) or not 1 <= len(rows) <= 32:
        raise RestoreHold("UCIE_W18_MANIFEST_DB_COUNT_INVALID")
    if count is not None and len(rows) != count:
        raise RestoreHold("UCIE_W18_EXPECTED_TEN_DB_MANIFEST_REQUIRED")
    seen: set[str] = set()
    sizes = 0
    for row in rows:
        if not isinstance(row, dict):
            raise RestoreHold("UCIE_W18_MANIFEST_ROW_NOT_OBJECT")
        name, digest, size = row.get("name"), row.get("sha256"), row.get("bytes")
        if (not isinstance(name, str) or NAME.fullmatch(name) is None
                or name.casefold() in seen or not isinstance(digest, str)
                or SHA.fullmatch(digest) is None or type(size) is not int
                or not 512 <= size <= MAX_DB_BYTES):
            raise RestoreHold("UCIE_W18_MANIFEST_ROW_INVALID")
        seen.add(name.casefold())
        sizes += size
    if "public_miner.sqlite3" not in seen:
        raise RestoreHold("UCIE_W18_PUBLIC_MINER_DB_NOT_PRESENT")
    if total_bytes is not None and sizes != total_bytes:
        raise RestoreHold("UCIE_W18_OWNER_W16_BYTE_COUNT_MISMATCH")
    actual_names = {p.name.casefold() for p in source.iterdir()}
    if (actual_names != seen | {"private_manifest.json"}
            or len(actual_names) != len(rows) + 1):
        raise RestoreHold("UCIE_W18_UNLISTED_SOURCE_ENTRY")
    for row in rows:
        path = source / row["name"]
        if (not direct(path, directory=False)
                or path.stat().st_size != row["bytes"]
                or _file_hash(path) != row["sha256"]):
            raise RestoreHold("UCIE_W18_W16_HASH_OR_LENGTH_MISMATCH")
    return rows, _file_hash(manifest_path)


def restore_rehearsal(source: Path, destination: Path, *,
                      expected_count: int | None = None,
                      expected_total: int | None = None) -> dict:
    """Reconstitute only a private sandbox; never the future live runtime."""
    if not direct(destination.parent, directory=True) or source == destination:
        raise RestoreHold("UCIE_W18_OUTPUT_PARENT_INVALID")
    if destination.exists() or destination.is_symlink():
        raise RestoreHold("UCIE_W18_DESTINATION_EXISTS_NO_OVERWRITE")
    rows, manifest_hash = _approved_source_rows(
        source, count=expected_count, total_bytes=expected_total)
    # Reserve output only AFTER complete manifest, hash and size checks.
    destination.mkdir(mode=0o700)
    if not direct(destination, directory=True):
        raise RestoreHold("UCIE_W18_DESTINATION_NOT_DIRECT")
    bytes_copied = 0
    for row in rows:
        target = destination / row["name"]
        with (source / row["name"]).open("rb") as src:
            with target.open("xb") as dst:
                shutil.copyfileobj(src, dst, length=1024 * 1024)
        if (not direct(target, directory=False)
                or target.stat().st_size != row["bytes"]
                or _file_hash(target) != row["sha256"]):
            raise RestoreHold("UCIE_W18_RESTORED_BYTES_NOT_IDENTICAL")
        # Immutable, read-only SQLite open: no WAL/SHM/journal writes and
        # no schema migration, triggers or application workload execution.
        with closing(sqlite3.connect(
                target.as_uri() + "?mode=ro&immutable=1",
                uri=True, timeout=4.0)) as conn:
            check = conn.execute("PRAGMA quick_check").fetchall()
            if check != [("ok",)]:
                raise RestoreHold("UCIE_W18_SANDBOX_SQLITE_QUICK_CHECK_FAILED")
        bytes_copied += row["bytes"]
    receipt = {
        "schema": SCHEMA,
        "status": "UCIE_W18_PRIVATE_RESTORE_REHEARSAL_COMPLETE",
        "source_w16_manifest_sha256": manifest_hash,
        "restored_database_count": len(rows),
        "restored_bytes": bytes_copied,
        "restored_rows": rows,
        "sqlite_readonly_quick_check": True,
        "w16_snapshot_rehearsal_only": True,
        "global_consistent_cutover_data": False,
        "new_root_runtime_data_written": False,
        "original_root_or_sqlite_modified": False,
        "tasks_or_c40_modified": False,
        "owner_opt_in_marker_created": False,
        "live_cutover_authorized": False,
    }
    (destination / "private_restore_receipt.json").write_text(
        json.dumps(receipt, sort_keys=True, indent=2) + "\n",
        encoding="utf-8")
    return {
        "schema": SCHEMA,
        "status": "UCIE_W18_PRIVATE_RESTORE_PASS__LIVE_CUTOVER_HOLD",
        "restored_database_count": len(rows),
        "restored_bytes": bytes_copied,
        "sqlite_readonly_quick_check": "PASS",
        "new_root_runtime_data_written": False,
        "original_root_or_sqlite_modified": False,
        "tasks_or_c40_modified": False,
        "global_consistent_cutover_data": False,
        "live_cutover_authorized": False,
    }


def _owner_acl_protected() -> bool:
    code = (
        "$ErrorActionPreference='Stop';"
        "$a=Get-Acl -LiteralPath 'D:\\UCIE_PROJECT\\ARCHIVE';"
        "$u=[Security.Principal.WindowsIdentity]::GetCurrent().User.Value;"
        "$o=$a.GetOwner([Security.Principal.SecurityIdentifier]).Value;"
        "if(-not $a.AreAccessRulesProtected -or $o -ne $u){exit 3};"
        "exit 0"
    )
    try:
        run = subprocess.run(
            ["powershell.exe", "-NoProfile", "-NonInteractive",
             "-Command", code], timeout=25, capture_output=True,
            check=False, text=True, errors="replace")
        return run.returncode == 0
    except (OSError, subprocess.TimeoutExpired):
        return False


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="UCIE W18 private source snapshot restore rehearsal")
    parser.add_argument("--prepare", action="store_true")
    parser.add_argument("--owner-approval", default="")
    args = parser.parse_args(argv)
    if not args.prepare:
        print(json.dumps({
            "schema": SCHEMA, "status": "UCIE_W18_CONTRACT_ONLY_NO_HOST_ACCESS",
            "snapshot_opened": False, "sandbox_written": False,
            "tasks_or_c40_modified": False,
            "live_cutover_authorized": False,
        }, sort_keys=True))
        return 0
    try:
        if (args.owner_approval != APPROVAL or os.name != "nt"
                or not sys.stdin.isatty()
                or sys.version_info[:2] != (3, 15)):
            raise RestoreHold("UCIE_W18_EXPLICIT_OWNER_PY315_REQUIRED")
        if (not direct(ARCHIVE, directory=True)
                or not direct(W16, directory=True)
                or not direct(ROOT, directory=True)
                or not direct(ROOT / ".git", directory=True)
                or not direct(ROOT / ".venv" / "Scripts" / "python.exe",
                              directory=False)
                or not _owner_acl_protected()):
            raise RestoreHold("UCIE_W18_PROTECTED_STAGE_NOT_READY")
        prior = _read_bounded_json(W14_RECEIPT)
        if (prior.get("schema") != "UCIE_W14_OFFLINE_RUNTIME_V01"
                or prior.get("status") !=
                "UCIE_W14_ISOLATED_OFFLINE_PYTHON_RUNTIME_PREPARED"
                or prior.get("offline_dependency_import_ok") is not True):
            raise RestoreHold("UCIE_W18_W17_ENVIRONMENT_RECEIPT_INVALID")
        if (ROOT / "runtime").exists() or OWNER_MARKER.exists():
            raise RestoreHold("UCIE_W18_NEW_ROOT_RUNTIME_OR_OPTIN_ALREADY_EXISTS")
        result = restore_rehearsal(
            W16, SANDBOX, expected_count=EXPECTED_DB_COUNT,
            expected_total=EXPECTED_SNAPSHOT_BYTES)
        print(json.dumps(result, sort_keys=True))
        return 0
    except (RestoreHold, OSError, sqlite3.Error, ValueError) as exc:
        code = str(exc) if isinstance(exc, RestoreHold) else type(exc).__name__
        if not re.fullmatch(r"UCIE_W18_[A-Z0-9_]{5,90}", code):
            code = type(exc).__name__
        print(json.dumps({
            "schema": SCHEMA,
            "status": "UCIE_W18_RESTORE_REHEARSAL_HOLD",
            "reason_code": code,
            "preserve_partial_sandbox_no_retry": True,
            "tasks_or_c40_modified": False,
            "live_cutover_authorized": False,
        }, sort_keys=True))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
