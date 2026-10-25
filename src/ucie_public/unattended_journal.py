"""Atomic UCIE-only unattended work receipt claim, never an executor.

This is a first-party local primitive for a trusted, owner-provisioned OS
directory. SQLite transaction serializes competing consumers. External
immutable rollback checkpoint and exact Windows owner ACL remain mandatory
before a real Git push or restart; DB integrity alone is not authority.
"""
from __future__ import annotations

from contextlib import closing
from datetime import datetime, timezone
import os
from pathlib import Path
import sqlite3
import stat

from .policy import PolicyError
from .unattended_ops import verify_owner_operation_grant

DB_NAME = "ucie_unattended_claims.sqlite3"
CREATE = """
CREATE TABLE IF NOT EXISTS grants (
  sequence INTEGER PRIMARY KEY,
  nonce TEXT NOT NULL UNIQUE,
  task_id TEXT NOT NULL UNIQUE,
  grant_sha256 TEXT NOT NULL UNIQUE,
  operation TEXT NOT NULL,
  target TEXT NOT NULL,
  recorded_utc TEXT NOT NULL
)
"""


def _checked_db_path(directory: Path) -> Path:
    if not isinstance(directory, Path) or not directory.is_absolute():
        raise PolicyError("absolute owner-protected UCIE journal directory required")
    if directory.is_symlink() or not directory.is_dir():
        raise PolicyError("UCIE journal directory unavailable or linked")
    # OS ACL ownership and exact D:\UCIE trust root must be separately
    # checked by the installing owner adapter; parent links also forbidden.
    if any(p.is_symlink() for p in (directory, *directory.parents)):
        raise PolicyError("linked UCIE journal path denied")
    target = directory / DB_NAME
    if target.is_symlink():
        raise PolicyError("linked UCIE journal database denied")
    if target.exists():
        current = target.stat()
        if not stat.S_ISREG(current.st_mode) or current.st_size > 4_194_304:
            raise PolicyError("unexpected UCIE journal file")
        if os.name != "nt" and current.st_nlink != 1:
            raise PolicyError("linked UCIE journal inode denied")
    return target


def claim_owner_grant_once(
    directory: Path, signed_bytes: bytes, signature: bytes,
    trusted_public_key_pem: bytes, *, at_time: datetime | None = None,
) -> dict:
    """Create one atomic bounded grant-claim receipt, with no side effects.

    Grant data contains no private key or shell command. Concurrent calls
    are serialized by SQLite BEGIN IMMEDIATE. Restored DB snapshots are NOT
    detectable here: host-level external anti-rollback attestation is a
    separate release gate.
    """
    db = _checked_db_path(directory)
    now = datetime.now(timezone.utc) if at_time is None else at_time
    try:
        with closing(sqlite3.connect(str(db), timeout=2.0, isolation_level=None)) as conn:
            conn.execute("PRAGMA busy_timeout=2000")
            conn.execute("PRAGMA synchronous=FULL")
            conn.execute("PRAGMA trusted_schema=OFF")
            conn.execute("BEGIN IMMEDIATE")
            conn.execute(CREATE)
            last = conn.execute("SELECT COALESCE(MAX(sequence),0) FROM grants").fetchone()[0]
            grant = verify_owner_operation_grant(
                signed_bytes, signature, trusted_public_key_pem,
                last_consumed_sequence=last, at_time=now)
            conn.execute(
                "INSERT INTO grants(sequence,nonce,task_id,grant_sha256,"
                "operation,target,recorded_utc) VALUES(?,?,?,?,?,?,?)",
                (grant["sequence"], grant["nonce"], grant["task_id"],
                 grant["grant_sha256"], grant["operation"], grant["target"],
                 now.strftime("%Y-%m-%dT%H:%M:%SZ")))
            conn.execute("COMMIT")
    except (sqlite3.Error, OSError) as exc:
        raise PolicyError("UCIE owner grant atomic claim failed") from exc
    return {
        "status": "UCIE_OWNER_OPERATION_CLAIMED_NO_EXECUTION",
        "task_id": grant["task_id"],
        "operation": grant["operation"],
        "sequence": grant["sequence"],
        "grant_sha256": grant["grant_sha256"],
        "local_atomic_sqlite_claimed": True,
        "host_owner_acl_verified": False,
        "external_rollback_anchor_verified": False,
        "git_push_performed": False,
        "service_restarted": False,
        "rule_promoted": False,
        "production_deployed": False,
    }
