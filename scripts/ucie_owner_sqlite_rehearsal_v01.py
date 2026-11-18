"""UCIE W16: private SQLite backup rehearsal, never an operating cutover.

The default command has no host access. Explicit owner-only Prepare backs up
UCIE runtime SQLite files via SQLite's online backup API to the protected
owner ARCHIVE. No D:/UCIE files are moved, overwritten, or deleted.

SQLite online backup provides per-file transaction consistency; it cannot
provide a global instant across several distinct SQLite databases. Thus these
copies are REHEARSAL ONLY and MUST NOT be promoted as cutover data.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
from hashlib import sha256
import json
import os
from pathlib import Path
import re
import sqlite3
import stat
import subprocess
import sys

SCHEMA = "UCIE_W16_OWNER_SQLITE_REHEARSAL_V01"
APPROVAL = "AUTHORIZE_UCIE_W16_PRIVATE_SQLITE_REHEARSAL"
SOURCE = Path(r"D:\UCIE\runtime")
ARCHIVE = Path(r"D:\UCIE_PROJECT\ARCHIVE")
DEST = ARCHIVE / "UCIE_W16_SQLITE_REHEARSAL_V01"
NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,120}\.sqlite3\Z")
MAX_DBS = 32
MAX_BYTES = 2 * 1024**3
MAX_DB_BYTES = 512 * 1024**2


class PrivateSnapshotError(ValueError):
    pass


def direct(path: Path, *, directory: bool | None = None) -> bool:
    """Reject symlink/reparse points along the entire existing path."""
    try:
        start = path.lstat()
        if (directory is True and not stat.S_ISDIR(start.st_mode)
                or directory is False and not stat.S_ISREG(start.st_mode)):
            return False
        for part in (path, *path.parents):
            state = part.lstat()
            if stat.S_ISLNK(state.st_mode) or (
                    getattr(state, "st_file_attributes", 0) & 0x400):
                return False
        return True
    except OSError:
        return False


def _archive_acl_owner_only() -> bool:
    """Use the first-party Windows owner ACL policy, no ACL writes."""
    code = (
        "$ErrorActionPreference='Stop';"
        "$a=Get-Acl -LiteralPath 'D:\\UCIE_PROJECT\\ARCHIVE';"
        "$u=[Security.Principal.WindowsIdentity]::GetCurrent().User.Value;"
        "$o=$a.GetOwner([Security.Principal.SecurityIdentifier]).Value;"
        "if(-not $a.AreAccessRulesProtected -or $o -ne $u){exit 3};"
        "exit 0"
    )
    try:
        p = subprocess.run(
            ["powershell.exe", "-NoProfile", "-NonInteractive",
             "-Command", code], timeout=25, check=False,
            capture_output=True, text=True, errors="replace",
        )
        return p.returncode == 0
    except (OSError, subprocess.TimeoutExpired):
        return False


def snapshot_databases(source: Path, destination: Path) -> dict:
    """Rehearsal backups only; never overwrites an existing destination."""
    if not direct(source, directory=True) or not direct(
            destination.parent, directory=True):
        raise PrivateSnapshotError("SOURCE_OR_PROTECTED_ARCHIVE_INDIRECT")
    if destination.exists() or destination.is_symlink():
        raise PrivateSnapshotError("SNAPSHOT_DESTINATION_ALREADY_EXISTS")
    entries = sorted(
        (p for p in source.iterdir() if NAME.fullmatch(p.name)),
        key=lambda x: x.name.casefold(),
    )
    if not (1 <= len(entries) <= MAX_DBS):
        raise PrivateSnapshotError("SQLITE_CANDIDATE_COUNT_OUT_OF_RANGE")
    if not any(p.name == "public_miner.sqlite3" for p in entries):
        raise PrivateSnapshotError("PUBLIC_MINER_DATABASE_MISSING")
    total = 0
    for entry in entries:
        if not direct(entry, directory=False):
            raise PrivateSnapshotError("SQLITE_INPUT_INDIRECT_OR_MISSING")
        size = entry.stat().st_size
        if size < 512 or size > MAX_DB_BYTES:
            raise PrivateSnapshotError("SQLITE_INPUT_SIZE_OUT_OF_RANGE")
        total += size
        if total > MAX_BYTES:
            raise PrivateSnapshotError("SQLITE_TOTAL_SIZE_TOO_LARGE")
    destination.mkdir(mode=0o700)
    if not direct(destination, directory=True):
        raise PrivateSnapshotError("SNAPSHOT_DESTINATION_INDIRECT")
    receipts = []
    for original in entries:
        output = destination / original.name
        # Private ACL-protected parent, exclusive reserve before SQLite opens.
        with output.open("xb"):
            pass
        try:
            source_uri = original.as_uri() + "?mode=ro"
            with sqlite3.connect(source_uri, uri=True, timeout=4.0) as src:
                with sqlite3.connect(str(output), timeout=4.0) as dst:
                    src.backup(dst, pages=256, sleep=0.05)
                    result = dst.execute("PRAGMA quick_check").fetchall()
                    if result != [("ok",)]:
                        raise PrivateSnapshotError("SNAPSHOT_QUICK_CHECK_FAILED")
            digest = sha256(output.read_bytes()).hexdigest()
            receipts.append({
                "name": original.name,
                "bytes": output.stat().st_size,
                "sha256": digest,
            })
        except (sqlite3.Error, OSError, ValueError) as exc:
            # Do not delete partial snapshot. Do not disclose DB names/data.
            raise PrivateSnapshotError(
                "ONE_DATABASE_BACKUP_FAILED_PARTIAL_HOLD") from exc
    manifest = {
        "schema": SCHEMA,
        "status": "UCIE_W16_PRIVATE_SQLITE_REHEARSAL_COMPLETE",
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "dbs": receipts,
        "single_global_transaction": False,
        "rehearsal_only": True,
        "cutover_data_freshness_accepted": False,
        "original_sqlite_updated_by_ucie_sql": False,
        "tasks_or_c40_modified": False,
        "owner_live_cutover_authorized": False,
    }
    (destination / "private_manifest.json").write_text(
        json.dumps(manifest, sort_keys=True, indent=2) + "\n",
        encoding="utf-8", errors="strict",
    )
    return {
        "schema": SCHEMA,
        "status": "UCIE_W16_PRIVATE_SQLITE_REHEARSAL_COMPLETE__CUTOVER_HOLD",
        "snapshot_db_count": len(receipts),
        "snapshot_bytes": sum(row["bytes"] for row in receipts),
        "per_db_quick_check": "PASS",
        "global_snapshot_atomicity_claimed": False,
        "original_files_moved_or_deleted": False,
        "tasks_or_c40_modified": False,
        "owner_live_cutover_authorized": False,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="UCIE-only private SQLite rehearsal, default no host access")
    parser.add_argument("--prepare", action="store_true")
    parser.add_argument("--owner-approval", default="")
    args = parser.parse_args(argv)
    if not args.prepare:
        print(json.dumps({
            "schema": SCHEMA,
            "status": "UCIE_W16_CONTRACT_ONLY_NO_HOST_ACCESS",
            "source_sqlite_opened": False,
            "archive_written": False,
            "tasks_or_c40_modified": False,
            "owner_live_cutover_authorized": False,
        }, sort_keys=True))
        return 0
    try:
        if (args.owner_approval != APPROVAL or os.name != "nt"
                or not sys.stdin.isatty()):
            raise PrivateSnapshotError("EXPLICIT_INTERACTIVE_WINDOWS_OWNER_REQUIRED")
        if (str(SOURCE).casefold() != r"d:\ucie\runtime"
                or str(DEST).casefold() !=
                r"d:\ucie_project\archive\ucie_w16_sqlite_rehearsal_v01"
                or not direct(ARCHIVE, directory=True)
                or not _archive_acl_owner_only()):
            raise PrivateSnapshotError("PRIVATE_ARCHIVE_OR_ROOT_INVALID")
        receipt = snapshot_databases(SOURCE, DEST)
        print(json.dumps(receipt, sort_keys=True))
        return 0
    except (PrivateSnapshotError, OSError, sqlite3.Error) as exc:
        print(json.dumps({
            "schema": SCHEMA,
            "status": "UCIE_W16_PRIVATE_SQLITE_REHEARSAL_HOLD",
            "reason_type": type(exc).__name__,
            "do_not_reapply_or_delete_partial_destination": True,
            "owner_live_cutover_authorized": False,
        }, sort_keys=True))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
