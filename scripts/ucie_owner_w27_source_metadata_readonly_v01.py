"""UCIE W27: read-only metadata-only source SQLite inventory preflight.

Never opens operating SQLite content, never takes SQLite locks, and never
changes Task Scheduler, C40, Git state, or W22/W24/W21 protected journals.
Default contract mode does not access the host. Explicit owner check examines
the name/size/path shape of current old-root .sqlite3 files while writers run,
compared with the W16/W18 protected historical set. NOT a cutover snapshot.
"""
from __future__ import annotations

import argparse
import ctypes
import importlib.util
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import sys

SCHEMA = "UCIE_W27_OWNER_SOURCE_SQLITE_METADATA_READONLY_V01"
APPROVAL = "AUTHORIZE_UCIE_W27_READONLY_RUNNING_SQLITE_SOURCE_METADATA"
ROOT = Path(r"D:\UCIE_PROJECT\UCIE")
OLD_ROOT = Path(r"D:\UCIE")
SOURCE = OLD_ROOT / "runtime"
ARCHIVE = Path(r"D:\UCIE_PROJECT\ARCHIVE")
W19 = ROOT / "scripts" / "ucie_owner_w19_lockstep_handoff_v01.py"
SELF = ROOT / "scripts" / "ucie_owner_w27_source_metadata_readonly_v01.py"
PYTHON = ROOT / ".venv" / "Scripts" / "python.exe"
W26_SOURCE = "7e2442839fd4274940147ed7e5f14d4ee9d22b02"
W19_BLOB = "f1597a9411d783cc5c0ede8fa906976f96f349c5"
MAX_DB = 512 * 1024 * 1024
EXPECTED_COUNT = 10
DB_NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,120}\.sqlite3\Z")


class InventoryHold(ValueError):
    """No DB content or source changes are performed on a rejected preflight."""


def direct(path: Path, directory: bool | None = None) -> bool:
    try:
        meta = path.lstat()
        if directory is True and not stat.S_ISDIR(meta.st_mode):
            return False
        if directory is False and not stat.S_ISREG(meta.st_mode):
            return False
        for part in (path, *path.parents):
            node = part.lstat()
            if (stat.S_ISLNK(node.st_mode)
                    or getattr(node, "st_file_attributes", 0) & 0x400):
                return False
        return True
    except OSError:
        return False


def inventory(source: Path, historical_names: set[str]) -> dict[str, int | bool]:
    """Inspect filenames/lstat only; intentionally no DB open/connect/reads."""
    if not direct(source, directory=True):
        raise InventoryHold("UCIE_W27_SOURCE_RUNTIME_NOT_DIRECT")
    if (not isinstance(historical_names, set)
            or len(historical_names) != EXPECTED_COUNT
            or any(not isinstance(s, str) or not DB_NAME.fullmatch(s)
                   for s in historical_names)):
        raise InventoryHold("UCIE_W27_HISTORICAL_NAMES_INVALID")
    normalized = {name.casefold() for name in historical_names}
    if len(normalized) != EXPECTED_COUNT or "public_miner.sqlite3" not in normalized:
        raise InventoryHold("UCIE_W27_HISTORICAL_NAMES_INVALID")
    files = [p for p in source.iterdir() if p.suffix.casefold() == ".sqlite3"]
    if len(files) != EXPECTED_COUNT:
        raise InventoryHold("UCIE_W27_LIVE_SQLITE_COUNT_CHANGED")
    casefolded = [p.name.casefold() for p in files]
    if len(set(casefolded)) != EXPECTED_COUNT or set(casefolded) != normalized:
        raise InventoryHold("UCIE_W27_LIVE_SQLITE_NAME_SET_CHANGED")
    sizes = []
    for p in files:
        if (not direct(p, directory=False)
                or not DB_NAME.fullmatch(p.name)):
            raise InventoryHold("UCIE_W27_SOURCE_DB_INDIRECT_OR_NAME_INVALID")
        meta = p.lstat()
        if meta.st_size < 512 or meta.st_size > MAX_DB:
            raise InventoryHold("UCIE_W27_SOURCE_DB_SIZE_OUT_OF_BOUNDS")
        sizes.append(meta.st_size)
    return {
        "database_count": EXPECTED_COUNT,
        "total_bytes_at_observation": sum(sizes),
        "exact_historical_name_set": True,
        "direct_non_reparse_paths": True,
        "size_bounds_checked": True,
    }


def _git_checked(*args: str) -> str:
    env = dict(os.environ)
    env["GIT_OPTIONAL_LOCKS"] = "0"
    result = subprocess.run(
        ["git", "-C", str(ROOT), *args], capture_output=True, text=True,
        timeout=15, check=False, errors="replace", env=env)
    if result.returncode:
        raise InventoryHold("UCIE_W27_FIRST_PARTY_GIT_PIN_OR_CLEAN_HOLD")
    return result.stdout.strip()


