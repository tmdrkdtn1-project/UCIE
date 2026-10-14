"""Read-only UCIE local promotion preflight; never touches any other project."""
from __future__ import annotations

import json
from pathlib import Path
import sqlite3
import sys

def main() -> int:
    root = Path(__file__).resolve().parents[1]
    if str(root).casefold() != "d:\\ucie".casefold():
        print(json.dumps({"status": "HOLD", "reason": "EXPECTED_D_UCIE"}))
        return 2
    db = root / "runtime" / "public_miner.sqlite3"
    if db.is_symlink() or not db.is_file():
        print(json.dumps({"status": "HOLD", "reason": "DATABASE_NOT_REGULAR_FILE"}))
        return 2
    uri = db.as_uri() + "?mode=ro"
    try:
        with sqlite3.connect(uri, uri=True, timeout=3) as con:
            integrity = con.execute("PRAGMA quick_check").fetchone()[0]
            tables = {row[0] for row in con.execute(
                "SELECT name FROM sqlite_master WHERE type='table'")}
            if not {"candidates", "runs"} <= tables:
                raise ValueError("missing known tables")
            candidates = con.execute("SELECT COUNT(*) FROM candidates").fetchone()[0]
            runs = con.execute("SELECT COUNT(*) FROM runs").fetchone()[0]
            invalid = con.execute(
                "SELECT COUNT(*) FROM candidates WHERE status != 'UNVERIFIED_CANDIDATE_ONLY'"
            ).fetchone()[0]
        safe = integrity == "ok" and invalid == 0
        print(json.dumps({"status": "READ_ONLY_DB_OK" if safe else "HOLD",
                          "integrity": integrity, "candidates": candidates,
                          "runs": runs, "invalid_status_rows": invalid,
                          "auto_promotion": False, "scheduler_enabled_by_script": False}))
        return 0 if safe else 2
    except (sqlite3.Error, ValueError, OSError) as exc:
        print(json.dumps({"status": "HOLD", "error_type": type(exc).__name__}))
        return 2

if __name__ == "__main__":
    sys.exit(main())
