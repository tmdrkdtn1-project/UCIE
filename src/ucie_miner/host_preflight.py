"""Stage 8 read-only UCIE-only Windows preflight observation.

This is NOT an installer, scheduler auditor, operational QA signature, or
approval. It uses SQLite read-only connections and generic counters.
"""
from __future__ import annotations

from contextlib import closing
from pathlib import Path
import sqlite3

ALLOWED_DB = ("public_miner.sqlite3", "knowledge.sqlite3")


def _inspect_sqlite(runtime: Path, name: str, required_table: str):
    path = runtime / name
    if (path.is_symlink() or not path.exists()
            or not path.is_file()):
        return {"state": "ABSENT_OR_UNSAFE", "integrity": "NOT_CHECKED",
                "records": None}
    try:
        uri = path.resolve(strict=True).as_uri() + "?mode=ro"
        with closing(sqlite3.connect(uri, uri=True, timeout=3)) as db:
            db.execute("PRAGMA query_only=ON")
            state = db.execute("PRAGMA quick_check").fetchone()
            if state != ("ok",):
                return {"state": "INVALID", "integrity": "FAIL",
                        "records": None}
            known = db.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
                (required_table,)).fetchone()
            if known is None:
                return {"state": "SCHEMA_MISSING", "integrity": "OK",
                        "records": None}
            count = db.execute("SELECT COUNT(*) FROM " + required_table).fetchone()[0]
            if type(count) is not int or count < 0:
                return {"state": "INVALID", "integrity": "FAIL",
                        "records": None}
        return {"state": "READ_ONLY_INSPECTED", "integrity": "OK",
                "records": count}
    except (sqlite3.DatabaseError, OSError, ValueError):
        return {"state": "UNAVAILABLE", "integrity": "UNKNOWN",
                "records": None}


def inspect_ucie_host(root: Path, *, is_windows: bool, python_version: tuple):
    """Explicit root is a test fixture; live wrapper pins root to D:/UCIE."""
    root = Path(root)
    if (root.is_symlink() or not root.is_dir()
            or (root / "runtime").is_symlink()):
        raise ValueError("unsafe UCIE checkout or runtime")
    runtime = root / "runtime"
    if not runtime.is_dir():
        raise ValueError("missing UCIE runtime directory")
    if type(is_windows) is not bool or not isinstance(python_version, tuple):
        raise ValueError("invalid host metadata")
    if (len(python_version) != 2 or
            any(type(v) is not int or v < 0 for v in python_version)):
        raise ValueError("invalid Python version")
    miner = _inspect_sqlite(runtime, "public_miner.sqlite3", "candidates")
    knowledge = _inspect_sqlite(runtime, "knowledge.sqlite3", "evidence")
    compatible = is_windows and python_version == (3, 15)
    complete = (compatible and
                miner["state"] == "READ_ONLY_INSPECTED" and
                knowledge["state"] == "READ_ONLY_INSPECTED")
    return {
        "schema": "UCIE_WINDOWS_HOST_PREFLIGHT_OBSERVATION_V1",
        "status": ("READ_ONLY_PRECHECK_COMPLETE" if complete else
                   "READ_ONLY_PRECHECK_INCOMPLETE"),
        "platform_compatible": compatible,
        "miner": miner, "knowledge": knowledge,
        "scheduler_registration": "NOT_INSPECTED",
        "rulepack_signature": "NOT_VERIFIED",
        "operator_approval": "NOT_VERIFIED",
        "operation_performed": False,
        "database_writes": 0,
        "rulepack_signed": False,
        "production_approved": False,
    }
