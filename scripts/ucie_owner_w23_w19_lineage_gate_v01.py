"""W23: W22 private W19 provenance pre-outage check as a Python SCRIPT FILE.

Do not pass multiline Python via "powershell.exe & python -c": Windows
PowerShell 5.1 can strip nested quoting when forwarding native argv.
Default command touches NO host. Explicit read-only owner mode calls the
existing first-party W19 _private_prerequisites() without starting tasks,
opening live SQLite, or modifying archives. Only W22 invokes this check.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
from pathlib import Path
import re
import stat
import sys

SCHEMA = "UCIE_W23_W22_PREOUTAGE_LINEAGE_ARGV_REPAIR_V01"
APPROVAL = "AUTHORIZE_UCIE_W23_READONLY_W19_LINEAGE_BEFORE_TASK_STOP"
ROOT = Path(r"D:\UCIE_PROJECT\UCIE")
OWNER_SCRIPT = ROOT / "scripts" / "ucie_owner_w23_w19_lineage_gate_v01.py"
W19_SCRIPT = ROOT / "scripts" / "ucie_owner_w19_lockstep_handoff_v01.py"
OWNER_PYTHON = ROOT / ".venv" / "Scripts" / "python.exe"
DB_NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,120}\.sqlite3\Z")


class GateHold(ValueError):
    """Pre-outage reject. Does not stop any task or create a maintenance intent."""


def direct(path: Path, directory: bool | None = None) -> bool:
    """Reject missing, symlinked, reparse-point or wrong-type files/parents."""
    try:
        meta = path.lstat()
        if directory is True and not stat.S_ISDIR(meta.st_mode):
            return False
        if directory is False and not stat.S_ISREG(meta.st_mode):
            return False
        for current in (path, *path.parents):
            item = current.lstat()
            if stat.S_ISLNK(item.st_mode) or (
                    getattr(item, "st_file_attributes", 0) & 0x400):
                return False
        return True
    except OSError:
        return False


def verify_lineage(w19_path: Path) -> set[str]:
    """Small synthetic-testable W19 receipt check, without live DB access."""
    if not direct(w19_path, directory=False):
        raise GateHold("UCIE_W23_W19_SOURCE_NOT_DIRECT")
    spec = importlib.util.spec_from_file_location(
        "ucie_w19_private_lineage_readonly", w19_path)
    if spec is None or spec.loader is None:
        raise GateHold("UCIE_W23_W19_IMPORT_SPEC_UNAVAILABLE")
    w19 = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(w19)
    callback = getattr(w19, "_private_prerequisites", None)
    if not callable(callback):
        raise GateHold("UCIE_W23_W19_LINEAGE_FUNCTION_MISSING")
    rows = callback()
    if (not isinstance(rows, set) or len(rows) != 10
            or any(not isinstance(name, str) or not DB_NAME.fullmatch(name)
                   for name in rows)
            or "public_miner.sqlite3" not in rows):
        raise GateHold("UCIE_W23_EXPECTED_TEN_ORIGINAL_SQLITE_NAMES_REQUIRED")
    return rows


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="UCIE W22 pre-outage private lineage gate, no mutation")
    parser.add_argument("--check-owner", action="store_true")
    parser.add_argument("--owner-approval", default="")
    options = parser.parse_args(argv)
    if not options.check_owner:
        print(json.dumps({
            "schema": SCHEMA,
            "status": "UCIE_W23_CONTRACT_ONLY_NO_HOST_ACCESS",
            "w19_source_imported": False,
            "private_receipts_read": False,
            "operating_sqlite_opened": False,
            "tasks_queried_or_modified": False,
            "c40_accessed": False,
            "live_cutover_authorized": False,
        }, sort_keys=True))
        return 0
    try:
        if options.owner_approval != APPROVAL:
            raise GateHold("UCIE_W23_EXPLICIT_OWNER_READONLY_APPROVAL_REQUIRED")
        if (os.name != "nt" or not sys.stdin.isatty()
                or sys.version_info[:2] != (3, 15)):
            raise GateHold("UCIE_W23_INTERACTIVE_WINDOWS_PY315_REQUIRED")
        if (Path(__file__).resolve() != OWNER_SCRIPT
                or Path(sys.executable).resolve() != OWNER_PYTHON
                or not direct(ROOT, directory=True)
                or not direct(OWNER_SCRIPT, directory=False)
                or not direct(OWNER_PYTHON, directory=False)):
            raise GateHold("UCIE_W23_EXACT_OWNER_NEWROOT_CODE_AND_PYTHON_REQUIRED")
        verify_lineage(W19_SCRIPT)
        print(json.dumps({
            "schema": SCHEMA,
            "status": "UCIE_W23_W19_PRIVATE_LINEAGE_PASS_BEFORE_TASK_STOP",
            "historical_database_count": 10,
            "historical_provenance_verified": True,
            "current_data_freshness_verified": False,
            "operating_sqlite_opened": False,
            "tasks_queried_or_modified": False,
            "c40_accessed": False,
            "live_cutover_authorized": False,
        }, sort_keys=True))
        return 0
    except (GateHold, OSError, ValueError, ImportError, RuntimeError,
            TypeError, AttributeError) as exc:
        reason = (str(exc) if isinstance(exc, GateHold)
                  and re.fullmatch(r"UCIE_W23_[A-Z0-9_]{5,100}", str(exc))
                  else type(exc).__name__)
        print(json.dumps({
            "schema": SCHEMA,
            "status": "UCIE_W23_PREOUTAGE_LINEAGE_HOLD_NO_TASK_STOP",
            "reason_code": reason,
            "operating_sqlite_opened": False,
            "tasks_queried_or_modified": False,
            "c40_accessed": False,
            "live_cutover_authorized": False,
        }, sort_keys=True))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