def validate_canonical() -> None:
    if (not direct(ROOT, directory=True)
            or not direct(OLD_ROOT, directory=True)
            or not direct(ARCHIVE, directory=True)
            or not direct(SELF, directory=False)
            or not direct(W19, directory=False)
            or not direct(PYTHON, directory=False)
            or not direct(ROOT / ".git", directory=True)):
        raise InventoryHold("UCIE_W27_DIRECT_FIRST_PARTY_PATH_REQUIRED")
    if (Path(__file__).resolve() != SELF
            or Path(sys.executable).resolve() != PYTHON
            or _git_checked("remote", "get-url", "origin")
            != "https://github.com/tmdrkdtn1-project/UCIE.git"):
        raise InventoryHold("UCIE_W27_CANONICAL_OWNER_CODE_OR_PYTHON_REQUIRED")
    _git_checked("merge-base", "--is-ancestor", W26_SOURCE, "HEAD")
    if (_git_checked("rev-parse",
                     "HEAD:scripts/ucie_owner_w19_lockstep_handoff_v01.py")
            != W19_BLOB):
        raise InventoryHold("UCIE_W27_W19_HANDOFF_SOURCE_BLOB_DRIFT")
    if _git_checked("status", "--porcelain", "--untracked-files=all"):
        raise InventoryHold("UCIE_W27_DIRTY_WORKTREE_HOLD")
    if (not _absent(ARCHIVE / "UCIE_W19_OWNER_DATA_TASK_STAGE_JOURNAL_V01.json")
            or not _absent(ARCHIVE / "UCIE_W13_TASK_REBIND_V01.json")
            or not _absent(ARCHIVE / "UCIE_W20_LOCAL_PILOT_JOURNAL_V01.json")
            or not _absent(ARCHIVE / "UCIE_W19_LOCKSTEP_FINAL_DATA_V01")
            or not _absent(ARCHIVE / ".ucie_owner_runtime_opt_in_v01")
            or not _absent(ROOT / "runtime")):
        raise InventoryHold("UCIE_W27_PARTIAL_STAGE_PRESENT_NO_METADATA_PASS")


def _absent(path: Path) -> bool:
    try:
        path.lstat()
    except FileNotFoundError:
        return True
    return False


def historical_names() -> set[str]:
    # W19 already enforces W14/W16/W18 owner provenance SHA, manifest schema,
    # ten historical names and immutable historical byte-count constraints.
    # Import checked-in SOURCE ONLY; do not call its --prepare mode.
    spec = importlib.util.spec_from_file_location(
        "ucie_w19_historical_provenance_readonly_v27", W19)
    if spec is None or spec.loader is None:
        raise InventoryHold("UCIE_W27_W19_SOURCE_IMPORT_SPEC_UNAVAILABLE")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module._private_prerequisites()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="W27 owner SQLite metadata only")
    parser.add_argument("--check-owner", action="store_true")
    parser.add_argument("--owner-approval", default="")
    opts = parser.parse_args(argv)
    if not opts.check_owner:
        print(json.dumps({
            "schema": SCHEMA,
            "status": "UCIE_W27_CONTRACT_ONLY_NO_HOST_ACCESS",
            "host_files_read": False,
            "sqlite_content_opened": False,
            "sqlite_locks_acquired": False,
            "task_or_c40_accessed": False,
            "journal_written": False,
            "full_cutover_authorized": False,
        }, sort_keys=True))
        return 0
    try:
        if opts.owner_approval != APPROVAL:
            raise InventoryHold("UCIE_W27_EXPLICIT_READONLY_OWNER_APPROVAL_REQUIRED")
        if (os.name != "nt" or not sys.stdin.isatty()
                or sys.version_info[:2] != (3, 15)
                or not bool(ctypes.windll.shell32.IsUserAnAdmin())):
            raise InventoryHold("UCIE_W27_INTERACTIVE_ELEVATED_WINDOWS_PY315_REQUIRED")
        validate_canonical()
        summary = inventory(SOURCE, historical_names())
        print(json.dumps({
            "schema": SCHEMA,
            "status": "UCIE_W27_RUNNING_OLD_SOURCE_SQLITE_METADATA_MATCH__LOCKS_NOT_TESTED",
            **summary,
            "historical_backup_is_current_global_snapshot": False,
            "running_writers_paused": False,
            "sqlite_content_opened": False,
            "sqlite_locks_acquired": False,
            "source_file_hashes_claimed": False,
            "source_quick_check_claimed": False,
            "w19_disabled_state_apply_replayed": False,
            "task_or_c40_accessed": False,
            "journal_written": False,
            "old_protected_intents_modified": False,
            "full_cutover_authorized": False,
        }, sort_keys=True))
        return 0
    except (InventoryHold, OSError, ValueError, RuntimeError,
            ImportError, AttributeError, subprocess.SubprocessError) as exc:
        if (isinstance(exc, InventoryHold)
                and re.fullmatch(r"UCIE_W27_[A-Z0-9_]{5,100}", str(exc))):
            reason = str(exc)
        else:
            reason = type(exc).__name__
        print(json.dumps({
            "schema": SCHEMA,
            "status": "UCIE_W27_SOURCE_METADATA_READONLY_HOLD",
            "reason_code": reason,
            "sqlite_content_opened": False,
            "task_or_c40_accessed": False,
            "journal_written": False,
            "full_cutover_authorized": False,
        }, sort_keys=True))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
